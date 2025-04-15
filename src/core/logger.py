import logging
import sys
from typing import Any, Dict, Optional

from src.core.config import settings

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_LEVEL = getattr(logging, settings.LOG_LEVEL.upper())


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger with the specified name

    Args:
        name: Logger name (usually __name__)

    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)

    # Avoid adding handlers if they already exist
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(handler)

    return logger