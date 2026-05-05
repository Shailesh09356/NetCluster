"""
Worker Backend - Core backend logic for worker node
"""
import threading
import uuid
from typing import Optional, Callable, Dict
from netcluster.network.client import NetworkClient
from netcluster.core.wordlist_generator import generate_wordlist
from netcluster.core.attacks.executor import AttackExecutor
from netcluster.utils.logger import setup_logger
from netcluster.utils.config import TASK_TIMEOUT

logger = setup_logger(__name__)


class WorkerBackend:
    """Backend for worker node - executes tasks from master"""
    
    def __init__(self, worker_name: str = "Worker"):
        self.worker_id = str(uuid.uuid4())
        self.worker_name = worker_name
        self.network_client: Optional[NetworkClient] = None
        self.master_ip: Optional[str] = None
        self.master_port: Optional[int] = None
        
        # Attack executor
        self.attack_executor = AttackExecutor(
            self.worker_id,
            self._send_attack_result,
            self._send_attack_log
        )
        
        # Callbacks for frontend
        self.on_connected: Optional[Callable[[], None]] = None
        self.on_disconnected: Optional[Callable[[], None]] = None
        self.on_task_received: Optional[Callable[[str, str], None]] = None
        self.on_task_completed: Optional[Callable[[str, bool], None]] = None
        self.on_attack_log: Optional[Callable[[str], None]] = None    # fn(msg) -> worker attack_terminal
        self.on_attack_result: Optional[Callable[[str], None]] = None  # fn(msg) -> worker attack_terminal (success/fail)
    
    def connect_to_master(self, master_ip: str, master_port: int, num_cpus: int = 0) -> bool:
        """
        Connect to master node
        
        Args:
            master_ip: Master node IP address
            master_port: Master node port
            num_cpus: Custom number of CPUs for Ray (0 for auto)
            
        Returns:
            True if connection successful
        """
        self.master_ip = master_ip
        self.master_port = master_port
        
        if self.network_client:
            self.network_client.disconnect()
        
        self.network_client = NetworkClient(
            master_ip,
            master_port,
            self.worker_id,
            self.worker_name
        )
        
        # Initialize Ray Worker
        # IMPORTANT: on local loopback, skip 'ray stop' to avoid killing master's Ray head
        import ray
        import subprocess
        is_local = master_ip in ('127.0.0.1', 'localhost', '::1')
        try:
            if is_local:
                logger.info("Same-machine mode: connecting to existing local Ray cluster")
                if not ray.is_initialized():
                    try:
                        ray.init(address="auto", _redis_password="netcluster",
                                 ignore_reinit_error=True)
                    except Exception:
                        pass  # Non-fatal — TCP task path still works
            else:
                logger.info(f"Connecting Ray Worker to {master_ip}...")
                subprocess.run(["ray", "stop", "--force"], capture_output=True, timeout=15)
                cmd = ["ray", "start", f"--address={master_ip}:6379",
                       "--redis-password=netcluster"]
                if num_cpus > 0:
                    cmd.append(f"--num-cpus={num_cpus}")
                subprocess.run(cmd, capture_output=True, timeout=30)
                logger.info("Ray Worker connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect Ray Worker: {e}")
        

        # Setup callbacks
        self.network_client.on_connected = self._on_connected
        self.network_client.on_disconnected = self._on_disconnected
        self.network_client.on_task_received = self._on_task_received
        
        success = self.network_client.connect()
        return success
    
    def disconnect(self):
        """Disconnect from master"""
        if self.network_client:
            self.network_client.disconnect()
            self.network_client = None
    
    def is_connected(self) -> bool:
        """Check if connected to master"""
        return self.network_client is not None and self.network_client.is_connected()
    
    def _on_connected(self):
        """Handle connection to master"""
        logger.info("Connected to master")
        if self.on_connected:
            try:
                self.on_connected()
            except Exception as e:
                logger.error(f"Error in on_connected callback: {e}")
    
    def _on_disconnected(self):
        """Handle disconnection from master"""
        logger.info("Disconnected from master")
        if self.on_disconnected:
            try:
                self.on_disconnected()
            except Exception as e:
                logger.error(f"Error in on_disconnected callback: {e}")
        
        # Auto-reconnect logic could go here if needed
    
    def _on_task_received(self, message: Dict):
        """Handle task received from master"""
        task_id = message.get('task_id')
        payload = message.get('payload', {})
        task_type = payload.get('task_type')
        task_payload = payload.get('payload', {}) if 'payload' in payload else payload
        
        logger.info(f"Task received: {task_id} ({task_type})")
        
        if self.on_task_received:
            try:
                self.on_task_received(task_id, task_type)
            except Exception as e:
                logger.error(f"Error in on_task_received callback: {e}")
        
        # Execute task in background thread
        task_thread = threading.Thread(
            target=self._execute_task,
            args=(task_id, task_type, task_payload),
            daemon=True
        )
        task_thread.start()
    
    def _execute_task(self, task_id: str, task_type: str, payload: Dict):
        """Execute a task"""
        try:
            if task_type == "wordlist_generate":
                result = self._execute_wordlist_generation(payload)
                success = True
                error = None
            elif task_type == "bruteforce_attack":
                # Wordlist-based attack
                # Store task_id in payload for executor
                payload['_task_id'] = task_id
                self.attack_executor.execute_wordlist_attack(payload)
                return  # Attack executor will send result via callback
            elif task_type == "bruteforce_generation_attack":
                # Generation-based attack
                # Store task_id in payload for executor
                payload['_task_id'] = task_id
                self.attack_executor.execute_generation_attack(payload)
                return  # Attack executor will send result via callback
            else:
                result = None
                success = False
                error = f"Unknown task type: {task_type}"
            
            # Send result back to master
            if self.network_client:
                self.network_client.send_result(task_id, success, result, error)
            
            if self.on_task_completed:
                try:
                    self.on_task_completed(task_id, success)
                except Exception as e:
                    logger.error(f"Error in on_task_completed callback: {e}")
        
        except Exception as e:
            logger.error(f"Error executing task {task_id}: {e}")
            if self.network_client:
                self.network_client.send_result(task_id, False, None, str(e))
            
            if self.on_task_completed:
                try:
                    self.on_task_completed(task_id, False)
                except Exception as e:
                    logger.error(f"Error in on_task_completed callback: {e}")
    
    def _send_attack_result(self, result: Dict):
        """Send attack result to master"""
        if self.network_client:
            # Use _task_id if available (from executor), otherwise use attack_id
            task_id = result.get('_task_id') or result.get('attack_id', 'unknown')
            success = result.get('success', False)
            self.network_client.send_result(task_id, success, result, result.get('error'))
        
        if self.on_task_completed:
            try:
                task_id = result.get('_task_id') or result.get('attack_id', 'unknown')
                success = result.get('success', False)
                self.on_task_completed(task_id, success)
            except Exception as e:
                logger.error(f"Error in on_task_completed callback: {e}")
    
    def _send_attack_log(self, message: str):
        """Forward attack progress log to the worker's Attack Results terminal"""
        logger.info(f"Attack log: {message}")
        if self.on_attack_log:
            try:
                self.on_attack_log(message)
            except Exception as e:
                logger.error(f"Error in on_attack_log callback: {e}")
    
    def _execute_wordlist_generation(self, payload: Dict) -> Dict:
        """Execute wordlist generation task"""
        min_length = payload.get('min_length', 4)
        max_length = payload.get('max_length', 6)
        use_lower = payload.get('use_lower', True)
        use_upper = payload.get('use_upper', False)
        use_digits = payload.get('use_digits', False)
        output_file = payload.get('output_file', f'wordlist_{uuid.uuid4().hex[:8]}.txt')
        
        total_generated, file_path, generation_time = generate_wordlist(
            min_length=min_length,
            max_length=max_length,
            use_lower=use_lower,
            use_upper=use_upper,
            use_digits=use_digits,
            output_file=output_file
        )
        
        return {
            'total_generated': total_generated,
            'file_path': file_path,
            'generation_time': generation_time
        }
