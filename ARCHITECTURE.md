# NetCluster Backend Architecture

## Complete Folder Structure

```
netcluster/
│
├── core/
│   ├── __init__.py
│   ├── master.py              # Existing UI (MasterNodeWindow)
│   ├── master_backend.py      # NEW: Master backend logic
│   ├── worker.py              # Existing UI (WorkerNodeWindow)
│   ├── worker_backend.py      # NEW: Worker backend logic
│   ├── task_executor.py       # Existing task execution
│   ├── task_manager.py        # NEW: Task queue and distribution
│   └── wordlist_generator.py  # NEW: Safe wordlist generation
│
├── network/
│   ├── __init__.py
│   ├── connection.py          # Existing LogBroadcastServer/LogClient
│   ├── protocol.py            # NEW: JSON message protocol
│   ├── server.py              # NEW: TCP server for master
│   └── client.py              # NEW: TCP client for worker
│
├── ui/
│   ├── __init__.py
│   ├── app.py                 # Existing launcher UI
│   ├── components.py          # Existing UI components
│   └── theme.py               # Existing UI theme
│
├── utils/
│   ├── __init__.py
│   ├── config.py              # NEW: Configuration settings
│   ├── logger.py              # NEW: Logging utility
│   └── helpers.py             # Utility helpers
│
└── __init__.py

main.py                         # Entry point (--master / --worker)
requirements.txt
README.md
```

## Architecture Layers

### 1. Network Layer (`network/`)
- **protocol.py**: JSON message encoding/decoding, message types
- **server.py**: TCP server accepting worker connections
- **client.py**: TCP client connecting to master
- **connection.py**: Existing logging broadcast (kept for compatibility)

### 2. Core Backend (`core/`)
- **master_backend.py**: Master node backend - worker registry, task distribution
- **worker_backend.py**: Worker node backend - task execution
- **task_manager.py**: Task queue, status tracking, timeout handling
- **wordlist_generator.py**: Safe string combination generator

### 3. Utilities (`utils/`)
- **config.py**: Centralized configuration (ports, timeouts, limits)
- **logger.py**: Logging setup utility

### 4. UI Layer (`ui/`)
- **Unchanged**: All existing UI code remains intact
- Frontend can integrate with backend via callbacks

## Import Dependencies (No Circular Imports)

```
network/
  protocol.py → (no internal deps)
  server.py → protocol, logger, config
  client.py → protocol, logger, config

core/
  master_backend.py → network.server, core.task_manager, utils.logger, utils.config
  worker_backend.py → network.client, core.wordlist_generator, utils.logger
  task_manager.py → utils.logger, utils.config
  wordlist_generator.py → utils.logger, utils.config

utils/
  config.py → (no internal deps)
  logger.py → utils.config
```

**No circular dependencies detected** ✅

## Key Features

### Master Backend
- ✅ TCP server on configurable port
- ✅ Worker registration and tracking
- ✅ Heartbeat monitoring
- ✅ Task queue management
- ✅ Round-robin task distribution
- ✅ Task timeout handling
- ✅ Automatic worker cleanup
- ✅ Clean API for frontend

### Worker Backend
- ✅ TCP client connection
- ✅ Automatic registration
- ✅ Heartbeat sending
- ✅ Task execution
- ✅ Result reporting
- ✅ Error handling
- ✅ Auto-reconnect capability

### Task Manager
- ✅ Thread-safe task queue
- ✅ Task status tracking (pending/running/completed/failed/timeout)
- ✅ Task timeout detection
- ✅ Automatic retry on timeout
- ✅ Worker assignment tracking

### Wordlist Generator
- ✅ Safe combination generation
- ✅ Memory-efficient streaming write
- ✅ Configurable limits
- ✅ Progress tracking

## Thread Safety

- All shared data structures use `threading.Lock()`
- Network operations run in separate threads
- UI callbacks use `QTimer.singleShot()` for thread safety
- No blocking operations in main thread

## Configuration

All settings in `netcluster/utils/config.py`:
- Ports (MASTER_PORT, PIN_SERVER_PORT)
- Timeouts (WORKER_TIMEOUT, TASK_TIMEOUT, HEARTBEAT_INTERVAL)
- Limits (MAX_WORKERS, MAX_WORDLIST_COMBINATIONS)
- Logging (LOG_LEVEL, LOG_FORMAT)

## Usage

```bash
# Start master node
python main.py --master

# Start worker node
python main.py --worker

# Start launcher (default)
python main.py
```

## Integration Points

Frontend can integrate backend by:
1. Creating backend instance
2. Setting up callbacks
3. Calling API methods
4. Handling callback events safely (use QTimer for UI updates)

See `BACKEND_INTEGRATION.md` for detailed integration examples.
