"""
Logger Utility - Configures application-wide logging
Logs to both file and console with rotation
"""

import os
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from config.settings import config

def setup_logging():
    """
    Setup application logging with file rotation
    
    Creates separate log files for:
    - transactions.log: All meal transactions
    - errors.log: Errors and warnings
    - system.log: General application logs
    """
    
    # Create logs directory if it doesn't exist
    os.makedirs(config.LOG_FILE_PATH, exist_ok=True)
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Remove default handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler (for development) - only show WARNING and above
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)  # Only show warnings and errors in terminal
    console_formatter = logging.Formatter(
        '%(levelname)s - %(message)s'  # Simpler format for console
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # System log handler (rotating by size)
    system_log_path = os.path.join(config.LOG_FILE_PATH, 'system.log')
    system_handler = RotatingFileHandler(
        system_log_path,
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5
    )
    system_handler.setLevel(logging.DEBUG)
    system_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    system_handler.setFormatter(system_formatter)
    root_logger.addHandler(system_handler)
    
    # Transaction log handler (rotating daily)
    transaction_log_path = os.path.join(config.LOG_FILE_PATH, 'transactions.log')
    transaction_handler = TimedRotatingFileHandler(
        transaction_log_path,
        when='midnight',
        interval=1,
        backupCount=config.LOG_RETENTION_DAYS
    )
    transaction_handler.setLevel(logging.INFO)
    transaction_formatter = logging.Formatter(
        '%(asctime)s - %(message)s'
    )
    transaction_handler.setFormatter(transaction_formatter)
    
    # Create transaction logger
    transaction_logger = logging.getLogger('transactions')
    transaction_logger.addHandler(transaction_handler)
    transaction_logger.setLevel(logging.INFO)
    
    # Error log handler (rotating daily)
    error_log_path = os.path.join(config.LOG_FILE_PATH, 'errors.log')
    error_handler = TimedRotatingFileHandler(
        error_log_path,
        when='midnight',
        interval=1,
        backupCount=config.LOG_RETENTION_DAYS
    )
    error_handler.setLevel(logging.WARNING)
    error_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(pathname)s:%(lineno)d'
    )
    error_handler.setFormatter(error_formatter)
    root_logger.addHandler(error_handler)
    
    logging.info("Logging system initialized")


def get_logger(name):
    """
    Get a logger instance
    
    Args:
        name: Logger name (typically __name__ of the module)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def log_transaction(student_id, student_name, meal_type, status, reason=None):
    """
    Log a transaction to the transaction log
    
    Args:
        student_id: Student ID
        student_name: Student name
        meal_type: Breakfast, Lunch, Snack
        status: Approved, Denied, Error
        reason: Denial reason (optional)
    """
    transaction_logger = logging.getLogger('transactions')
    
    msg = f"Station: {config.STATION_ID} | Student: {student_id} - {student_name} | Meal: {meal_type} | Status: {status}"
    if reason:
        msg += f" | Reason: {reason}"
    
    transaction_logger.info(msg)


if __name__ == "__main__":
    # Test logging
    setup_logging()
    
    logger = get_logger(__name__)
    
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    # Test transaction logging
    log_transaction("12345", "John Smith", "Lunch", "Approved")
    log_transaction("67890", "Jane Doe", "Lunch", "Denied", "Daily limit reached")
    
    print("\nCheck the logs/ directory for output files")