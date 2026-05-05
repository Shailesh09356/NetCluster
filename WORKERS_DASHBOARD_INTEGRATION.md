# Workers Dashboard Integration

## Overview

The Workers Dashboard has been successfully integrated into the Master Node UI. It displays live execution logs for each connected worker node.

## New Components

### 1. WorkerLogCard (`netcluster/ui/worker_dashboard.py`)
- Displays individual worker information and logs
- Features:
  - Worker name header
  - Status indicator (Green = connected, Red = disconnected)
  - IP address and task count display
  - Read-only terminal area with auto-scroll
  - Dark terminal styling matching attack terminal

### 2. WorkersDashboardPage (`netcluster/ui/worker_dashboard.py`)
- Main dashboard page with scrollable grid layout
- Features:
  - Responsive 2-column grid layout
  - Dynamic card creation/removal
  - Auto-wrapping for multiple workers
  - Scrollable container

## Integration Points

### Signals Added to MasterNodeWindow

```python
worker_log_signal = pyqtSignal(str, str)  # worker_name, message
worker_connected_signal = pyqtSignal(str, str)  # worker_name, ip
worker_disconnected_signal = pyqtSignal(str)  # worker_name
```

### Signal Connections

```python
self.worker_log_signal.connect(self._on_worker_log_received)
self.worker_connected_signal.connect(self._on_worker_connected_ui)
self.worker_disconnected_signal.connect(self._on_worker_disconnected_ui)
```

### LogBroadcastServer Extension

Added minimal callback support:
```python
self.log_server.on_worker_log = self._on_worker_log_callback
```

Workers can send logs using:
```python
log_client.send_worker_log("Task execution started")
```

## Navigation

New navbar button added:
- **"Workers Dashboard"** - Switches to section index 4
- Positioned after "Workers" button
- Uses same styling as other nav buttons

## Section Index Mapping

- 0: Attacks
- 1: Dashboard
- 2: Settings
- 3: Workers (table view)
- 4: Workers Dashboard (NEW - live logs)

## Thread Safety

All UI updates use PyQt signals:
- Network callbacks → Signals → GUI thread slots
- No direct UI updates from network threads
- Safe for PyQt integration

## Dynamic Behavior

- **Worker connects**: Card created automatically
- **Worker disconnects**: Card marked as disconnected (red indicator)
- **Worker reconnects**: Card status restored to connected
- **Logs received**: Appended to appropriate worker card terminal

## Worker Log Format

Workers send logs using format:
```
WORKER_LOG:worker_name:log_message
```

Example:
```
WORKER_LOG:Worker-01:Task execution completed successfully
```

## UI Features

- **Auto-scroll**: Terminal automatically scrolls to bottom on new log
- **Status indicators**: Visual connection status
- **Task count**: Shows number of tasks assigned to worker
- **Responsive layout**: 2 cards per row, wraps automatically
- **Dark theme**: Matches existing terminal styling

## Code Structure

```
netcluster/
├── ui/
│   └── worker_dashboard.py    # NEW: WorkerLogCard + WorkersDashboardPage
│
├── core/
│   └── master.py              # UPDATED: Added dashboard integration
│
└── network/
    └── connection.py          # UPDATED: Added worker log callback
```

## Usage

1. Start Master Node
2. Workers connect automatically
3. Navigate to "Workers Dashboard" tab
4. View live logs for each worker
5. Logs update in real-time as workers send messages

## Notes

- Existing Attack Results and Master Logs terminals remain unchanged
- No backend logic modified (only UI extensions)
- Thread-safe signal-based updates
- Clean modular structure
