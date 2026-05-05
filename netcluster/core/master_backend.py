"""
Master Backend - Core backend logic for master node
"""
import threading
import time
from typing import Dict, Optional, Callable, List
from netcluster.network.server import NetworkServer
from netcluster.core.task_manager import TaskManager, TaskStatus
from netcluster.core.attacks.coordinator import AttackCoordinator
from netcluster.utils.logger import setup_logger
from netcluster.utils.config import WORKER_TIMEOUT

logger = setup_logger(__name__)


class MasterBackend:
    """Backend for master node - manages workers and tasks"""
    
    def __init__(self):
        self.network_server = NetworkServer()
        self.task_manager = TaskManager()
        self.attack_coordinator = AttackCoordinator(self.task_manager, self)
        self.workers: Dict[str, Dict] = {}  # worker_id -> {socket, name, ip, status, last_heartbeat}
        self.worker_socket_map: Dict = {}  # socket -> worker_id
        self.lock = threading.Lock()
        self.running = False
        
        # Setup callbacks
        self._setup_callbacks()
        
        # Callbacks for frontend
        self.on_worker_connected: Optional[Callable[[str, str, str], None]] = None
        self.on_worker_disconnected: Optional[Callable[[str], None]] = None
        self.on_task_status_changed: Optional[Callable[[str, str], None]] = None
        self.on_attack_result: Optional[Callable[[str], None]] = None  # fn(msg) -> Attack Results terminal
        self.on_worker_attack_log: Optional[Callable[[str, str], None]] = None  # fn(worker_name, msg)
    
    def _setup_callbacks(self):
        """Setup internal callbacks"""
        self.network_server.on_client_connected = self._on_client_connected
        self.network_server.on_client_disconnected = self._on_client_disconnected
        self.network_server.on_message_received = self._on_message_received
        self.task_manager.on_task_status_changed = self._on_task_status_changed
    
    def start_server(self):
        """Start the master server"""
        if self.running:
            return
        
        # Wire coordinator callbacks
        self.attack_coordinator.attack_result_callback = self._on_attack_result
        
        self.running = True
        self.network_server.start()
        
        # Start worker timeout checker
        timeout_thread = threading.Thread(target=self._timeout_checker, daemon=True)
        timeout_thread.start()
        
        # Start task distributor
        distributor_thread = threading.Thread(target=self._task_distributor, daemon=True)
        distributor_thread.start()

        # Initialize Ray Head Node in background with 2 CPUs by default
        # (subprocess calls are slow; must not block GUI)
        ray_thread = threading.Thread(target=self.restart_ray, args=(2,), daemon=True)
        ray_thread.start()
    
    def restart_ray(self, num_cpus: int):
        """(Re)Start Ray Head Node with specified CPU count — runs in background thread."""
        import ray
        import subprocess
        try:
            logger.info(f"(Re)Initializing Ray Head Node with {num_cpus} CPUs...")
            if ray.is_initialized():
                ray.shutdown()
            subprocess.run(["ray", "stop", "--force"], capture_output=True, timeout=15)
            subprocess.run(
                ["ray", "start", "--head", "--port=6379",
                 f"--num-cpus={num_cpus}", "--include-dashboard=False",
                 "--redis-password=netcluster"],
                capture_output=True, timeout=30
            )
            ray.init(address="auto", _redis_password="netcluster", ignore_reinit_error=True)
            logger.info("Ray Head Node initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Ray Head: {e}")
            return False
    
    def stop_server(self):
        """Stop the master server"""
        self.running = False
        self.network_server.stop()
        logger.info("Master backend stopped")
    
    def _on_client_connected(self, client_sock, worker_id: str, worker_name: str):
        """Handle client connection"""
        client_info = self.network_server.get_client_info(client_sock)
        ip_address = client_info['address'][0] if client_info else 'unknown'
        
        with self.lock:
            self.workers[worker_id] = {
                'socket': client_sock,
                'name': worker_name,
                'ip': ip_address,
                'status': 'idle',
                'last_heartbeat': time.time()
            }
            self.worker_socket_map[client_sock] = worker_id
        
        logger.info(f"Worker registered: {worker_id} ({worker_name}) from {ip_address}")
        
        if self.on_worker_connected:
            try:
                self.on_worker_connected(worker_id, worker_name, ip_address)
            except Exception as e:
                logger.error(f"Error in on_worker_connected callback: {e}")
    
    def _on_client_disconnected(self, client_sock):
        """Handle client disconnection"""
        worker_id = self.worker_socket_map.get(client_sock)
        
        if worker_id:
            with self.lock:
                if worker_id in self.workers:
                    del self.workers[worker_id]
                if client_sock in self.worker_socket_map:
                    del self.worker_socket_map[client_sock]
            
            logger.info(f"Worker disconnected: {worker_id}")
            
            if self.on_worker_disconnected:
                try:
                    self.on_worker_disconnected(worker_id)
                except Exception as e:
                    logger.error(f"Error in on_worker_disconnected callback: {e}")
    
    def _on_message_received(self, client_sock, message: Dict):
        """Handle received message"""
        msg_type = message.get('type')
        task_id = message.get('task_id')
        
        if msg_type == 'RESULT':
            payload = message.get('payload', {})
            success = payload.get('success', False)
            result = payload.get('result')
            error = payload.get('error')
            
            # Check if this is an attack result
            if isinstance(result, dict) and 'attack_id' in result:
                self.attack_coordinator.handle_worker_result(task_id, result)
            
            self.task_manager.complete_task(task_id, result, success, error)
        
        elif msg_type == 'HEARTBEAT':
            worker_id = self.worker_socket_map.get(client_sock)
            if worker_id:
                with self.lock:
                    if worker_id in self.workers:
                        self.workers[worker_id]['last_heartbeat'] = time.time()
                        status = message.get('payload', {}).get('status', 'idle')
                        self.workers[worker_id]['status'] = status
    
    def _on_task_status_changed(self, task_id: str, status: TaskStatus):
        """Handle task status change"""
        if self.on_task_status_changed:
            try:
                self.on_task_status_changed(task_id, status.value)
            except Exception as e:
                logger.error(f"Error in on_task_status_changed callback: {e}")
    
    def _on_attack_result(self, msg: str):
        """Relay attack result message to frontend"""
        if self.on_attack_result:
            try:
                self.on_attack_result(msg)
            except Exception as e:
                logger.error(f"Error in on_attack_result callback: {e}")
    
    def _timeout_checker(self):
        """Check for timed out workers and tasks"""
        while self.running:
            time.sleep(5)
            
            current_time = time.time()
            with self.lock:
                workers_to_remove = []
                for worker_id, worker_info in list(self.workers.items()):
                    elapsed = current_time - worker_info['last_heartbeat']
                    if elapsed > WORKER_TIMEOUT:
                        workers_to_remove.append(worker_id)
                
                for worker_id in workers_to_remove:
                    socket = self.workers[worker_id]['socket']
                    self._on_client_disconnected(socket)
            
            # Check task timeouts
            self.task_manager.check_timeouts()
    
    def _task_distributor(self):
        """Distribute tasks to idle workers"""
        worker_round_robin = []
        
        while self.running:
            time.sleep(1)
            
            # Get next task
            task = self.task_manager.get_next_task()
            if not task:
                continue
            
            # Get idle workers
            with self.lock:
                idle_workers = [
                    (wid, info) for wid, info in self.workers.items()
                    if info['status'] == 'idle'
                ]
            
            if not idle_workers:
                # No idle workers, put task back
                self.task_manager.task_queue.put(task.task_id)
                continue
            
            # Round-robin selection
            if not worker_round_robin:
                worker_round_robin = [wid for wid, _ in idle_workers]
            
            worker_id = worker_round_robin.pop(0)
            worker_round_robin.append(worker_id)
            
            # Assign task
            if self.task_manager.assign_task(task.task_id, worker_id):
                # Send task to worker
                worker_info = self.workers.get(worker_id)
                if worker_info:
                    from netcluster.network.protocol import Protocol
                    task_msg = Protocol.create_task_message(
                        task.task_id,
                        task.task_type,
                        task.payload
                    )
                    self.network_server.send_message(worker_info['socket'], task_msg)
    
    def get_connected_workers(self) -> Dict[str, Dict]:
        """Get all connected workers"""
        with self.lock:
            return {
                wid: {
                    'name': info['name'],
                    'ip': info['ip'],
                    'status': info['status']
                }
                for wid, info in self.workers.items()
            }
    
    def submit_task(self, task_type: str, payload: Dict, timeout: int = 300) -> str:
        """Submit a new task"""
        return self.task_manager.submit_task(task_type, payload, timeout)
    
    def get_task_status(self, task_id: str) -> Optional[str]:
        """Get task status"""
        status = self.task_manager.get_task_status(task_id)
        return status.value if status else None
    
    def get_all_tasks(self) -> Dict[str, Dict]:
        """Get all tasks with their status"""
        tasks = self.task_manager.get_all_tasks()
        return {
            task_id: {
                'task_type': task.task_type,
                'status': task.status.value,
                'assigned_worker': task.assigned_worker,
                'result': task.result,
                'error': task.error
            }
            for task_id, task in tasks.items()
        }
    
    def create_attack(self, attack_config: dict) -> str:
        """Create a new brute force attack"""
        return self.attack_coordinator.create_attack(attack_config)
    
    def get_attack_status(self, attack_id: str) -> Optional[Dict]:
        """Get attack status"""
        return self.attack_coordinator.get_attack_status(attack_id)
    
    def get_all_attacks(self) -> Dict[str, Dict]:
        """Get all attacks"""
        return self.attack_coordinator.get_all_attacks()
    
    def stop_attack(self, attack_id: str):
        """Stop an attack"""
        self.attack_coordinator.stop_attack(attack_id)
    
    def get_available_workers(self) -> List[Dict]:
        """Get list of available workers (combines legacy TCP and Ray nodes)"""
        workers = []
        with self.lock:
            for wid, info in self.workers.items():
                if info['status'] == 'idle':
                    workers.append({'id': wid, 'name': info['name'], 'ip': info['ip'], 'status': info['status']})
                    
        import ray
        if ray.is_initialized():
            # Always include Ray cluster when it has CPU resources
            if ray.cluster_resources().get('CPU', 0) > 0:
                workers.append({'id': 'ray_cluster_auto', 'name': 'Ray Cluster Nodes', 'ip': 'auto', 'status': 'idle'})
                
        return workers