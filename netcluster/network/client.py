"""
Network Client - TCP client for worker node
"""
import socket
import threading
import time
from typing import Optional, Callable, Dict, Any
from netcluster.utils.logger import setup_logger
from netcluster.utils.config import HEARTBEAT_INTERVAL
from netcluster.network.protocol import Protocol, MessageType

logger = setup_logger(__name__)


class NetworkClient:
    """TCP client for connecting to master"""
    
    def __init__(self, master_ip: str, master_port: int, worker_id: str, worker_name: str):
        self.master_ip = master_ip
        self.master_port = master_port
        self.worker_id = worker_id
        self.worker_name = worker_name
        self.socket: Optional[socket.socket] = None
        self.running = False
        self.connected = False
        
        # Callbacks
        self.on_connected: Optional[Callable[[], None]] = None
        self.on_disconnected: Optional[Callable[[], None]] = None
        self.on_task_received: Optional[Callable[[Dict], None]] = None
    
    def connect(self) -> bool:
        """Connect to master server"""
        if self.connected:
            return True
        
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((self.master_ip, self.master_port))
            self.socket.settimeout(None)
            
            self.running = True
            self.connected = True
            
            # Send registration
            register_msg = Protocol.create_register_message(self.worker_id, self.worker_name)
            self.socket.sendall(register_msg)
            
            logger.info(f"Connected to master at {self.master_ip}:{self.master_port}")
            
            # Start receive thread
            receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            receive_thread.start()
            
            # Start heartbeat thread
            heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
            heartbeat_thread.start()
            
            if self.on_connected:
                try:
                    self.on_connected()
                except Exception as e:
                    logger.error(f"Error in on_connected callback: {e}")
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to connect to master: {e}")
            self.connected = False
            if self.socket:
                try:
                    self.socket.close()
                except Exception:
                    pass
            return False
    
    def disconnect(self):
        """Disconnect from master"""
        self.running = False
        self.connected = False
        
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
        
        if self.on_disconnected:
            try:
                self.on_disconnected()
            except Exception as e:
                logger.error(f"Error in on_disconnected callback: {e}")
        
        logger.info("Disconnected from master")
    
    def _receive_loop(self):
        """Receive messages from master"""
        buffer = b''
        
        try:
            while self.running and self.connected:
                try:
                    data = self.socket.recv(4096)
                    if not data:
                        break
                    
                    buffer += data
                    
                    # Process complete messages
                    while b'\n' in buffer:
                        line, buffer = buffer.split(b'\n', 1)
                        if line:
                            message = Protocol.decode_message(line)
                            if message:
                                self._process_message(message)
                
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        logger.error(f"Error receiving data: {e}")
                    break
        
        except Exception as e:
            logger.error(f"Receive loop error: {e}")
        finally:
            if self.running:
                self.disconnect()
    
    def _process_message(self, message: Dict):
        """Process received message"""
        msg_type = message.get('type')
        
        if msg_type == MessageType.TASK.value:
            # Forward task to callback
            if self.on_task_received:
                try:
                    self.on_task_received(message)
                except Exception as e:
                    logger.error(f"Error in on_task_received callback: {e}")
        
        elif msg_type == MessageType.ACK.value:
            # ACK received, nothing to do
            pass
    
    def _heartbeat_loop(self):
        """Send periodic heartbeat"""
        while self.running and self.connected:
            time.sleep(HEARTBEAT_INTERVAL)
            
            if self.running and self.connected:
                try:
                    heartbeat_msg = Protocol.create_heartbeat_message(self.worker_id, "idle")
                    self.socket.sendall(heartbeat_msg)
                except Exception as e:
                    logger.error(f"Error sending heartbeat: {e}")
                    if self.running:
                        self.disconnect()
                    break
    
    def send_result(self, task_id: str, success: bool, result: Any, error: Optional[str] = None) -> bool:
        """Send task result to master"""
        if not self.connected:
            return False
        
        try:
            result_msg = Protocol.create_result_message(task_id, success, result, error)
            self.socket.sendall(result_msg)
            return True
        except Exception as e:
            logger.error(f"Error sending result: {e}")
            if self.running:
                self.disconnect()
            return False
    
    def send_error(self, error_msg: str, task_id: Optional[str] = None) -> bool:
        """Send error message to master"""
        if not self.connected:
            return False
        
        try:
            error_msg_bytes = Protocol.create_error_message(error_msg, task_id)
            self.socket.sendall(error_msg_bytes)
            return True
        except Exception as e:
            logger.error(f"Error sending error message: {e}")
            return False
    
    def is_connected(self) -> bool:
        """Check if connected to master"""
        return self.connected
