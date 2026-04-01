"""yt-dlp options generation for audio/video downloads
Supports: audio-only, video-only, and audio+video modes
"""

import random
import os
import re
import shutil
from config import (
    DOWNLOAD_FOLDER,
    RATE_LIMIT_DELAY,
    COOKIES_FILE,
    USER_AGENTS,
    AUDIO_FORMAT,
)

# Download modes
MODE_AUDIO = "audio"  # Extract audio only (mp3)
MODE_VIDEO = "video"  # Video with audio (merged mp4)
MODE_BOTH = "both"  # Download both separately

# Add Node.js to PATH for yt-dlp JavaScript runtime
NODEJS_PATHS = [
    r"C:\Program Files\nodejs",
    r"C:\Program Files (x86)\nodejs",
    os.path.expanduser("~\\AppData\\Roaming\\npm"),
]
for node_path in NODEJS_PATHS:
    if os.path.exists(node_path) and node_path not in os.environ.get("PATH", ""):
        os.environ["PATH"] = node_path + os.pathsep + os.environ.get("PATH", "")


def setup_ffmpeg_path():
    """Setup FFmpeg path from settings or auto-detect"""
    # Try to get custom FFmpeg path from settings
    try:
        from settings import get_ffmpeg_path

        custom_ffmpeg = get_ffmpeg_path()
        if custom_ffmpeg and custom_ffmpeg not in os.environ.get("PATH", ""):
            os.environ["PATH"] = custom_ffmpeg + os.pathsep + os.environ.get("PATH", "")
            return True
    except ImportError:
        pass

    # Fallback: Add FFmpeg to PATH if it exists in common locations
    FFMPEG_PATHS = [
        os.path.expanduser("~\\ffmpeg"),
        os.path.expanduser("~\\ffmpeg\\bin"),
        r"C:\ffmpeg\bin",
        r"C:\Program Files\ffmpeg\bin",
    ]
    for ffmpeg_path in FFMPEG_PATHS:
        if os.path.exists(ffmpeg_path) and ffmpeg_path not in os.environ.get(
            "PATH", ""
        ):
            os.environ["PATH"] = ffmpeg_path + os.pathsep + os.environ.get("PATH", "")

    return shutil.which("ffmpeg") is not None


# Setup FFmpeg on module load
setup_ffmpeg_path()

# Check if FFmpeg is available
FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None


def sanitize_filename(title):
    """
    Sanitize filename for Windows compatibility.
    Removes/replaces all problematic characters.
    """
    if not title:
        return "audio"

    # Remove or replace invalid Windows filename characters: < > : " / \ | ? *
    title = re.sub(r'[<>:"/\\|?*]', "", title)
    # Remove Unicode characters that cause issues
    title = re.sub(r"[^\x00-\x7F]+", "_", title)
    # Replace multiple spaces/underscores with single underscore
    title = re.sub(r"[\s_]+", "_", title)
    # Remove leading/trailing underscores and dots
    title = title.strip("._")
    # Limit length to 150 chars to be safe
    if len(title) > 150:
        title = title[:150]
    # If empty after sanitization, use fallback
    if not title:
        title = "audio"
    return title


