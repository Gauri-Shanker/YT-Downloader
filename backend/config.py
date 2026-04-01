"""Configuration and constants for YouTube Audio Downloader"""

import os
from dotenv import load_dotenv

load_dotenv()

# Paths - use absolute paths to avoid working directory issues
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BACKEND_DIR)  # Go up one level to yt-desktop folder
PROJECT_DIR = os.path.normpath(PROJECT_DIR)

# Import settings module for configurable paths
try:
    from settings import get_download_folder, get_cookies_path

    DOWNLOAD_FOLDER = get_download_folder()
    _cookies_path = get_cookies_path()
    COOKIES_FILE = (
        _cookies_path if _cookies_path else os.path.join(PROJECT_DIR, "cookies.txt")
    )
except ImportError:
    # Fallback if settings module not available
    DOWNLOAD_FOLDER = os.path.join(PROJECT_DIR, "downloads")
    COOKIES_FILE = os.path.join(PROJECT_DIR, "cookies.txt")

FAILED_LOG_FILE = os.path.join(PROJECT_DIR, "failed_downloads.txt")

# Timeouts & Retries
DOWNLOAD_TIMEOUT = int(os.getenv("DOWNLOAD_TIMEOUT", "300"))  # 5 minutes
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RATE_LIMIT_DELAY = float(os.getenv("RATE_LIMIT_DELAY", "2.0"))

# Threading - LIMITED TO 2 FOR STABILITY
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "2"))
# Force max 2 workers to prevent concurrency issues
if MAX_WORKERS > 2:
    MAX_WORKERS = 2

# Formats & Codecs
AUDIO_FORMAT = os.getenv("AUDIO_FORMAT", "mp3")

# Logging
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "app.log")

# Create necessary directories
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# Server Configuration
PORT = int(os.getenv("PORT", 5000))
DEBUG = os.getenv("DEBUG", "True") == "True"

# User Agents for rotation (avoid detection)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15",
]
