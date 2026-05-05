"""
Distributed Attack Coordinator
Manages brute force attacks across multiple worker nodes
"""
import time
import threading
import hashlib
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from netcluster.utils.logger import setup_logger
from netcluster.core.attacks import AttackType, AttackStatus, AttackResult
import ray
try:
    from netcluster.core.ray_executor import ray_execute_attack
except ImportError:
    pass

logger = setup_logger(__name__)


@dataclass
class AttackTask:
    """Represents a distributed brute force attack"""
    task_id: str
    attack_type: str
    target: str
    port: Optional[int]
    username: Optional[str]
    username_list: Optional[str]  # File path
    password_list: Optional[str]   # File path
    protocol_config: Dict[str, Any] = field(default_factory=dict)
    
    # Attack parameters
    min_length: int = 4
    max_length: int = 8
    charset: str = "abcdefghijklmnopqrstuvwxyz0123456789"
    
    # Distribution
    workers_assigned: List[str] = field(default_factory=list)
    worker_chunks: Dict[str, dict] = field(default_factory=dict)
    results: Dict[str, Any] = field(default_factory=dict)
    
    # Status
    status: str = 'pending'
    start_time: float = None
    end_time: float = None
    attempts: int = 0
    found_password: Optional[str] = None
    found_username: Optional[str] = None
    speed: float = 0  # attempts per second
    
    # Wordlist mode vs Generation mode
    use_wordlist: bool = True
    wordlist_file: Optional[str] = None


