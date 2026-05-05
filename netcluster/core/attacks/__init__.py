"""
Educational Brute Force Attack Module
Demonstrates distributed attack patterns and password security concepts

⚠️ FOR EDUCATIONAL PURPOSES ONLY
"""

from enum import Enum

class AttackType(Enum):
    """Types of brute force attacks for educational demonstration"""
    SSH = "ssh"
    FTP = "ftp"
    HTTP_BASIC = "http_basic"
    HTTP_FORM = "http_form"
    MYSQL = "mysql"
    HASH = "hash"
    ZIP = "zip"

class AttackStatus(Enum):
    PENDING = "pending"
    DISTRIBUTING = "distributing"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"

class AttackResult(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    ERROR = "error"
