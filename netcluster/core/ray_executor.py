import ray
import time
import os
import socket
from netcluster.core.attacks.executor import AttackExecutor
from netcluster.utils.logger import setup_logger

logger = setup_logger(__name__)

@ray.remote
def ray_execute_attack(task_data, master_ip=None, timeout=None):
    """
    Ray remote task to execute an attack chunk.
    It returns the resulting dictionary.
    """
    # Simple log callback that prints to stdout (captured by ray)
    def send_log(msg):
        print(f"[Ray Worker] {msg}")

    # We will collect results via a callback, then return them.
    results = []
    def send_result(res):
        results.append(res)
        
    executor = AttackExecutor("RayWorker", send_result, send_log)
    
    # Check attack type
    task_type = task_data.get('task_type', '')
    if 'generation' in task_type:
        executor.execute_generation_attack(task_data)
    else:
        executor.execute_wordlist_attack(task_data)
        
    if results:
        # Return the last relevant result
        return results[-1]
    
    # Fallback
    return {
        'attack_id': task_data.get('attack_id'),
        'success': False,
        'error': 'No result triggered'
    }

