"""
Logging configuration for CSV Upload API
Handles all logging setup including file and console output
"""

import logging
import logging.handlers
import os
from pathlib import Path
from datetime import datetime

# Create logs directory if it doesn't exist
LOGS_DIR = Path(__file__).parent.parent.parent / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Log file paths
LOG_FILE = LOGS_DIR / "api.log"
UPLOAD_LOG_FILE = LOGS_DIR / "uploads.log"
ERROR_LOG_FILE = LOGS_DIR / "errors.log"


def setup_logging(log_level=logging.INFO):
    """
    Setup comprehensive logging configuration

    Args:
        log_level: logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        logger: configured root logger
    """

    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    simple_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler (INFO level for development)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)

    # Main API log file (rotating)
    api_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    api_handler.setLevel(logging.DEBUG)
    api_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(api_handler)

    # Upload-specific log file
    upload_handler = logging.handlers.RotatingFileHandler(
        UPLOAD_LOG_FILE,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3
    )
    upload_handler.setLevel(logging.INFO)
    upload_handler.setFormatter(detailed_formatter)

    # Error log file (separate for critical issues)
    error_handler = logging.handlers.RotatingFileHandler(
        ERROR_LOG_FILE,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_handler)

    # Setup upload logger
    upload_logger = logging.getLogger('upload')
    upload_logger.addHandler(upload_handler)

    root_logger.info(f"Logging initialized - API logs: {LOG_FILE}")
    root_logger.info(f"Upload logs: {UPLOAD_LOG_FILE}")
    root_logger.info(f"Error logs: {ERROR_LOG_FILE}")

    return root_logger


def get_logger(name):
    """
    Get or create a named logger

    Args:
        name: logger name (usually __name__)

    Returns:
        logger: configured logger instance
    """
    return logging.getLogger(name)


def get_upload_logger():
    """Get the upload-specific logger"""
    return logging.getLogger('upload')


def setup_error_logging(log_level=logging.ERROR):
    """
    Setup separate error logging for admin debugging with full stack traces

    Args:
        log_level: logging level (default ERROR to capture all errors)

    Returns:
        logger: configured error logger
    """
    error_logger = logging.getLogger('upload_errors')
    error_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    for handler in error_logger.handlers[:]:
        error_logger.removeHandler(handler)

    # Detailed formatter with exception info
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s\n'
        'Module: %(name)s | File: %(filename)s:%(lineno)d\n'
        'Function: %(funcName)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # File handler for error logs with full stack traces
    error_handler = logging.handlers.RotatingFileHandler(
        LOGS_DIR / 'errors_detailed.log',
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    error_handler.setLevel(log_level)
    error_handler.setFormatter(detailed_formatter)
    error_logger.addHandler(error_handler)

    # Also log to main error log
    main_error_handler = logging.handlers.RotatingFileHandler(
        ERROR_LOG_FILE,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3
    )
    main_error_handler.setLevel(log_level)
    main_error_handler.setFormatter(detailed_formatter)
    error_logger.addHandler(main_error_handler)

    return error_logger


def get_error_logger():
    """
    Get or create the error-specific logger for admin debugging

    Returns:
        logger: error logger with enhanced stack trace formatting
    """
    logger = logging.getLogger('upload_errors')
    if not logger.handlers:
        setup_error_logging()
    return logger
