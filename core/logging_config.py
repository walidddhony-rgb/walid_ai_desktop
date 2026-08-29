"""Centralized logging configuration for Walid AI Desktop."""
import logging
import sys
from pathlib import Path
from core.paths import DATA_DIR

# Create logs directory
LOGS_DIR = DATA_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Log file path
LOG_FILE = LOGS_DIR / "walid_ai.log"


def setup_logging(level=logging.INFO):
    """
    Configure logging for the application.
    
    Args:
        level: logging level (default: INFO)
    """
    logger = logging.getLogger("walid_ai")
    
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    
    # File handler
    try:
        file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Failed to setup file logging: {e}")
    
    logger.addHandler(console_handler)
    
    return logger


# Initialize logger
logger = setup_logging()


def get_logger(name: str = "walid_ai") -> logging.Logger:
    """Get or create a named logger."""
    return logging.getLogger(name)
