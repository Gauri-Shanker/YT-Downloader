"""Downloader module for YouTube Audio/Video Downloader
Supports: audio-only, video-only, and both modes
"""

import yt_dlp
import os
import time
import threading
import random
import glob
from config import (
    MAX_RETRIES,
    RATE_LIMIT_DELAY,
    AUDIO_FORMAT,
)


def get_current_download_folder():
    """Get the current download folder from settings (dynamic)"""
    try:
        from settings import get_download_folder

        return get_download_folder()
    except ImportError:
        from config import DOWNLOAD_FOLDER

        return DOWNLOAD_FOLDER


from ydl_options import get_ydl_opts_with_retry, MODE_AUDIO, MODE_VIDEO, MODE_BOTH
from logger import log_info, log_warning, log_error, log_success
from utils import log_failed_download, classify_error

# Global semaphore to limit concurrent downloads
download_semaphore = threading.Semaphore(2)


def clean_url(url):
    """Remove playlist parameters from YouTube URL"""
    if "&list=" in url:
        return url.split("&list=")[0]
    return url


def find_downloaded_file(video_id, download_folder, mode=MODE_AUDIO):
    """
    Find the downloaded file by video ID.
    Handles the fact that postprocessor changes extension.
    """
    # Extensions based on mode
    if mode == MODE_VIDEO:
        extensions = [".mp4", ".mkv", ".webm", ".avi", ".mov"]
    else:
        extensions = [".mp3", ".m4a", ".opus", ".webm", ".aac", ".wav", ".ogg"]

    # Escape brackets for glob pattern - [] are special glob characters
    escaped_id = video_id.replace("[", "[[]").replace("]", "[]]")

    for ext in extensions:
        # Look for files containing the video ID with brackets (our filename format)
        # Pattern: *[video_id]*.ext - need to escape the brackets
        pattern = os.path.join(download_folder, f"*[[]{ video_id }[]]*{ext}")
        matches = glob.glob(pattern)
        if matches:
            return matches[0]

    # Also check without brackets (fallback for other filename formats)
    for ext in extensions:
        pattern = os.path.join(download_folder, f"*{video_id}*{ext}")
        matches = glob.glob(pattern)
        if matches:
            return matches[0]

    return None


