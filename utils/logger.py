"""
Logging utilities
"""
import logging
from config.settings import settings

def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance."""
    logger = logging.getLogger(name)
    logger.setLevel(settings.LOG_LEVEL)
    return logger