class AttackCoordinator:
    """
    Coordinates distributed brute force attacks
    Uses existing task_manager for distribution
    """
    
    def __init__(self, task_manager, worker_registry=None):
        self.task_manager = task_manager
        self.worker_registry = worker_registry
        self.active_attacks: Dict[str, AttackTask] = {}
        self.lock = threading.Lock()
        self.results_dir = "attack_results"
        os.makedirs(self.results_dir, exist_ok=True)
        self.ray_refs = {}  # {future: task_id}
        
        # Setup task status callback
        self.task_manager.on_task_status_changed = self._on_task_status_changed
        # Optional log callback so master UI can receive per-attempt logs
        self.log_callback = None  # set externally: fn(worker_name, msg)
        self.attack_result_callback = None  # set externally: fn(msg) -> Attack Results terminal
    
    def create_attack(self, attack_config: dict) -> str:
        """
        Create a new distributed attack
        Returns attack_id
        """
        attack_id = f"attack_{int(time.time())}_{hashlib.md5(str(attack_config).encode()).hexdigest()[:8]}"
        
        # Create attack task
        attack = AttackTask(
            task_id=attack_id,
            attack_type=attack_config['type'],
            target=attack_config['target'],
            port=attack_config.get('port'),
            username=attack_config.get('username'),
            username_list=attack_config.get('username_list'),
            password_list=attack_config.get('password_list'),
            protocol_config=attack_config.get('protocol_config', {}),
            min_length=attack_config.get('min_length', 4),
            max_length=attack_config.get('max_length', 8),
            charset=attack_config.get('charset', 'abcdefghijklmnopqrstuvwxyz0123456789'),
            use_wordlist=attack_config.get('use_wordlist', True),
            start_time=time.time()
        )
        
        with self.lock:
            self.active_attacks[attack_id] = attack
        
        # Start attack distribution
        threading.Thread(target=self._distribute_attack, args=(attack_id,), daemon=True).start()
        
        logger.info(f"Created attack: {attack_id} ({attack.attack_type})")
        return attack_id
    
    def _distribute_attack(self, attack_id: str):
        """
        Distribute attack workload to workers using task_manager
        """
        attack = self.active_attacks.get(attack_id)
        if not attack:
            return
        
        attack.status = 'distributing'
        
        # Wait for at least one worker to be available (Ray may still be initialising)
        # Retry up to 40 seconds so attacks started right after master launch still work
        worker_ids = []
        for _attempt in range(40):
            if self.worker_registry and hasattr(self.worker_registry, 'get_available_workers'):
                workers = self.worker_registry.get_available_workers()
                worker_ids = [w['id'] for w in workers]
            if worker_ids:
                break
            time.sleep(1)
        
        if not worker_ids:
            attack.status = 'failed'
            attack.end_time = time.time()
            logger.warning(f"No workers available for attack {attack_id}")
            if self.attack_result_callback:
                try:
                    self.attack_result_callback(
                        f"\u274c No workers / Ray CPUs available. Start a worker or wait for Ray to initialise."
                    )
                except Exception:
                    pass
            return
        
        # Separate real TCP workers from the Ray pseudo-worker
        tcp_workers = [w for w in worker_ids if w != 'ray_cluster_auto']
        has_ray    = 'ray_cluster_auto' in worker_ids
        
        if has_ray:
            # Always prefer Ray when the cluster has CPUs — it uses ALL
            # cluster resources (master + remote workers) automatically
            use_ray = True
            effective_workers = ['ray_cluster_auto']
        elif tcp_workers:
            # Fallback to direct TCP workers when Ray isn't available
            use_ray = False
            effective_workers = tcp_workers
        else:
            attack.status = 'failed'
            return
        
        if attack.use_wordlist and attack.password_list:
            self._distribute_wordlist_attack(attack_id, effective_workers, use_ray)
        else:
            self._distribute_generation_attack(attack_id, effective_workers, use_ray)
    
    def _distribute_wordlist_attack(self, attack_id: str, worker_ids: list, use_ray: bool = False):
        """Distribute passwords from wordlist to workers"""
        attack = self.active_attacks.get(attack_id)
        if not attack:
            return
        
        if not attack.password_list or not os.path.exists(attack.password_list):
            attack.status = 'failed'
            logger.error(f"Wordlist file not found: {attack.password_list}")
            if self.attack_result_callback:
                try:
                    self.attack_result_callback(f"❌ Wordlist not found: {attack.password_list}")
                except Exception:
                    pass
            return
        
        # Count lines in wordlist
        try:
            with open(attack.password_list, 'r', encoding='utf-8', errors='ignore') as f:
                total_passwords = sum(1 for _ in f)
        except Exception as e:
            logger.error(f"Error reading wordlist: {e}")
            attack.status = 'failed'
            return
        
        if total_passwords == 0:
            attack.status = 'failed'
            return
        
        if self.attack_result_callback:
            try:
                self.attack_result_callback(
                    f"📊 Wordlist: {total_passwords} passwords ÷ {len(worker_ids)} worker(s)"
                    + (" [Ray]" if use_ray else " [TCP]")
                )
            except Exception:
                pass
        
        # Split wordlist into chunks for each worker
        chunk_size = total_passwords // len(worker_ids)
        remainder = total_passwords % len(worker_ids)
        
        start_line = 0
        for i, worker_id in enumerate(worker_ids):
            end_line = start_line + chunk_size + (1 if i < remainder else 0)
            
            task_payload = {
                'attack_id': attack_id,
                'attack_type': attack.attack_type,
                'target': attack.target,
                'port': attack.port,
                'username': attack.username,
                'username_list': attack.username_list,
                'wordlist_file': attack.password_list,
                'start_line': start_line,
                'end_line': end_line,
                'protocol_config': attack.protocol_config,
                'task_type': 'bruteforce_attack'
            }
            
            task_id = f"ray_{int(time.time() * 1000)}_{worker_id}"
            task_payload['_task_id'] = task_id
            
            if use_ray:
                # Dispatch to Ray cluster
                dispatched = False
                try:
                    future = ray_execute_attack.remote(task_payload)
                    self.ray_refs[future] = task_id
                    dispatched = True
                except Exception as e:
                    logger.error(f"Ray dispatch error: {e} | Falling back to local thread execution")
                
                if not dispatched:
                    # Ray not ready — run locally in a daemon thread so results still come back
                    threading.Thread(
                        target=self._run_locally_fallback,
                        args=(task_id, task_payload),
                        daemon=True
                    ).start()
            else:
                # Dispatch via TCP task_manager (goes to real Worker nodes)
                submitted_id = self.task_manager.submit_task(
                    'bruteforce_attack', task_payload, timeout=3600
                )
                task_id = submitted_id
            
            attack.worker_chunks[worker_id] = {
                'task_id': task_id,
                'start_line': start_line,
                'end_line': end_line
            }
            attack.workers_assigned.append(worker_id)
            start_line = end_line
        
        attack.status = 'running'
        logger.info(f"Attack {attack_id} distributed to {len(worker_ids)} workers ({'Ray' if use_ray else 'TCP'})")
        if use_ray:
            threading.Thread(target=self._monitor_ray_results, daemon=True).start()

    
    def _distribute_generation_attack(self, attack_id: str, worker_ids: list, use_ray: bool = False):
        """Distribute keyspace for generation-based attack"""
        attack = self.active_attacks.get(attack_id)
        if not attack:
            return
        
        charset_size = len(attack.charset)
        
        # Calculate total combinations
        total = 0
        for length in range(attack.min_length, attack.max_length + 1):
            total += charset_size ** length
        
        if total == 0:
            attack.status = 'failed'
            return
        
        if self.attack_result_callback:
            try:
                self.attack_result_callback(
                    f"📊 Generation: {total:,} combos ÷ {len(worker_ids)} worker(s)"
                    + (" [Ray]" if use_ray else " [TCP]")
                )
            except Exception:
                pass
        
        # Calculate chunks
        chunk_size = total // len(worker_ids)
        remainder = total % len(worker_ids)
        
        start_idx = 0
        for i, worker_id in enumerate(worker_ids):
            end_idx = start_idx + chunk_size + (1 if i < remainder else 0) - 1
            
            task_payload = {
                'attack_id': attack_id,
                'attack_type': attack.attack_type,
                'target': attack.target,
                'port': attack.port,
                'username': attack.username,
                'charset': attack.charset,
                'min_length': attack.min_length,
                'max_length': attack.max_length,
                'start_idx': start_idx,
                'end_idx': end_idx,
                'protocol_config': attack.protocol_config,
                'task_type': 'bruteforce_generation_attack'
            }
            
            task_id = f"ray_{int(time.time() * 1000)}_{worker_id}"
            task_payload['_task_id'] = task_id
            
            if use_ray:
                dispatched = False
                try:
                    future = ray_execute_attack.remote(task_payload)
                    self.ray_refs[future] = task_id
                    dispatched = True
                except Exception as e:
                    logger.error(f"Ray dispatch error: {e} | Falling back to local thread execution")
                
                if not dispatched:
                    threading.Thread(
                        target=self._run_locally_fallback,
                        args=(task_id, task_payload),
                        daemon=True
                    ).start()
            else:
                submitted_id = self.task_manager.submit_task(
                    'bruteforce_generation_attack', task_payload, timeout=3600
                )
                task_id = submitted_id
            
            attack.worker_chunks[worker_id] = {
                'task_id': task_id,
                'start_idx': start_idx,
                'end_idx': end_idx
            }
            attack.workers_assigned.append(worker_id)
            start_idx = end_idx + 1
        
        attack.status = 'running'
        logger.info(f"Generation attack {attack_id} distributed to {len(worker_ids)} workers ({'Ray' if use_ray else 'TCP'})")
        if use_ray:
            threading.Thread(target=self._monitor_ray_results, daemon=True).start()
    
    def _run_locally_fallback(self, task_id: str, task_payload: dict):
        """Fallback: execute an attack chunk in the current process when Ray is unavailable."""
        from netcluster.core.attacks.executor import AttackExecutor
        
        result_holder = []
        log_holder = []

        def _send_result(r):
            result_holder.append(r)

        def _send_log(msg):
            log_holder.append(msg)
            if self.attack_result_callback:
                try:
                    self.attack_result_callback(f"[Local] {msg}")
                except Exception:
                    pass

        executor = AttackExecutor("LocalFallback", _send_result, _send_log)
        task_type = task_payload.get('task_type', '')
        if 'generation' in task_type:
            executor.execute_generation_attack(task_payload)
        else:
            executor.execute_wordlist_attack(task_payload)

        result = result_holder[-1] if result_holder else {
            'attack_id': task_payload.get('attack_id'),
            'success': False,
            'error': 'No result from local fallback',
            'attempts': 0
        }
        self.handle_worker_result(task_id, result)

    def _monitor_ray_results(self):
        """Monitor Ray futures for returned results"""
        _last_progress_log = 0  # Throttle progress messages
        while self.ray_refs:
            futures = list(self.ray_refs.keys())
            try:
                done_refs, pending = ray.wait(futures, timeout=1.0)
                for done in done_refs:
                    task_id = self.ray_refs.pop(done)
                    try:
                        result = ray.get(done)
                        if isinstance(result, dict):
                            self.handle_worker_result(task_id, result)
                    except Exception as e:
                        logger.error(f"Error fetching ray task {task_id}: {e}")
                
                # Emit periodic progress to the Attack Results terminal
                now = time.time()
                if now - _last_progress_log >= 3 and pending:
                    _last_progress_log = now
                    done_count = len(futures) - len(pending)
                    total_count = len(futures)
                    if self.attack_result_callback:
                        try:
                            self.attack_result_callback(
                                f"⏳ Ray tasks: {done_count}/{total_count} completed, "
                                f"{len(pending)} still running..."
                            )
                        except Exception:
                            pass
            except Exception as e:
                logger.error(f"Ray wait error: {e}")
                time.sleep(1)
    
    def handle_worker_result(self, task_id: str, result: dict):
        """Handle result from worker"""
        attack_id = None
        worker_id = None
        
        with self.lock:
            # Primary lookup: match by task_id stored in worker_chunks
            for aid, attack in self.active_attacks.items():
                for wid, chunk_info in attack.worker_chunks.items():
                    if chunk_info.get('task_id') == task_id:
                        attack_id = aid
                        worker_id = wid
                        break
                if attack_id:
                    break
            
            # Fallback: match by attack_id embedded in the result itself
            if not attack_id:
                result_aid = result.get('attack_id')
                if result_aid and result_aid in self.active_attacks:
                    attack_id = result_aid
                    # Pick first unresolved worker slot
                    attack = self.active_attacks[attack_id]
                    for wid, chunk_info in attack.worker_chunks.items():
                        if wid not in attack.results:
                            worker_id = wid
                            break
        
        if not attack_id:
            logger.warning(f"Result received for unknown task: {task_id} | attack_id in result: {result.get('attack_id')}")
            return
        
        attack = self.active_attacks.get(attack_id)
        if not attack:
            return
        
        with self.lock:
            # Store result
            attack.results[worker_id] = result
            
            # Update attempts count
            attack.attempts += result.get('attempts', 0)
            
            # Check if password found
            if result.get('success'):
                attack.found_password = result.get('password')
                attack.found_username = result.get('username')
                attack.status = 'completed'
                attack.end_time = time.time()
                elapsed = attack.end_time - attack.start_time if attack.start_time else 0
                
                # Log success
                self._log_success(attack, result)
                
                success_msg = (
                    f"✅ SUCCESS [{attack.attack_type}] "
                    f"{attack.found_username}:{attack.found_password} on {attack.target}\n"
                    f"   ⏱ Time: {elapsed:.2f}s | Attempts: {attack.attempts}"
                )
                logger.info(f"Attack {attack_id} SUCCESS: {attack.found_username}:{attack.found_password}")
                if self.attack_result_callback:
                    try:
                        self.attack_result_callback(success_msg)
                    except Exception:
                        pass
            
            # Check if all workers completed
            elif len(attack.results) == len(attack.worker_chunks):
                attack.status = 'completed'
                attack.end_time = time.time()
                elapsed = attack.end_time - attack.start_time if attack.start_time else 0
                self._log_completion(attack)
                done_msg = (
                    f"❌ Attack completed - no password found [{attack.attack_type}] {attack.target}\n"
                    f"   ⏱ Time: {elapsed:.2f}s | Attempts: {attack.attempts}"
                )
                logger.info(f"Attack {attack_id} completed (no success)")
                if self.attack_result_callback:
                    try:
                        self.attack_result_callback(done_msg)
                    except Exception:
                        pass
    
    def _on_task_status_changed(self, task_id: str, status):
        """Handle task status change from task_manager"""
        # This can be used to track individual task progress
        pass
    
    def _log_success(self, attack: AttackTask, result: dict):
        """Log successful attack"""
        log_file = os.path.join(self.results_dir, f"success_{attack.task_id}.txt")
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(f"Attack Successful!\n")
                f.write(f"Target: {attack.target}\n")
                f.write(f"Type: {attack.attack_type}\n")
                f.write(f"Username: {result.get('username', attack.username)}\n")
                f.write(f"Password: {result.get('password')}\n")
                f.write(f"Attempts: {attack.attempts}\n")
                f.write(f"Time: {attack.end_time - attack.start_time:.2f} seconds\n")
                f.write(f"Worker: {result.get('worker_id')}\n")
        except Exception as e:
            logger.error(f"Error writing success log: {e}")
    
    def _log_completion(self, attack: AttackTask):
        """Log attack completion (no success)"""
        log_file = os.path.join(self.results_dir, f"failed_{attack.task_id}.txt")
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(f"Attack Completed - No Success\n")
                f.write(f"Target: {attack.target}\n")
                f.write(f"Type: {attack.attack_type}\n")
                f.write(f"Attempts: {attack.attempts}\n")
                f.write(f"Time: {attack.end_time - attack.start_time:.2f} seconds\n")
        except Exception as e:
            logger.error(f"Error writing completion log: {e}")
    
    def get_attack_status(self, attack_id: str) -> Optional[Dict]:
        """Get current attack status"""
        attack = self.active_attacks.get(attack_id)
        if not attack:
            return None
        
        # Calculate speed
        elapsed = time.time() - attack.start_time if attack.start_time else 0
        if elapsed > 0 and attack.attempts > 0:
            speed = attack.attempts / elapsed
        else:
            speed = 0
        
        # Determine display status
        display_status = attack.status
        if attack.status == 'running' and attack.attempts == 0 and len(attack.results) == 0:
            display_status = 'executing'  # Ray task dispatched but no results yet
        
        return {
            'attack_id': attack.task_id,
            'status': display_status,
            'type': attack.attack_type,
            'target': attack.target,
            'attempts': attack.attempts,
            'speed': speed,
            'workers': len(attack.workers_assigned),
            'completed_workers': len(attack.results),
            'found_password': attack.found_password,
            'found_username': attack.found_username,
            'elapsed': elapsed,
            'progress': (len(attack.results) / len(attack.worker_chunks)) * 100 if attack.worker_chunks else 0
        }
    
    def get_all_attacks(self) -> Dict[str, Dict]:
        """Get all attacks with their status"""
        with self.lock:
            return {
                attack_id: self.get_attack_status(attack_id)
                for attack_id in self.active_attacks.keys()
            }
    
    def stop_attack(self, attack_id: str):
        """Stop an attack"""
        attack = self.active_attacks.get(attack_id)
        if attack:
            attack.status = 'stopped'
            attack.end_time = time.time()
            logger.info(f"Attack {attack_id} stopped")
