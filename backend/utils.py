"""Utility functions for YouTube Audio Downloader"""

import re
import os
from config import FAILED_LOG_FILE, DOWNLOAD_FOLDER


def sanitize_filename(filename):
    """Remove or replace invalid characters for Windows filenames"""
    # Remove invalid Windows characters: < > : " / \ | ? *
    filename = re.sub(r'[<>:"/\\|?*]', "_", filename)
    # Remove control characters
    filename = "".join(char for char in filename if ord(char) >= 32)
    # Remove trailing dots and spaces (Windows limitation)
    filename = re.sub(r"[\s.]+$", "", filename)
    # Limit length
    if len(filename) > 200:
        filename = filename[:200]
    return filename


def log_failed_download(url, error):
    """Log failed download to file for later reference"""
    with open(FAILED_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{url} | ERROR: {error}\n")


def find_downloaded_file(video_id):
    """
    Search for a downloaded file by video ID.
    Returns the full path if found, None otherwise.
    """
    try:
        for filename in os.listdir(DOWNLOAD_FOLDER):
            if video_id in filename and filename.endswith(
                (".webm", ".m4a", ".mp3", ".opus", ".aac", ".wav")
            ):
                return os.path.join(DOWNLOAD_FOLDER, filename)
    except OSError:
        pass
    return None


def get_file_size_mb(file_path):
    """Get file size in MB"""
    try:
        return os.path.getsize(file_path) / (1024 * 1024)
    except OSError:
        return 0


def classify_error(error_str):
    """
    Classify error message to determine error type and how to handle it.
    Returns: (error_type, is_retryable, description)
    """
    error_lower = error_str.lower()

    # Private/Restricted videos
    if "private" in error_lower or "sign in" in error_lower:
        return (
            "private",
            False,
            "🔒 Private or restricted audio - login required",
        )

    # Removed videos
    if "removed" in error_lower or "terms of service" in error_lower:
        return ("removed", False, "❌ Video removed by YouTube (Terms of Service)")

    # Unavailable videos
    if "video unavailable" in error_lower or "terminated" in error_lower:
        return ("unavailable", False, "⚠️ Video unavailable (channel terminated)")

    # Age restricted
    if "age" in error_lower and "restrict" in error_lower:
        return ("age_restricted", False, "🔞 Age-restricted content - requires login")

    # No formats found (potentially retryable with different format options)
    if any(
        x in error_lower
        for x in [
            "no video formats found",
            "no formats available",
            "requested format not available",
            "format not available",
            "no suitable format",
            "unable to extract",
            "requested format is not available",
        ]
    ):
        return (
            "no_formats",
            True,
            "No audio formats available - retrying with different options...",
        )

    # Errno 22 - Invalid filename characters (retryable with sanitization in newer options)
    if "errno 22" in error_lower or "invalid argument" in error_lower:
        return (
            "errno_22",
            True,
            "[Errno 22] Filename issue - retrying with safer options...",
        )

    # FFmpeg errors
    if "ffmpeg" in error_lower or "ffprobe" in error_lower:
        return (
            "ffmpeg_error",
            False,
            "⚠️ FFmpeg error - please ensure FFmpeg is installed",
        )

    # Rate limiting
    if (
        "rate limit" in error_lower
        or "429" in error_lower
        or "too many requests" in error_lower
    ):
        return ("rate_limit", True, "🚫 Rate limited - backing off...")

    # Timeout / Connection errors
    if "timeout" in error_lower or "timed out" in error_lower:
        return ("timeout", True, "⏱️ Timeout during extraction - retrying...")

    if "connection" in error_lower or "network" in error_lower:
        return ("network", True, "🌐 Network error - retrying...")

    # HTTP errors
    if "http error 403" in error_lower:
        return (
            "forbidden",
            True,
            "🚫 Access forbidden - retrying with different client...",
        )

    if "http error 404" in error_lower:
        return ("not_found", False, "❌ Video not found")

    # Geo restriction
    if "geo" in error_lower or "country" in error_lower or "region" in error_lower:
        return ("geo_restricted", False, "🌍 Video not available in your region")

    # Unknown error - not retryable by default
    return ("unknown", False, f"Unknown error: {error_str[:100]}")