def download_with_rate_limit(
    url, retry_count=0, progress_callback=None, mode=MODE_AUDIO
):
    """
    Download from YouTube URL with retry logic.

    Modes:
    - MODE_AUDIO: Extract audio only (mp3)
    - MODE_VIDEO: Download video with audio merged (mp4)
    - MODE_BOTH: Download both audio and video separately

    Returns dict with:
    - url: original URL
    - status: 'success' or 'failed'
    - file/files: filename(s) (on success)
    - path/paths: full path(s) (on success)
    - error: error message (on failure)
    - type: error type (on failure)
    - retryable: whether error is retryable
    """

    # Handle MODE_BOTH by downloading twice
    if mode == MODE_BOTH:
        audio_result = download_with_rate_limit(
            url, retry_count, progress_callback, MODE_AUDIO
        )
        video_result = download_with_rate_limit(
            url, retry_count, progress_callback, MODE_VIDEO
        )

        if (
            audio_result.get("status") == "success"
            and video_result.get("status") == "success"
        ):
            return {
                "url": url,
                "status": "success",
                "mode": "both",
                "files": [audio_result.get("file"), video_result.get("file")],
                "paths": [audio_result.get("path"), video_result.get("path")],
                "audio": audio_result,
                "video": video_result,
            }
        elif audio_result.get("status") == "success":
            return {
                "url": url,
                "status": "partial",
                "mode": "both",
                "message": "Audio downloaded, video failed",
                "audio": audio_result,
                "video": video_result,
            }
        elif video_result.get("status") == "success":
            return {
                "url": url,
                "status": "partial",
                "mode": "both",
                "message": "Video downloaded, audio failed",
                "audio": audio_result,
                "video": video_result,
            }
        else:
            return {
                "url": url,
                "status": "failed",
                "mode": "both",
                "error": "Both downloads failed",
                "audio": audio_result,
                "video": video_result,
            }

    mode_label = "🎵 Audio" if mode == MODE_AUDIO else "🎬 Video"

    with download_semaphore:
        try:
            # Clean URL
            clean_url_str = clean_url(url)
            if clean_url_str != url:
                log_info(f"🧹 Cleaned URL: {url} → {clean_url_str}")
                url = clean_url_str

            log_info(f"\n{'='*80}")
            log_info(f"⏬ Downloading ({mode_label}): {url}")
            log_info(f"📊 Attempt #{retry_count + 1}/{MAX_RETRIES + 1}")
            log_info(f"{'='*80}")

            # Rate limit with exponential backoff
            if retry_count > 0:
                backoff_time = (2**retry_count) + random.uniform(0, 2)
                log_info(f"⏳ Backoff: {backoff_time:.2f}s")
                time.sleep(backoff_time)
            else:
                delay = random.uniform(0.5, RATE_LIMIT_DELAY)
                log_info(f"⏱️ Delay: {delay:.2f}s")
                time.sleep(delay)

            # Ensure download folder exists (get from settings)
            download_folder = get_current_download_folder()
            os.makedirs(download_folder, exist_ok=True)

            # Get download options with mode
            opts = get_ydl_opts_with_retry(retry_count, mode)
            log_info(
                f"📥 Starting download ({mode}) with format: {opts.get('format', 'default')}"
            )

            if progress_callback:
                opts["progress_hooks"] = [progress_callback]

            with yt_dlp.YoutubeDL(opts) as ydl:
                # First, extract info WITHOUT downloading to see available formats
                log_info("📋 Fetching available formats...")
                info = ydl.extract_info(url, download=False)

                if not info:
                    raise Exception("No video info returned from yt-dlp")

                # Log ALL available formats for debugging (no filtering)
                formats = info.get("formats", [])
                log_info(f"📊 Found {len(formats)} total formats:")
                log_info("=" * 80)
                for fmt in formats:
                    fmt_id = fmt.get("format_id", "?")
                    ext = fmt.get("ext", "?")
                    acodec = fmt.get("acodec", "none")
                    vcodec = fmt.get("vcodec", "none")
                    abr = fmt.get("abr", 0) or 0
                    vbr = fmt.get("vbr", 0) or 0
                    width = fmt.get("width", 0) or 0
                    height = fmt.get("height", 0) or 0
                    fps = fmt.get("fps", 0) or 0
                    filesize = fmt.get("filesize") or fmt.get("filesize_approx") or 0
                    size_mb = filesize / (1024 * 1024) if filesize else 0
                    format_note = fmt.get("format_note", "")

                    # Determine type
                    has_video = vcodec != "none"
                    has_audio = acodec != "none"
                    if has_video and has_audio:
                        type_icon = "🎬+🎵"
                    elif has_audio:
                        type_icon = "🎵 AUDIO"
                    elif has_video:
                        type_icon = "🎬 VIDEO"
                    else:
                        type_icon = "❓"

                    log_info(
                        f"  [{fmt_id:>5}] {ext:>5} | {type_icon:>10} | v:{vcodec:>12} a:{acodec:>12} | {width}x{height}@{fps}fps | abr:{abr}kbps vbr:{vbr}kbps | {size_mb:.2f}MB | {format_note}"
                    )
                log_info("=" * 80)

                # Now download
                log_info("⬇️ Downloading selected format...")
                info = ydl.extract_info(url, download=True)

                video_id = info.get("id", "unknown")
                title = info.get("title", "Unknown")

                log_info(f"🎵 Title: {title}")
                log_info(f"🆔 Video ID: {video_id}")

                # Find the downloaded file (extension may have changed due to postprocessor)
                downloaded_file = find_downloaded_file(video_id, download_folder, mode)

                if not downloaded_file:
                    # Try using yt-dlp's prepare_filename with appropriate extension
                    base_filename = ydl.prepare_filename(info)
                    base_without_ext = os.path.splitext(base_filename)[0]

                    # Extensions based on mode
                    if mode == MODE_VIDEO:
                        extensions_to_try = [".mp4", ".mkv", ".webm"]
                    else:
                        extensions_to_try = [
                            f".{AUDIO_FORMAT}",
                            ".mp3",
                            ".m4a",
                            ".opus",
                            ".webm",
                        ]

                    for ext in extensions_to_try:
                        candidate = base_without_ext + ext
                        if os.path.exists(candidate):
                            downloaded_file = candidate
                            break

                if not downloaded_file or not os.path.exists(downloaded_file):
                    # Last resort: find most recent file in download folder
                    log_warning(
                        "Could not find expected file, searching for recent downloads..."
                    )
                    files = []
                    for f in os.listdir(download_folder):
                        full_path = os.path.join(download_folder, f)
                        if os.path.isfile(full_path):
                            files.append((full_path, os.path.getmtime(full_path)))

                    if files:
                        files.sort(key=lambda x: x[1], reverse=True)
                        # Check if most recent file was created in last 60 seconds
                        if time.time() - files[0][1] < 60:
                            downloaded_file = files[0][0]

                if downloaded_file and os.path.exists(downloaded_file):
                    file_size = os.path.getsize(downloaded_file) / (1024 * 1024)
                    log_success(f"✅ Downloaded ({mode}): {title}")
                    log_info(f"📁 File: {os.path.basename(downloaded_file)}")
                    log_info(f"📦 Size: {file_size:.2f} MB")
                    log_info(f"{'='*80}\n")

                    return {
                        "url": url,
                        "status": "success",
                        "mode": mode,
                        "file": os.path.basename(downloaded_file),
                        "path": os.path.abspath(downloaded_file),
                        "title": title,
                        "size_mb": round(file_size, 2),
                    }
                else:
                    raise Exception(
                        f"Downloaded file not found for video ID: {video_id}"
                    )

        except Exception as e:
            error_msg = str(e)
            error_type, is_retryable, description = classify_error(error_msg)

            log_error(f"❌ Failed: {url}")
            log_error(f"Error type: {error_type}")
            log_error(f"Error: {error_msg[:200]}")
            log_error(f"Retryable: {is_retryable}")
            log_info(f"{'='*80}\n")

            return {
                "url": url,
                "status": "failed",
                "mode": mode,
                "error": description or error_msg[:200],
                "type": error_type,
                "retryable": is_retryable,
                "retry_count": retry_count,
            }


# Backward-compatible alias
def download_audio_with_rate_limit(url, retry_count=0, progress_callback=None):
    """Backward-compatible function - downloads audio only"""
    return download_with_rate_limit(url, retry_count, progress_callback, MODE_AUDIO)
