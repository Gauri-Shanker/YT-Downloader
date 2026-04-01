"""User settings management for YT Downloader"""

import os
import json
import shutil

# Settings file location - in user's home folder for persistence
SETTINGS_DIR = os.path.join(os.path.expanduser("~"), ".yt-downloader")
SETTINGS_FILE = os.path.join(SETTINGS_DIR, "settings.json")

# Default settings
DEFAULT_SETTINGS = {
    "download_folder": os.path.join(
        os.path.expanduser("~"), "Downloads", "YT-Downloads"
    ),
    "ffmpeg_path": "",  # Empty = auto-detect
    "cookies_path": "",  # Empty = use default
}

# Ensure settings directory exists
os.makedirs(SETTINGS_DIR, exist_ok=True)


def load_settings():
    """Load settings from file, return defaults if file doesn't exist"""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved_settings = json.load(f)
                # Merge with defaults to ensure all keys exist
                settings = {**DEFAULT_SETTINGS, **saved_settings}
                return settings
    except Exception as e:
        print(f"Error loading settings: {e}")

    return DEFAULT_SETTINGS.copy()


def save_settings(settings):
    """Save settings to file"""
    try:
        # Validate settings before saving
        validated = validate_settings(settings)

        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(validated, f, indent=2)

        return {"status": "success", "settings": validated}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def validate_settings(settings):
    """Validate and normalize settings"""
    validated = DEFAULT_SETTINGS.copy()

    # Download folder
    if settings.get("download_folder"):
        download_folder = settings["download_folder"].strip()
        if download_folder:
            validated["download_folder"] = os.path.normpath(download_folder)

    # FFmpeg path
    if settings.get("ffmpeg_path"):
        ffmpeg_path = settings["ffmpeg_path"].strip()
        if ffmpeg_path:
            validated["ffmpeg_path"] = os.path.normpath(ffmpeg_path)

    # Cookies path
    if settings.get("cookies_path"):
        cookies_path = settings["cookies_path"].strip()
        if cookies_path:
            validated["cookies_path"] = os.path.normpath(cookies_path)

    return validated


def get_download_folder():
    """Get the configured download folder, create if doesn't exist"""
    settings = load_settings()
    folder = settings.get("download_folder", DEFAULT_SETTINGS["download_folder"])

    # Create folder if it doesn't exist
    try:
        os.makedirs(folder, exist_ok=True)
    except Exception as e:
        print(f"Error creating download folder: {e}")
        # Fallback to default
        folder = DEFAULT_SETTINGS["download_folder"]
        os.makedirs(folder, exist_ok=True)

    return folder


def get_ffmpeg_path():
    """Get FFmpeg path - returns configured path or auto-detects"""
    settings = load_settings()
    ffmpeg_path = settings.get("ffmpeg_path", "")

    # If custom path is set and valid, return it
    if ffmpeg_path:
        # Check if it's a directory (containing ffmpeg.exe) or the exe itself
        if os.path.isdir(ffmpeg_path):
            ffmpeg_exe = os.path.join(ffmpeg_path, "ffmpeg.exe")
            if os.path.exists(ffmpeg_exe):
                return ffmpeg_path
        elif os.path.isfile(ffmpeg_path) and ffmpeg_path.endswith("ffmpeg.exe"):
            return os.path.dirname(ffmpeg_path)

    # Auto-detect FFmpeg in common locations
    common_paths = [
        os.path.expanduser("~\\ffmpeg"),
        os.path.expanduser("~\\ffmpeg\\bin"),
        r"C:\ffmpeg",
        r"C:\ffmpeg\bin",
        r"C:\Program Files\ffmpeg\bin",
        r"C:\Program Files (x86)\ffmpeg\bin",
    ]

    for path in common_paths:
        if os.path.exists(os.path.join(path, "ffmpeg.exe")):
            return path

    # Check if ffmpeg is in PATH
    if shutil.which("ffmpeg"):
        return ""  # Empty means use system PATH

    return ""


def get_cookies_path():
    """Get cookies file path"""
    settings = load_settings()
    cookies_path = settings.get("cookies_path", "")

    if cookies_path and os.path.exists(cookies_path):
        return cookies_path

    # Default location
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(backend_dir)
    default_cookies = os.path.join(project_dir, "cookies.txt")

    return default_cookies if os.path.exists(default_cookies) else ""


def check_ffmpeg_status():
    """Check if FFmpeg is available and return status"""
    ffmpeg_path = get_ffmpeg_path()

    if ffmpeg_path:
        ffmpeg_exe = os.path.join(ffmpeg_path, "ffmpeg.exe")
        if os.path.exists(ffmpeg_exe):
            return {
                "available": True,
                "path": ffmpeg_path,
                "source": (
                    "custom" if load_settings().get("ffmpeg_path") else "auto-detected"
                ),
            }

    # Check system PATH
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return {
            "available": True,
            "path": os.path.dirname(system_ffmpeg),
            "source": "system",
        }

    return {
        "available": False,
        "path": None,
        "source": None,
        "error": "FFmpeg not found. Please install FFmpeg or set the path in settings.",
    }
