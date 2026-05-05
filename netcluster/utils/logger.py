"""
Logging utility for NetCluster
"""
import logging
import sys
from netcluster.utils.config import LOG_LEVEL, LOG_FORMAT


def setup_logger(name: str, level: str = None) -> logging.Logger:
    """
    Setup and return a logger instance
    
    Args:
        name: Logger name
        level: Log level (defaults to config LOG_LEVEL)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, level or LOG_LEVEL, logging.INFO))
        logger.propagate = False
    
    return logger
