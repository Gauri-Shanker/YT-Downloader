"""Logging configuration for YouTube Audio Downloader"""

import logging
import sys
from config import LOG_FILE

# Configure UTF-8 for Windows console
sys.stdout.reconfigure(encoding="utf-8")

# Console logger (for terminal output)
console_logger = logging.getLogger("console")
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
)
console_logger.addHandler(console_handler)
console_logger.setLevel(logging.INFO)

# File logger (for persistent logs)
file_logger = logging.getLogger("file")
file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
)
file_logger.addHandler(file_handler)
file_logger.setLevel(logging.INFO)


def log_info(msg):
    """Log info message"""
    console_logger.info(msg)
    file_logger.info(msg)
    print(msg)


def log_warning(msg):
    """Log warning message"""
    console_logger.warning(msg)
    file_logger.warning(msg)
    print(f"⚠️ {msg}")


def log_error(msg):
    """Log error message"""
    console_logger.error(msg)
    file_logger.error(msg)
    print(f"❌ {msg}")


def log_success(msg):
    """Log success message"""
    console_logger.info(msg)
    file_logger.info(msg)
    print(f"✅ {msg}")