def get_ydl_opts_with_retry(retry_count=0, mode=MODE_AUDIO):
    """
    Generate yt-dlp options for different download modes.

    Modes:
    - MODE_AUDIO: Extract audio only (mp3)
    - MODE_VIDEO: Download video with audio merged (mp4)
    - MODE_BOTH: Used twice - once for audio, once for video

    Uses postprocessors when FFmpeg is available.
    """

    # Format selection based on mode
    if mode == MODE_VIDEO:
        # Video with audio - AUTO BEST QUALITY (same as Custom Auto Best)
        if retry_count == 0:
            # Get absolute highest quality: 1080p+ preferred, best audio
            format_str = (
                "bestvideo[ext=mp4][height>=1080]+bestaudio[ext=m4a]/"
                "bestvideo[ext=webm][height>=1080]+bestaudio[ext=webm]/"
                "bestvideo[ext=mp4]+bestaudio[ext=m4a]/"
                "bestvideo[ext=webm]+bestaudio[ext=webm]/"
                "bestvideo+bestaudio/best"
            )
        elif retry_count == 1:
            # Fallback: still try best quality
            format_str = "bestvideo+bestaudio/best"
        else:
            # Last resort: any combined format
            format_str = "best"
    else:
        # Audio only - comprehensive fallback chain (good to bad quality)
        # Tries audio-only streams first, then extracts from video if needed
        if retry_count == 0:
            # Best quality audio with full fallback chain:
            # 1. Best m4a (AAC) audio-only stream
            # 2. Best webm (opus) audio-only stream
            # 3. Any best audio-only stream
            # 4. Best overall (video+audio) - FFmpeg will extract audio
            format_str = "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio[ext=mp3]/bestaudio[ext=ogg]/bestaudio/best"
        elif retry_count == 1:
            # Fallback: any audio stream, or video to extract from
            format_str = "bestaudio/best[height<=480]"
        else:
            # Last resort: worst quality (smallest file)
            format_str = "worstaudio/worst"

    # Get download folder from settings (dynamic)
    try:
        from settings import get_download_folder

        download_folder = get_download_folder()
    except ImportError:
        download_folder = DOWNLOAD_FOLDER

    # Output template based on mode
    if mode == MODE_VIDEO:
        output_template = os.path.join(
            download_folder, "%(title).100B [%(id)s].%(ext)s"
        )
    else:
        output_template = os.path.join(
            download_folder, "%(title).100B [%(id)s].%(ext)s"
        )

    opts = {
        # FORMAT: Audio-preferred with fallbacks
        "format": format_str,
        # OUTPUT: Safe filename with video ID
        "outtmpl": output_template,
        # BASIC OPTIONS
        "noplaylist": True,
        "quiet": False,  # Show progress for debugging
        "no_warnings": False,
        "ignoreerrors": False,
        # FILENAME SAFETY: Critical for Windows - this is the key fix for Errno 22
        "restrictfilenames": True,
        "windowsfilenames": True,
        # BANDWIDTH SAVING OPTIONS (especially for audio)
        "writethumbnail": False,  # Don't download thumbnails
        "writeinfojson": False,  # Don't write metadata JSON
        "writedescription": False,  # Don't write description
        "writeannotations": False,  # Don't write annotations
        # NETWORK
        "socket_timeout": 120,
        "retries": 3,
        "fragment_retries": 3,
        "file_access_retries": 3,
        # HEADERS
        "http_headers": {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
        # YOUTUBE: Multiple player clients for reliability
        "extractor_args": {
            "youtube": {
                "player_client": ["android_music", "android", "web"],
            }
        },
        # COOKIES (optional)
        "cookiefile": COOKIES_FILE if os.path.exists(COOKIES_FILE) else None,
        # FFMPEG settings
        "prefer_ffmpeg": True,
        # JAVASCRIPT RUNTIME: Required for YouTube signature solving
        # Enable Node.js as the JavaScript runtime
        "js_runtimes": {"node": {}},
    }

    # Add postprocessors based on mode
    if FFMPEG_AVAILABLE:
        if mode == MODE_AUDIO:
            # AUDIO ONLY - optimized for minimal bandwidth
            # extract_audio ensures we only get audio stream
            opts["extract_audio"] = True

            preferred_codec = (
                AUDIO_FORMAT
                if AUDIO_FORMAT in ["mp3", "m4a", "opus", "wav", "aac"]
                else "mp3"
            )
            opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": preferred_codec,
                    "preferredquality": "192",
                }
            ]
            opts["keepvideo"] = False
        elif mode == MODE_VIDEO:
            # Merge video+audio into mp4/mkv
            opts["postprocessors"] = [
                {
                    "key": "FFmpegVideoRemuxer",
                    "preferedformat": "mp4",
                }
            ]
            opts["merge_output_format"] = "mp4"
        # For MODE_BOTH, postprocessors will be set by the caller

    return opts


def get_check_opts():
    """Check video availability - info only, no download"""
    return {
        "format": "bestaudio/best",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "skip_download": True,
        "http_headers": {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept-Language": "en-US,en;q=0.9",
        },
        "extractor_args": {
            "youtube": {
                "player_client": ["android_music", "android", "web"],
            }
        },
        "socket_timeout": 30,
        "cookiefile": COOKIES_FILE if os.path.exists(COOKIES_FILE) else None,
        "js_runtimes": {"node": {}},
    }
