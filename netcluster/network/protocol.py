"""
Network Protocol - JSON message format for master-worker communication
"""
import json
import uuid
from typing import Dict, Any, Optional
from enum import Enum


class MessageType(Enum):
    """Message types for protocol"""
    REGISTER = "REGISTER"
    HEARTBEAT = "HEARTBEAT"
    TASK = "TASK"
    RESULT = "RESULT"
    ERROR = "ERROR"
    ACK = "ACK"
    DISCONNECT = "DISCONNECT"


class Protocol:
    """Protocol handler for encoding/decoding messages"""
    
    @staticmethod
    def encode_message(msg_type: MessageType, payload: Dict[str, Any], task_id: Optional[str] = None) -> bytes:
        """
        Encode a message to JSON bytes
        
        Args:
            msg_type: Message type enum
            payload: Message payload dictionary
            task_id: Optional task ID for task-related messages
            
        Returns:
            JSON-encoded bytes with newline terminator
        """
        message = {
            "type": msg_type.value,
            "payload": payload
        }
        
        if task_id:
            message["task_id"] = task_id
            
        json_str = json.dumps(message)
        return (json_str + "\n").encode('utf-8')
    
    @staticmethod
    def decode_message(data: bytes) -> Optional[Dict[str, Any]]:
        """
        Decode JSON bytes to message dictionary
        
        Args:
            data: JSON-encoded bytes
            
        Returns:
            Decoded message dictionary or None if invalid
        """
        try:
            json_str = data.decode('utf-8').strip()
            if not json_str:
                return None
            return json.loads(json_str)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None
    
    @staticmethod
    def create_register_message(worker_id: str, worker_name: str) -> bytes:
        """Create REGISTER message"""
        return Protocol.encode_message(
            MessageType.REGISTER,
            {"worker_id": worker_id, "worker_name": worker_name}
        )
    
    @staticmethod
    def create_heartbeat_message(worker_id: str, status: str = "idle") -> bytes:
        """Create HEARTBEAT message"""
        return Protocol.encode_message(
            MessageType.HEARTBEAT,
            {"worker_id": worker_id, "status": status}
        )
    
    @staticmethod
    def create_task_message(task_id: str, task_type: str, payload: Dict[str, Any]) -> bytes:
        """Create TASK message"""
        return Protocol.encode_message(
            MessageType.TASK,
            {"task_type": task_type, "payload": payload},
            task_id=task_id
        )
    
    @staticmethod
    def create_result_message(task_id: str, success: bool, result: Any, error: Optional[str] = None) -> bytes:
        """Create RESULT message"""
        payload = {
            "success": success,
            "result": result
        }
        if error:
            payload["error"] = error
        return Protocol.encode_message(
            MessageType.RESULT,
            payload,
            task_id=task_id
        )
    
    @staticmethod
    def create_ack_message(task_id: Optional[str] = None) -> bytes:
        """Create ACK message"""
        payload = {}
        if task_id:
            payload["task_id"] = task_id
        return Protocol.encode_message(MessageType.ACK, payload)
    
    @staticmethod
    def create_error_message(error_msg: str, task_id: Optional[str] = None) -> bytes:
        """Create ERROR message"""
        return Protocol.encode_message(
            MessageType.ERROR,
            {"error": error_msg},
            task_id=task_id
        )
    
    @staticmethod
    def generate_task_id() -> str:
        """Generate unique task ID"""
        return str(uuid.uuid4())
