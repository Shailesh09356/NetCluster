"""
Network Server - TCP server for master node
"""
import socket
import threading
from typing import Dict, Callable, Optional
from netcluster.utils.logger import setup_logger
from netcluster.utils.config import MASTER_PORT
from netcluster.network.protocol import Protocol, MessageType

logger = setup_logger(__name__)


class NetworkServer:
    """TCP server for accepting worker connections"""
    
    def __init__(self, port: int = MASTER_PORT):
        self.port = port
        self.server_socket: Optional[socket.socket] = None
        self.running = False
        self.clients: Dict[socket.socket, Dict] = {}
        self.lock = threading.Lock()
        
        # Callbacks
        self.on_client_connected: Optional[Callable[[socket.socket, str, str], None]] = None
        self.on_client_disconnected: Optional[Callable[[socket.socket], None]] = None
        self.on_message_received: Optional[Callable[[socket.socket, Dict], None]] = None
    
    def start(self):
        """Start the server"""
        if self.running:
            return
        
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('0.0.0.0', self.port))
            self.server_socket.listen(10)
            self.running = True
            
            logger.info(f"Network server started on port {self.port}")
            
            # Start accept thread
            accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
            accept_thread.start()
            
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            self.running = False
            raise
    
    def stop(self):
        """Stop the server"""
        self.running = False
        
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
        
        # Close all client connections
        with self.lock:
            for client_sock in list(self.clients.keys()):
                self._disconnect_client(client_sock)
        
        logger.info("Network server stopped")
    
    def _accept_loop(self):
        """Accept incoming connections"""
        while self.running:
            try:
                client_sock, addr = self.server_socket.accept()
                logger.info(f"New connection from {addr}")
                
                with self.lock:
                    self.clients[client_sock] = {
                        'address': addr,
                        'worker_id': None,
                        'worker_name': None
                    }
                
                # Start client handler thread
                handler_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_sock,),
                    daemon=True
                )
                handler_thread.start()
                
            except Exception as e:
                if self.running:
                    logger.error(f"Error accepting connection: {e}")
    
    def _handle_client(self, client_sock: socket.socket):
        """Handle client connection"""
        buffer = b''
        
        try:
            while self.running:
                try:
                    data = client_sock.recv(4096)
                    if not data:
                        break
                    
                    buffer += data
                    
                    # Process complete messages (newline-separated)
                    while b'\n' in buffer:
                        line, buffer = buffer.split(b'\n', 1)
                        if line:
                            message = Protocol.decode_message(line)
                            if message:
                                self._process_message(client_sock, message)
                
                except socket.timeout:
                    continue
                except Exception as e:
                    logger.error(f"Error receiving data from client: {e}")
                    break
        
        except Exception as e:
            logger.error(f"Client handler error: {e}")
        finally:
            self._disconnect_client(client_sock)
    
    def _process_message(self, client_sock: socket.socket, message: Dict):
        """Process received message"""
        msg_type = message.get('type')
        
        if msg_type == MessageType.REGISTER.value:
            payload = message.get('payload', {})
            worker_id = payload.get('worker_id')
            worker_name = payload.get('worker_name', 'Unknown')
            
            with self.lock:
                if client_sock in self.clients:
                    self.clients[client_sock]['worker_id'] = worker_id
                    self.clients[client_sock]['worker_name'] = worker_name
            
            # Send ACK
            self.send_message(client_sock, Protocol.create_ack_message())
            
            # Notify callback
            if self.on_client_connected:
                try:
                    self.on_client_connected(client_sock, worker_id, worker_name)
                except Exception as e:
                    logger.error(f"Error in on_client_connected callback: {e}")
        
        elif msg_type == MessageType.HEARTBEAT.value:
            # Send ACK for heartbeat
            self.send_message(client_sock, Protocol.create_ack_message())
        
        elif msg_type == MessageType.RESULT.value:
            # Forward result to callback
            if self.on_message_received:
                try:
                    self.on_message_received(client_sock, message)
                except Exception as e:
                    logger.error(f"Error in on_message_received callback: {e}")
        
        elif msg_type == MessageType.ERROR.value:
            # Forward error to callback
            if self.on_message_received:
                try:
                    self.on_message_received(client_sock, message)
                except Exception as e:
                    logger.error(f"Error in on_message_received callback: {e}")
    
    def send_message(self, client_sock: socket.socket, message: bytes) -> bool:
        """Send message to client"""
        try:
            with self.lock:
                if client_sock not in self.clients:
                    return False
            
            client_sock.sendall(message)
            return True
        
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            self._disconnect_client(client_sock)
            return False
    
    def _disconnect_client(self, client_sock: socket.socket):
        """Disconnect and remove client"""
        with self.lock:
            if client_sock in self.clients:
                worker_id = self.clients[client_sock].get('worker_id')
                del self.clients[client_sock]
        
        try:
            client_sock.close()
        except Exception:
            pass
        
        if self.on_client_disconnected:
            try:
                self.on_client_disconnected(client_sock)
            except Exception as e:
                logger.error(f"Error in on_client_disconnected callback: {e}")
        
        logger.info(f"Client disconnected: {worker_id}")
    
    def get_client_info(self, client_sock: socket.socket) -> Optional[Dict]:
        """Get client information"""
        with self.lock:
            return self.clients.get(client_sock)
    
    def get_all_clients(self) -> Dict[socket.socket, Dict]:
        """Get all connected clients"""
        with self.lock:
            return self.clients.copy()
