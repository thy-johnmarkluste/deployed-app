"""
Logging configuration for the application.
Provides centralized logging setup for controllers and models.
"""
import logging
import os
from logging.handlers import RotatingFileHandler

from models.paths import get_logs_dir, get_log_file


MAX_BYTES = 5 * 1024 * 1024


BACKUP_COUNT = 3


def setup_logging(name: str = None, level: int = logging.INFO) -> logging.Logger:
    """
    Set up and return a logger with the specified name.

    Args:
        name: Logger name (usually module name). If None, returns root logger.
        level: Logging level (default: INFO)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)


    if logger.handlers:
        return logger

    logger.setLevel(level)


    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )


    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)


    file_handler = RotatingFileHandler(
        get_log_file(),
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)


    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.
    Uses lazy initialization to avoid creating loggers before setup.

    Args:
        name: Logger name (usually __name__ of the module)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def module_logger(module_name: str) -> logging.Logger:
    """
    Get or create a logger for a specific module.

    Args:
        module_name: Name of the module (usually __name__)

    Returns:
        Logger instance
    """
    logger = logging.getLogger(module_name)


    if not logger.handlers:

        if not logging.getLogger().handlers:
            setup_logging()
        else:

            logger.setLevel(logging.DEBUG)

    return logger
