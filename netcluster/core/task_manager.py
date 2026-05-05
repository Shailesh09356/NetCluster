"""
Task Manager - Handles task queue and distribution
"""
import queue
import threading
import time
from typing import Dict, Optional, Callable, Any
from enum import Enum
from netcluster.utils.logger import setup_logger
from netcluster.utils.config import TASK_TIMEOUT, MAX_TASK_RETRIES

logger = setup_logger(__name__)


class TaskStatus(Enum):
    """Task status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class Task:
    """Task representation"""
    def __init__(self, task_id: str, task_type: str, payload: Dict, timeout: int = TASK_TIMEOUT):
        self.task_id = task_id
        self.task_type = task_type
        self.payload = payload
        self.status = TaskStatus.PENDING
        self.created_at = time.time()
        self.started_at: Optional[float] = None
        self.completed_at: Optional[float] = None
        self.assigned_worker: Optional[str] = None
        self.result: Optional[Any] = None
        self.error: Optional[str] = None
        self.timeout = timeout
        self.retry_count = 0
    
    def is_expired(self) -> bool:
        """Check if task has exceeded timeout"""
        if self.started_at is None:
            return False
        elapsed = time.time() - self.started_at
        return elapsed > self.timeout
    
    def can_retry(self) -> bool:
        """Check if task can be retried"""
        return self.retry_count < MAX_TASK_RETRIES


class TaskManager:
    """Manages task queue and distribution"""
    
    def __init__(self):
        self.task_queue: queue.Queue = queue.Queue()
        self.tasks: Dict[str, Task] = {}
        self.lock = threading.Lock()
        self.on_task_status_changed: Optional[Callable[[str, TaskStatus], None]] = None
    
    def submit_task(self, task_type: str, payload: Dict, timeout: int = TASK_TIMEOUT) -> str:
        """
        Submit a new task to the queue
        
        Args:
            task_type: Type of task
            payload: Task payload
            timeout: Task timeout in seconds
            
        Returns:
            Task ID
        """
        from netcluster.network.protocol import Protocol
        task_id = Protocol.generate_task_id()
        
        task = Task(task_id, task_type, payload, timeout)
        
        with self.lock:
            self.tasks[task_id] = task
        
        self.task_queue.put(task_id)
        logger.info(f"Task submitted: {task_id} ({task_type})")
        
        return task_id
    
    def get_next_task(self) -> Optional[Task]:
        """
        Get next pending task from queue
        
        Returns:
            Task object or None if queue is empty
        """
        try:
            task_id = self.task_queue.get_nowait()
            with self.lock:
                task = self.tasks.get(task_id)
                if task and task.status == TaskStatus.PENDING:
                    return task
                # If task is not pending, put it back or skip
                if task and task.status == TaskStatus.PENDING:
                    self.task_queue.put(task_id)
        except queue.Empty:
            pass
        return None
    
    def assign_task(self, task_id: str, worker_id: str) -> bool:
        """
        Assign a task to a worker
        
        Args:
            task_id: Task ID
            worker_id: Worker ID
            
        Returns:
            True if assignment successful
        """
        with self.lock:
            task = self.tasks.get(task_id)
            if not task or task.status != TaskStatus.PENDING:
                return False
            
            task.status = TaskStatus.RUNNING
            task.assigned_worker = worker_id
            task.started_at = time.time()
        
        self._notify_status_change(task_id, TaskStatus.RUNNING)
        logger.info(f"Task {task_id} assigned to worker {worker_id}")
        return True
    
    def complete_task(self, task_id: str, result: Any, success: bool = True, error: Optional[str] = None) -> bool:
        """
        Mark task as completed
        
        Args:
            task_id: Task ID
            result: Task result
            success: Whether task succeeded
            error: Error message if failed
            
        Returns:
            True if task found and updated
        """
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                return False
            
            task.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
            task.completed_at = time.time()
            task.result = result
            task.error = error
        
        self._notify_status_change(task_id, task.status)
        logger.info(f"Task {task_id} completed: success={success}")
        return True
    
    def timeout_task(self, task_id: str) -> bool:
        """
        Mark task as timed out and requeue if retries available
        
        Args:
            task_id: Task ID
            
        Returns:
            True if task found
        """
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                return False
            
            task.status = TaskStatus.TIMEOUT
            task.completed_at = time.time()
            task.error = "Task timeout"
            
            # Requeue if retries available
            if task.can_retry():
                task.retry_count += 1
                task.status = TaskStatus.PENDING
                task.started_at = None
                task.assigned_worker = None
                self.task_queue.put(task_id)
                logger.info(f"Task {task_id} requeued (retry {task.retry_count}/{MAX_TASK_RETRIES})")
        
        self._notify_status_change(task_id, task.status)
        return True
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        with self.lock:
            return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> Dict[str, Task]:
        """Get all tasks"""
        with self.lock:
            return self.tasks.copy()
    
    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """Get task status"""
        task = self.get_task(task_id)
        return task.status if task else None
    
    def check_timeouts(self):
        """Check for timed out tasks"""
        with self.lock:
            for task_id, task in list(self.tasks.items()):
                if task.status == TaskStatus.RUNNING and task.is_expired():
                    self.timeout_task(task_id)
    
    def _notify_status_change(self, task_id: str, status: TaskStatus):
        """Notify callback of status change"""
        if self.on_task_status_changed:
            try:
                self.on_task_status_changed(task_id, status)
            except Exception as e:
                logger.error(f"Error in task status callback: {e}")
