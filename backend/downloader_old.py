"""Audio downloader module for YouTube Audio Downloader
Simplified configuration based on proven Google Colab working pattern
"""

import yt_dlp
import os
import time
import threading
import random
from config import (
    DOWNLOAD_FOLDER,
    MAX_RETRIES,
    RATE_LIMIT_DELAY,
)
from ydl_options import get_ydl_opts_with_retry
from logger import log_info, log_warning, log_error, log_success
from utils import log_failed_download, classify_error

# Global semaphore to limit concurrent downloads
download_semaphore = threading.Semaphore(2)


def clean_url(url):
    """
    Clean YouTube URL by removing playlist parameters.
    Converts: https://youtube.com/watch?v=xxx&list=yyy&index=zzz
    To: https://youtube.com/watch?v=xxx
    """
    return url.split("&list=")[0]


def download_audio_with_rate_limit(url, retry_count=0, progress_callback=None):
    """
    Download audio from YouTube URL - simplified, proven pattern.
    Based on Google Colab working configuration.

    Returns dict with:
    - url: original URL
    - status: 'success' or 'failed'
    - file: filename (on success)
    - path: full path (on success)
    - error: error message (on failure)
    """

    with download_semaphore:
        try:
            # Clean URL to remove playlist parameters
            clean_url_str = clean_url(url)
            if clean_url_str != url:
                log_info(f"🧹 Cleaned URL: {url} → {clean_url_str}")
                url = clean_url_str

            log_info(f"\n{'='*80}")
            log_info(f"⏬ Downloading: {url}")
            log_info(f"📊 Attempt #{retry_count + 1}/{MAX_RETRIES + 1}")
            log_info(f"{'='*80}")

            # Rate limit delay
            if retry_count > 0:
                backoff_time = (2**retry_count) + random.uniform(0, 1)
                log_info(f"⏳ Backoff: {backoff_time:.2f}s")
                time.sleep(backoff_time)
            else:
                delay = random.uniform(1, RATE_LIMIT_DELAY)
                log_info(f"⏱️ Delay: {delay:.2f}s")
                time.sleep(delay)

            # Download with proven configuration
            log_info(f"📥 Starting download...")
            opts = get_ydl_opts_with_retry(retry_count)
            if progress_callback:
                opts["progress_hooks"] = [progress_callback]

            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)

                if not info:
                    raise Exception("No video info returned")

                video_id = info.get("id", "unknown")
                title = info.get("title", "Unknown")

                # Get actual filename from yt-dlp
                filename = ydl.prepare_filename(info)

                if not os.path.exists(filename):
                    raise Exception(f"File not found: {filename}")

                log_success(f"✅ Downloaded: {title}")
                log_info(f"📁 File: {os.path.basename(filename)}")
                log_info(f"{'='*80}\n")

                return {
                    "url": url,
                    "status": "success",
                    "file": os.path.basename(filename),
                    "path": os.path.abspath(filename),
                    "title": title,
                }

        except Exception as e:
            error_msg = str(e)
            error_type, _, description = classify_error(error_msg)

            log_error(f"❌ Failed: {url}")
            log_error(f"Error: {error_msg}")
            log_failed_download(url, error_msg[:200])
            log_info(f"{'='*80}\n")

            return {
                "url": url,
                "status": "failed",
                "error": description or error_msg[:100],
            }

            log_info(f"📥 Starting audio extraction...")
            opts = get_ydl_opts_with_retry(retry_count)
            if progress_callback:
                opts["progress_hooks"] = [progress_callback]

            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)

                if not info:
                    raise Exception("No video info returned")

                video_id = info.get("id", "unknown")

                # Get the ACTUAL filename that yt-dlp used, not reconstructed
                # This is the most reliable way to find the downloaded file
                filename = ydl.prepare_filename(info)

                log_success(f"Audio extraction completed for video ID: {video_id}")
                log_info(f"📁 Audio file: {os.path.basename(filename)}")

                # Verify file exists with the actual yt-dlp filename
                if not os.path.exists(filename):
                    log_warning(f"Expected file not found at: {filename}")
                    # Search for ANY recent files in download folder
                    if os.path.exists(DOWNLOAD_FOLDER):
                        # Find files modified within last 30 seconds
                        current_time = time.time()
                        for file in os.listdir(DOWNLOAD_FOLDER):
                            file_path = os.path.join(DOWNLOAD_FOLDER, file)
                            file_time = os.path.getmtime(file_path)
                            # If file was modified within last 30 seconds, likely our file
                            if (current_time - file_time) < 30 and any(
                                file.endswith(ext)
                                for ext in [
                                    ".webm",
                                    ".m4a",
                                    ".mp3",
                                    ".opus",
                                    ".aac",
                                    ".wav",
                                ]
                            ):
                                filename = file_path
                                log_success(f"Found recently modified file: {file}")
                                break

                    if not os.path.exists(filename):
                        raise Exception(
                            f"Downloaded file not found. "
                            f"Video ID: {video_id}, Expected path: {filename}, "
                            f"Download folder: {DOWNLOAD_FOLDER}"
                        )

                log_success(f"AUDIO EXTRACTION SUCCESSFUL: {url}")
                log_info(f"{'='*80}\n")

                return {
                    "url": url,
                    "status": "success",
                    "file": os.path.basename(filename),
                    "path": os.path.abspath(filename),
                    "message": f"Audio extracted successfully",
                }

        except Exception as e:
            error_type, is_retryable, description = classify_error(str(e))

            log_error(f"Audio extraction failed: {url}")
            log_error(f"Error: {str(e)}")

            # Let the caller (routes.py) handle the retry loop safely outside the semaphore lock!
            # Max retries exceeded or not retryable recorded here
            error_text = f"{description} - {str(e)[:100]}"
            log_error(f"Max retries reached or not retryable: {error_type}")
            log_failed_download(url, error_text)

            log_info(f"{'='*80}\n")

            return {
                "url": url,
                "status": "failed",
                "type": error_type,
                "error": error_text,
            }
