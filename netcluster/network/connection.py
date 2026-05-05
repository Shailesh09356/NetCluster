"""
NetCluster Network Module - Master-controlled logging and worker communication
Logs are generated ONLY by Master Node. Workers receive read-only synced messages.
"""
import socket
import threading
from datetime import datetime
from typing import Optional, Callable


def _format_master_log(msg: str) -> str:
    """Format log message: [HH:MM:SS] [MASTER] <msg>"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    return f"[{timestamp}] [MASTER] {msg}"


class LogBroadcastServer:
    """
    Master-centric logging server.
    - Maintains centralized immutable log history
    - Broadcasts new logs to all connected workers in real time
    - Sends full history to newly connected workers
    - Workers cannot inject or modify logs
    """
    def __init__(self, host='0.0.0.0', port=50050):
        self.host = host
        self.port = port
        self.server = None
        self.clients = []
        self.worker_info = {}
        self.running = False
        self.lock = threading.Lock()
        # Centralized log history - immutable after creation
        self._log_history = []
        # Callbacks for Master to log worker connect/disconnect (called from network thread)
        self.on_worker_connected: Optional[Callable[[str, str], None]] = None
        self.on_worker_disconnected: Optional[Callable[[str, str], None]] = None
        # Callback for worker log messages (called from network thread)
        self.on_worker_log: Optional[Callable[[str, str], None]] = None  # worker_name, message

    def start_server(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((self.host, self.port))
        self.server.listen(5)
        self.running = True
        threading.Thread(target=self.accept_clients, daemon=True).start()

    def accept_clients(self):
        while self.running:
            try:
                client, addr = self.server.accept()
                with self.lock:
                    self.clients.append(client)
                    self.worker_info[client] = {
                        'ip': addr[0],
                        'name': f"Worker-{len(self.clients):02d}",
                        'tasks': 0,
                        'status': '🟢 Active'
                    }
                threading.Thread(target=self._handle_client, args=(client,), daemon=True).start()
            except Exception:
                break

    def _handle_client(self, client):
        worker_name = None
        worker_ip = None
        try:
            first_msg = True
            while self.running:
                data = client.recv(1024)
                if not data:
                    break
                if first_msg and data.startswith(b'WORKER_NAME:'):
                    worker_name = data.decode('utf-8', errors='ignore').split(':', 1)[1].strip()
                    with self.lock:
                        if client in self.worker_info:
                            self.worker_info[client]['name'] = worker_name
                            worker_ip = self.worker_info[client]['ip']
                    first_msg = False
                    # Send full log history to newly connected worker
                    self._send_history_to_client(client)
                    # Notify Master to log worker connected
                    if self.on_worker_connected and worker_name:
                        try:
                            self.on_worker_connected(worker_name, worker_ip or '')
                        except Exception:
                            pass
                    continue
                
                # Check for worker log messages (format: WORKER_LOG:worker_name:message)
                if data.startswith(b'WORKER_LOG:'):
                    try:
                        parts = data.decode('utf-8', errors='ignore').split(':', 2)
                        if len(parts) >= 3:
                            log_worker_name = parts[1].strip()
                            log_message = parts[2].strip()
                            if self.on_worker_log and log_worker_name:
                                try:
                                    self.on_worker_log(log_worker_name, log_message)
                                except Exception:
                                    pass
                    except Exception:
                        pass
                    continue
                
                first_msg = False
        except Exception:
            pass
        finally:
            with self.lock:
                if client in self.worker_info:
                    worker_name = self.worker_info[client].get('name', 'Unknown')
                    worker_ip = self.worker_info[client].get('ip', '')
                if client in self.clients:
                    self.clients.remove(client)
                if client in self.worker_info:
                    del self.worker_info[client]
            try:
                client.close()
            except Exception:
                pass
            # Notify Master to log worker disconnected
            if self.on_worker_disconnected and worker_name:
                try:
                    self.on_worker_disconnected(worker_name, worker_ip or '')
                except Exception:
                    pass

    def _send_history_to_client(self, client):
        """Send full log history to a single client (thread-safe)."""
        with self.lock:
            history = list(self._log_history)
        for line in history:
            try:
                client.sendall(line.encode('utf-8') + b'\n')
            except Exception:
                return

    def add_master_log(self, msg: str) -> str:
        """
        Add a master log entry. Format: [HH:MM:SS] [MASTER] <msg>
        - Appends to centralized history
        - Broadcasts to all connected workers
        - Prevents duplicate consecutive entries
        Returns the formatted log line.
        """
        formatted = _format_master_log(msg)
        with self.lock:
            # Deduplication: skip if identical to last log (prevents double-add from race)
            if self._log_history and self._log_history[-1] == formatted:
                return formatted
            self._log_history.append(formatted)
        self._broadcast(formatted)
        return formatted

    def _broadcast(self, message: str):
        """Send a raw message to all connected clients (internal use)."""
        data = message.encode('utf-8') + b'\n'
        with self.lock:
            for client in self.clients[:]:
                try:
                    client.sendall(data)
                except Exception:
                    if client in self.clients:
                        self.clients.remove(client)
                    if client in self.worker_info:
                        del self.worker_info[client]
                    try:
                        client.close()
                    except Exception:
                        pass

    def broadcast_log(self, message: str):
        """
        Broadcast a raw message to all clients WITHOUT adding to log history.
        Used for control messages: [SETTINGS], [PIN_CHANGED], etc.
        """
        self._broadcast(message)

    def get_log_history(self):
        """Get a copy of the log history (read-only)."""
        with self.lock:
            return list(self._log_history)

    def stop(self):
        self.running = False
        if self.server:
            try:
                self.server.close()
            except Exception:
                pass
        with self.lock:
            for client in self.clients[:]:
                try:
                    client.close()
                except Exception:
                    pass
            self.clients.clear()
            self.worker_info.clear()

    def get_worker_info(self):
        with self.lock:
            return self.worker_info.copy()

    def update_worker_status(self, client, status):
        with self.lock:
            if client in self.worker_info:
                self.worker_info[client]['status'] = status

    def update_worker_tasks(self, client, tasks):
        with self.lock:
            if client in self.worker_info:
                self.worker_info[client]['tasks'] = tasks


# --- Worker Node Side ---
class LogClient:
    """Read-only log client. Receives logs from Master; cannot inject or modify."""
    def __init__(self, master_ip, port=50050, on_log=None, worker_name=None):
        self.master_ip = master_ip
        self.port = port
        self.sock = None
        self.running = False
        self.on_log = on_log
        self.worker_name = worker_name

    def start_client(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((self.master_ip, self.port))
            if self.worker_name:
                self.sock.sendall(f"WORKER_NAME:{self.worker_name}\n".encode('utf-8'))
            self.running = True
            threading.Thread(target=self._receive_logs, daemon=True).start()
            return True
        except Exception:
            return False

    def _receive_logs(self):
        buffer = b''
        while self.running:
            try:
                data = self.sock.recv(1024)
                if not data:
                    break
                buffer += data
                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    decoded = line.decode('utf-8', errors='ignore')
                    if decoded and self.on_log:
                        self.on_log(decoded)
            except Exception:
                break
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass

    def send_worker_log(self, message: str):
        """
        Send a log message from worker to master
        
        Args:
            message: Log message to send
        """
        if self.running and self.sock:
            try:
                log_msg = f"WORKER_LOG:{self.worker_name}:{message}\n".encode('utf-8')
                self.sock.sendall(log_msg)
            except Exception:
                pass
    
    def stop(self):
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
