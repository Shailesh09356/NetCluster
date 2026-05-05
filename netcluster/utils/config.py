"""
Configuration settings for NetCluster
"""
import os

# Network Configuration
# Port layout:
#   50050 - LogBroadcastServer  (log streaming from master -> workers, legacy)
#   50051 - PIN auth server     (PIN handshake for worker auth)
#   50053 - NetworkServer       (structured JSON task distribution, master<->worker)
MASTER_PORT = int(os.getenv("NETCLUSTER_MASTER_PORT", "50053"))
PIN_SERVER_PORT = int(os.getenv("NETCLUSTER_PIN_PORT", "50051"))
WORKER_TIMEOUT = int(os.getenv("NETCLUSTER_WORKER_TIMEOUT", "30"))  # seconds
HEARTBEAT_INTERVAL = int(os.getenv("NETCLUSTER_HEARTBEAT_INTERVAL", "5"))  # seconds
TASK_TIMEOUT = int(os.getenv("NETCLUSTER_TASK_TIMEOUT", "300"))  # seconds

# Task Configuration
MAX_TASK_RETRIES = int(os.getenv("NETCLUSTER_MAX_TASK_RETRIES", "2"))
MAX_WORKERS = int(os.getenv("NETCLUSTER_MAX_WORKERS", "100"))

# Wordlist Generator Configuration
MAX_WORDLIST_COMBINATIONS = int(os.getenv("NETCLUSTER_MAX_WORDLIST_COMBINATIONS", "10000000"))  # 10M max
WORDLIST_CHUNK_SIZE = int(os.getenv("NETCLUSTER_WORDLIST_CHUNK_SIZE", "10000"))  # Write in chunks

# Logging Configuration
LOG_LEVEL = os.getenv("NETCLUSTER_LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
