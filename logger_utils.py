"""
Logging utilities for DC Motor Control System
Provides centralized logging with proper formatting and rotation
"""

import logging
from typing import Optional
from config import get_config


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    Get a configured logger instance

    Args:
        name: Logger name (typically __name__ of the module)
        level: Optional logging level override

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    if level:
        logger.setLevel(getattr(logging, level.upper()))

    return logger


def log_exception(logger: logging.Logger, message: str, exc: Exception) -> None:
    """
    Log an exception with proper formatting

    Args:
        logger: Logger instance
        message: Context message
        exc: Exception to log
    """
    logger.error(f"{message}: {type(exc).__name__}: {str(exc)}", exc_info=True)


class LoggerMixin:
    """Mixin class to add logging capability to any class"""

    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class"""
        if not hasattr(self, '_logger'):
            self._logger = get_logger(self.__class__.__name__)
        return self._logger
