# Backend Integration Guide

## Architecture Overview

The backend is cleanly separated from the UI and provides a simple API for the frontend to interact with.

## Master Node Integration

### Initialization

```python
from netcluster.core.master_backend import MasterBackend

# Create backend instance
backend = MasterBackend()

# Setup callbacks (optional)
backend.on_worker_connected = lambda wid, name, ip: print(f"Worker {name} connected")
backend.on_worker_disconnected = lambda wid: print(f"Worker {wid} disconnected")
backend.on_task_status_changed = lambda task_id, status: print(f"Task {task_id}: {status}")

# Start server
backend.start_server()
```

### API Methods

```python
# Get connected workers
workers = backend.get_connected_workers()
# Returns: {worker_id: {'name': str, 'ip': str, 'status': str}}

# Submit a task
task_id = backend.submit_task(
    task_type="wordlist_generate",
    payload={
        "min_length": 4,
        "max_length": 6,
        "use_lower": True,
        "use_upper": False,
        "use_digits": True,
        "output_file": "wordlist.txt"
    },
    timeout=300
)

# Get task status
status = backend.get_task_status(task_id)
# Returns: "pending", "running", "completed", "failed", or "timeout"

# Get all tasks
all_tasks = backend.get_all_tasks()
# Returns: {task_id: {task_type, status, assigned_worker, result, error}}

# Stop server
backend.stop_server()
```

## Worker Node Integration

### Initialization

```python
from netcluster.core.worker_backend import WorkerBackend

# Create backend instance
backend = WorkerBackend(worker_name="MyWorker")

# Setup callbacks (optional)
backend.on_connected = lambda: print("Connected to master")
backend.on_disconnected = lambda: print("Disconnected from master")
backend.on_task_received = lambda task_id, task_type: print(f"Task {task_id} received")
backend.on_task_completed = lambda task_id, success: print(f"Task {task_id} completed: {success}")

# Connect to master
success = backend.connect_to_master(master_ip="127.0.0.1", master_port=50050)

# Check connection status
is_connected = backend.is_connected()

# Disconnect
backend.disconnect()
```

## Frontend Integration Pattern

### Master Node Frontend

The existing `MasterNodeWindow` can integrate with backend like this:

```python
class MasterNodeWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # ... existing UI setup ...
        
        # Initialize backend
        self.backend = MasterBackend()
        self.backend.on_worker_connected = self._on_worker_connected
        self.backend.on_worker_disconnected = self._on_worker_disconnected
        self.backend.on_task_status_changed = self._on_task_status_changed
        self.backend.start_server()
    
    def _on_worker_connected(self, worker_id, name, ip):
        # Update UI - this runs in backend thread
        # Use QTimer.singleShot or signal to update GUI thread safely
        QTimer.singleShot(0, lambda: self.update_worker_list())
    
    def submit_attack_task(self, attack_type, config):
        # Submit task through backend
        task_id = self.backend.submit_task(
            task_type=attack_type,
            payload=config
        )
        return task_id
```

### Worker Node Frontend

The existing `WorkerNodeWindow` can integrate like this:

```python
class WorkerNodeWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # ... existing UI setup ...
        
        # Initialize backend
        self.backend = WorkerBackend(worker_name="Worker")
        self.backend.on_connected = self._on_backend_connected
        self.backend.on_disconnected = self._on_backend_disconnected
    
    def connect_to_master(self):
        ip = self.pin_input.text()  # Get IP from UI
        success = self.backend.connect_to_master(ip, 50050)
        if success:
            self._set_status("connected")
    
    def _on_backend_connected(self):
        # Update UI safely
        QTimer.singleShot(0, lambda: self._set_status("connected"))
```

## Thread Safety

**Important**: Backend callbacks run in network threads, not the GUI thread. Always use `QTimer.singleShot(0, ...)` or PyQt signals to update UI from callbacks.

## Task Types

Currently supported task types:
- `wordlist_generate`: Generate wordlist file

Payload format for `wordlist_generate`:
```python
{
    "min_length": int,
    "max_length": int,
    "use_lower": bool,
    "use_upper": bool,
    "use_digits": bool,
    "output_file": str
}
```

## Error Handling

All backend methods handle errors gracefully and log them. Check return values:
- `connect_to_master()` returns `bool`
- `submit_task()` returns `str` (task_id) or raises exception
- `get_task_status()` returns `None` if task not found
