"""Flask routes for YouTube Audio Downloader"""

import json
import os
import queue
import threading
import time
import random
import uuid
from flask import jsonify, request, Response
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import DOWNLOAD_FOLDER, MAX_WORKERS, DOWNLOAD_TIMEOUT, MAX_RETRIES
from downloader import download_audio_with_rate_limit, download_with_rate_limit
from ydl_options import get_ydl_opts_with_retry, MODE_AUDIO, MODE_VIDEO, MODE_BOTH
from logger import log_info, log_warning, log_error, log_success
from utils import classify_error
import yt_dlp


def register_routes(app):
    """Register all Flask routes"""

    @app.route("/download", methods=["POST"])
    def download():
        """Batch download endpoint with retry logic"""
        data = request.get_json()
        links = data.get("links", [])

        log_info(f"\n{'='*80}")
        log_info(f"🚀 NEW BATCH AUDIO EXTRACTION REQUEST")
        log_info(f"📊 Total tracks: {len(links)}")
        log_info(f"{'='*80}\n")

        if not links:
            log_warning("No links provided in request")
            return jsonify({"error": "No links provided"}), 400

        results = []

        def download_with_retries(url):
            """Download with retry logic"""
            for retry in range(MAX_RETRIES + 1):
                try:
                    result = download_audio_with_rate_limit(url, retry_count=retry)

                    if result.get("status") == "success":
                        return result

                    # Check if retryable
                    if retry < MAX_RETRIES and result.get("retryable", True):
                        log_warning(
                            f"Retrying {url} (attempt {retry + 2}/{MAX_RETRIES + 1})"
                        )
                        continue
                    else:
                        return result

                except Exception as e:
                    if retry == MAX_RETRIES:
                        return {
                            "url": url,
                            "status": "failed",
                            "error": str(e)[:100],
                        }

        log_info(f"🔄 Starting downloads with {MAX_WORKERS} workers...\n")
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(download_with_retries, url): url for url in links
            }

            completed = 0
            for future in as_completed(futures):
                completed += 1
                try:
                    result = future.result(timeout=DOWNLOAD_TIMEOUT)
                    results.append(result)
                    status = "✅" if result.get("status") == "success" else "❌"
                    log_info(f"{status} {completed}/{len(links)}")
                except TimeoutError:
                    url = futures[future]
                    log_error(f"TIMEOUT: {url}")
                    results.append({"url": url, "status": "failed", "error": "Timeout"})
                except Exception as e:
                    url = futures[future]
                    log_error(f"ERROR: {url} -> {e}")
                    results.append(
                        {"url": url, "status": "failed", "error": str(e)[:100]}
                    )

        success = len([r for r in results if r.get("status") == "success"])
        failed = len([r for r in results if r.get("status") == "failed"])
        log_info(f"\n📊 COMPLETE: {success} success, {failed} failed")
        log_info(f"{'='*80}\n")

        return (
            jsonify(
                {
                    "message": "Audio extraction completed",
                    "results": results,
                    "summary": {"success": success, "failed": failed},
                    "download_path": os.path.abspath(DOWNLOAD_FOLDER),
                }
            ),
            200,
        )

    # REMOVED: /download-stream endpoint - using /download-single with polling instead
    # The polling approach is more stable and doesn't have long-running connection issues

    # Global dictionary to store download jobs (URL -> status/result)
    download_jobs = {}
    download_jobs_lock = threading.Lock()

    @app.route("/download-single", methods=["POST"])
    def download_single():
        """Single download endpoint - starts download in background, returns immediately"""
        data = request.get_json()
        url = data.get("url")
        url = url.split("&list=")[0]
        proxy = data.get("proxy")

        log_info(f"\n{'='*80}")
        log_info(f"🎵 SINGLE AUDIO EXTRACTION REQUEST")
        log_info(f"📥 URL: {url}")
        log_info(f"{'='*80}\n")

        if not url:
            log_warning("No URL provided in request")
            return jsonify({"error": "No URL provided"}), 400

        # Create job ID for tracking (without raw URL to prevent route matching 404s)
        job_id = f"job_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"

        # Initialize job status
        with download_jobs_lock:
            download_jobs[job_id] = {
                "url": url,
                "status": "queued",
                "attempt": 0,
                "max_attempts": MAX_RETRIES + 1,
            }

        def download_worker():
            """Background worker to download audio - runs even if client disconnects"""
            retry = 0
            while retry <= MAX_RETRIES:
                try:
                    with download_jobs_lock:
                        download_jobs[job_id]["status"] = "processing"
                        download_jobs[job_id]["attempt"] = retry + 1

                    log_info(
                        f"🔄 Background worker: {url} (Attempt {retry + 1}/{MAX_RETRIES + 1})"
                    )

                    # Small delay to space out requests
                    import time as time_module

                    time_module.sleep(random.uniform(0.5, 1))

                    def progress_hook(d):
                        if d["status"] == "downloading":
                            try:
                                downloaded = d.get("downloaded_bytes", 0)
                                total = d.get("total_bytes") or d.get(
                                    "total_bytes_estimate", 0
                                )
                                with download_jobs_lock:
                                    download_jobs[job_id]["status"] = "downloading"
                                    download_jobs[job_id]["downloaded"] = downloaded
                                    download_jobs[job_id]["total"] = total
                            except Exception:
                                pass

                    # Download audio with timeout protection
                    result = download_audio_with_rate_limit(
                        url, retry, progress_callback=progress_hook
                    )

                    # Update job with result
                    with download_jobs_lock:
                        download_jobs[job_id].update(result)
                        if result.get("status") == "success":
                            log_success(f"Background download completed: {url}")
                            break  # Exit on success
                        else:
                            error_type = result.get("type")
                            # Retry on specific errors if retries remaining
                            if (
                                error_type in ["no_formats", "errno_22", "timeout"]
                                and retry < MAX_RETRIES
                            ):
                                log_warning(
                                    f"Retryable error detected: {error_type} → Retrying..."
                                )
                                download_jobs[job_id]["status"] = "retrying"
                                retry += 1
                                backoff = (2**retry) + random.uniform(0, 1)
                                time_module.sleep(backoff)
                                continue
                            else:
                                log_error(
                                    f"Background download failed (non-retryable): {url}"
                                )
                                break  # Exit on fatal error

                except Exception as e:
                    log_error(f"Background worker exception: {str(e)[:100]}")
                    error_type, is_retryable, error_msg = classify_error(str(e))

                    # Update job status with error
                    with download_jobs_lock:
                        download_jobs[job_id].update(
                            {
                                "status": "failed",
                                "type": error_type,
                                "error": error_msg[:200],
                            }
                        )
                    break  # Exit on exception

        # Start background thread (daemon thread continues even if client disconnects)
        worker_thread = threading.Thread(target=download_worker, daemon=True)
        worker_thread.start()

        # Return immediately with job ID
        return (
            jsonify({"job_id": job_id, "url": url, "status": "queued"}),
            202,
        )

    @app.route("/download-sync", methods=["POST"])
    def download_sync():
        """Synchronous download endpoint - waits for download to complete before returning

        Modes:
        - audio: Extract audio only (mp3) - default
        - video: Download video with audio merged (mp4)
        - both: Download both audio and video separately
        """
        data = request.get_json()
        url = data.get("url")
        proxy = data.get("proxy")
        mode = data.get("mode", "audio")  # Default to audio

        # Map mode string to constants
        mode_map = {"audio": MODE_AUDIO, "video": MODE_VIDEO, "both": MODE_BOTH}
        download_mode = mode_map.get(mode, MODE_AUDIO)

        mode_label = {"audio": "🎵 Audio", "video": "🎬 Video", "both": "🎵+🎬 Both"}

        log_info(f"\n{'='*80}")
        log_info(f"{mode_label.get(mode, '🎵 Audio')} SYNCHRONOUS DOWNLOAD REQUEST")
        log_info(f"📥 URL: {url}")
        log_info(f"📦 Mode: {mode}")
        log_info(f"{'='*80}\n")

        if not url:
            log_warning("No URL provided in request")
            return jsonify({"error": "No URL provided"}), 400

        retry = 0
        final_result = None

        while retry <= MAX_RETRIES:
            try:
                log_info(
                    f"🔄 Sync worker ({mode}): {url} (Attempt {retry + 1}/{MAX_RETRIES + 1})"
                )

                # Small delay to space out requests
                import time as time_module

                time_module.sleep(random.uniform(0.5, 1))

                # Download with specified mode
                result = download_with_rate_limit(url, retry, mode=download_mode)
                final_result = result

                if result.get("status") == "success":
                    log_success(f"Sync download completed: {url}")
                    break  # Exit on success
                else:
                    error_type = result.get("type")
                    is_retryable = result.get("retryable", False)
                    # Retry on specific errors if retries remaining
                    retryable_types = [
                        "no_formats",
                        "errno_22",
                        "timeout",
                        "network",
                        "rate_limit",
                        "forbidden",
                    ]
                    if (
                        error_type in retryable_types or is_retryable
                    ) and retry < MAX_RETRIES:
                        log_warning(
                            f"Retryable error detected: {error_type} → Retrying with fallback format..."
                        )
                        retry += 1
                        backoff = (2**retry) + random.uniform(0, 1)
                        time_module.sleep(backoff)
                        continue
                    else:
                        log_error(f"Sync download failed (non-retryable): {url}")
                        break  # Exit on fatal error

            except Exception as e:
                log_error(f"Sync worker exception: {str(e)[:100]}")
                error_type, is_retryable, error_msg = classify_error(str(e))
                final_result = {
                    "url": url,
                    "status": "failed",
                    "type": error_type,
                    "error": error_msg[:200],
                }
                break

        # Always return 200, the frontend will check the 'status' property
        return jsonify(final_result), 200

    @app.route("/download-status/<job_id>", methods=["GET"])
    def download_status(job_id):
        """Poll endpoint to check download status - returns immediately"""
        with download_jobs_lock:
            if job_id not in download_jobs:
                return jsonify({"error": "Job not found"}), 404
            job_data = download_jobs[job_id].copy()

        # Return current status immediately (no waiting)
        return jsonify(job_data), 200

    @app.route("/health", methods=["GET"])
    def health():
        """Health check endpoint"""
        import shutil
        from config import COOKIES_FILE

        ffmpeg_available = shutil.which("ffmpeg") is not None
        cookies_exist = os.path.exists(COOKIES_FILE)

        return jsonify(
            {
                "status": "running",
                "max_workers": MAX_WORKERS,
                "max_retries": MAX_RETRIES,
                "download_folder": os.path.abspath(DOWNLOAD_FOLDER),
                "ffmpeg_available": ffmpeg_available,
                "cookies_exist": cookies_exist,
                "cookies_path": (
                    os.path.abspath(COOKIES_FILE) if cookies_exist else None
                ),
            }
        )

    @app.route("/cookies-status", methods=["GET"])
    def cookies_status():
        """Check cookies file status"""
        from config import COOKIES_FILE

        exists = os.path.exists(COOKIES_FILE)
        valid = False
        if exists:
            valid = os.path.getsize(COOKIES_FILE) > 0

        return jsonify(
            {
                "exists": exists,
                "valid": valid,
                "size": os.path.getsize(COOKIES_FILE) if exists else 0,
                "path": os.path.abspath(COOKIES_FILE) if exists else None,
            }
        )

    @app.route("/formats", methods=["POST"])
    def get_formats():
        """Get available formats for a video URL - only mp4/webm"""
        data = request.get_json()
        url = data.get("url")

        if not url:
            return jsonify({"error": "No URL provided"}), 400

        # Clean URL
        if "&list=" in url:
            url = url.split("&list=")[0]

        log_info(f"📋 Fetching formats for: {url}")

        try:
            opts = {
                "quiet": True,
                "no_warnings": True,
                "noplaylist": True,
                "skip_download": True,
                "js_runtimes": {"node": {}},
            }

            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)

                if not info:
                    return jsonify({"error": "Could not fetch video info"}), 400

                formats = info.get("formats", [])
                title = info.get("title", "Unknown")
                duration = info.get("duration", 0) or 0
                thumbnail = info.get("thumbnail", "")

                # Process and filter formats (only mp4/webm)
                video_audio = []  # Combined video+audio
                video_only = []  # Video without audio (need merge)
                audio_only = []  # Audio only

                for fmt in formats:
                    ext = fmt.get("ext", "")
                    if ext not in ["mp4", "webm"]:
                        continue

                    fmt_id = fmt.get("format_id", "")
                    acodec = fmt.get("acodec", "none")
                    vcodec = fmt.get("vcodec", "none")
                    width = fmt.get("width", 0) or 0
                    height = fmt.get("height", 0) or 0
                    fps = fmt.get("fps", 0) or 0
                    abr = fmt.get("abr", 0) or 0
                    vbr = fmt.get("vbr", 0) or 0
                    tbr = fmt.get("tbr", 0) or 0  # Total bitrate
                    filesize = fmt.get("filesize") or fmt.get("filesize_approx") or 0

                    # Calculate size - use filesize if available, otherwise estimate from bitrate
                    if filesize:
                        size_mb = round(filesize / (1024 * 1024), 2)
                        size_estimated = False
                    elif duration > 0 and (tbr or vbr or abr):
                        # Estimate: bitrate (kbps) * duration (s) / 8 / 1024 = MB
                        bitrate = tbr or (vbr + abr)
                        estimated_bytes = bitrate * 1000 * duration / 8
                        size_mb = round(estimated_bytes / (1024 * 1024), 1)
                        size_estimated = True
                    else:
                        size_mb = 0
                        size_estimated = False

                    format_note = fmt.get("format_note", "")

                    has_video = vcodec != "none"
                    has_audio = acodec != "none"

                    format_info = {
                        "format_id": fmt_id,
                        "ext": ext,
                        "width": width,
                        "height": height,
                        "fps": fps,
                        "vcodec": vcodec if has_video else None,
                        "acodec": acodec if has_audio else None,
                        "abr": abr,
                        "vbr": vbr,
                        "tbr": tbr,
                        "size_mb": size_mb,
                        "size_estimated": size_estimated if size_mb else False,
                        "quality": format_note or f"{height}p" if height else "unknown",
                        "has_video": has_video,
                        "has_audio": has_audio,
                    }

                    if has_video and has_audio:
                        video_audio.append(format_info)
                    elif has_video:
                        video_only.append(format_info)
                    elif has_audio:
                        audio_only.append(format_info)

                # Sort by quality (height) descending
                video_audio.sort(key=lambda x: (x["height"], x["fps"]), reverse=True)
                video_only.sort(key=lambda x: (x["height"], x["fps"]), reverse=True)
                audio_only.sort(key=lambda x: x["abr"], reverse=True)

                # Find best audio for merging (highest bitrate)
                best_audio_id = audio_only[0]["format_id"] if audio_only else None

                # Find best video+audio combined
                best_combined_id = video_audio[0]["format_id"] if video_audio else None

                # Find best video-only (for merge with audio)
                best_video_id = video_only[0]["format_id"] if video_only else None

                return (
                    jsonify(
                        {
                            "url": url,
                            "title": title,
                            "duration": duration,
                            "thumbnail": thumbnail,
                            "video_audio": video_audio,  # Ready to download (has both)
                            "video_only": video_only,  # Need FFmpeg merge
                            "audio_only": audio_only,  # For merging
                            "best_audio_id": best_audio_id,
                            "best_combined_id": best_combined_id,
                            "best_video_id": best_video_id,
                        }
                    ),
                    200,
                )

        except Exception as e:
            log_error(f"Error fetching formats: {str(e)[:200]}")
            return jsonify({"error": str(e)[:200]}), 500

    @app.route("/download-format", methods=["POST"])
    def download_format():
        """Download specific format(s) - merges video+audio if needed

        Params:
        - url: YouTube URL
        - video_format_id: format ID for video
        - audio_format_id: format ID for audio (optional - auto-selects best if missing)
        - has_audio: whether the video format already has audio
        - auto_best: if True, downloads best quality automatically
        """
        data = request.get_json()
        url = data.get("url")
        video_format_id = data.get("video_format_id")
        audio_format_id = data.get("audio_format_id")
        has_audio = data.get("has_audio", False)  # Does the selected format have audio?
        auto_best = data.get("auto_best", False)  # Auto select best quality

        if not url:
            return jsonify({"error": "No URL provided"}), 400

        # Clean URL
        if "&list=" in url:
            url = url.split("&list=")[0]

        log_info(
            f"📥 Download format request: video={video_format_id}, audio={audio_format_id}, has_audio={has_audio}, auto_best={auto_best}"
        )

        try:
            # Build format string
            if auto_best:
                # Auto best: Get absolute highest quality video + best audio
                # Priority: mp4/webm video with highest resolution + m4a/opus audio
                format_str = (
                    "bestvideo[ext=mp4][height>=1080]+bestaudio[ext=m4a]/"
                    "bestvideo[ext=webm][height>=1080]+bestaudio[ext=webm]/"
                    "bestvideo[ext=mp4]+bestaudio[ext=m4a]/"
                    "bestvideo[ext=webm]+bestaudio[ext=webm]/"
                    "bestvideo+bestaudio/best"
                )
                log_info(f"🚀 Auto-best mode (highest quality): {format_str}")
            elif video_format_id and audio_format_id:
                # Explicit merge: user-selected video + user-selected audio
                format_str = f"{video_format_id}+{audio_format_id}"
                log_info(f"🔗 Merging user selection: {format_str}")
            elif video_format_id:
                # User selected a video format - merge with best available audio
                # This ensures high quality audio even if video format has lower quality audio
                format_str = (
                    f"{video_format_id}+bestaudio[ext=m4a]/"
                    f"{video_format_id}+bestaudio[ext=webm]/"
                    f"{video_format_id}+bestaudio/"
                    f"{video_format_id}"
                )
                log_info(f"🔗 Merging with best audio: {format_str}")
            else:
                return jsonify({"error": "No format selected"}), 400

            # Get download folder from settings (dynamic, not cached)
            from settings import get_download_folder

            download_folder = get_download_folder()

            opts = {
                "format": format_str,
                "outtmpl": os.path.join(
                    download_folder, "%(title).100B [%(id)s].%(ext)s"
                ),
                "noplaylist": True,
                "restrictfilenames": True,
                "windowsfilenames": True,
                "merge_output_format": "mp4",  # Merge to mp4
                "postprocessors": [
                    {
                        "key": "FFmpegVideoRemuxer",
                        "preferedformat": "mp4",
                    }
                ],
                "prefer_ffmpeg": True,
                "js_runtimes": {"node": {}},
            }

            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)

                if not info:
                    return jsonify({"error": "Download failed"}), 500

                video_id = info.get("id", "unknown")
                title = info.get("title", "Unknown")

                # Find downloaded file
                import glob

                pattern = os.path.join(download_folder, f"*[{video_id}]*.mp4")
                matches = glob.glob(pattern)
                if not matches:
                    pattern = os.path.join(download_folder, f"*{video_id}*.mp4")
                    matches = glob.glob(pattern)

                if matches:
                    downloaded_file = matches[0]
                    file_size = os.path.getsize(downloaded_file) / (1024 * 1024)

                    return (
                        jsonify(
                            {
                                "status": "success",
                                "url": url,
                                "title": title,
                                "file": os.path.basename(downloaded_file),
                                "path": os.path.abspath(downloaded_file),
                                "size_mb": round(file_size, 2),
                            }
                        ),
                        200,
                    )
                else:
                    return jsonify({"error": "Downloaded file not found"}), 500

        except Exception as e:
            log_error(f"Download format error: {str(e)[:200]}")
            return jsonify({"error": str(e)[:200], "status": "failed"}), 500

    # ==================== SETTINGS ENDPOINTS ====================

    @app.route("/settings", methods=["GET"])
    def get_settings():
        """Get current user settings"""
        from settings import load_settings, check_ffmpeg_status, get_download_folder

        settings = load_settings()
        ffmpeg_status = check_ffmpeg_status()

        return jsonify(
            {
                "settings": settings,
                "download_folder": get_download_folder(),
                "ffmpeg": ffmpeg_status,
            }
        )

    @app.route("/settings", methods=["POST"])
    def update_settings():
        """Update user settings"""
        from settings import (
            save_settings,
            load_settings,
            get_download_folder,
            check_ffmpeg_status,
        )

        data = request.get_json()

        # Get current settings and merge with new values
        current = load_settings()

        if "download_folder" in data:
            current["download_folder"] = data["download_folder"]
        if "ffmpeg_path" in data:
            current["ffmpeg_path"] = data["ffmpeg_path"]
        if "cookies_path" in data:
            current["cookies_path"] = data["cookies_path"]

        result = save_settings(current)

        if result["status"] == "success":
            # Ensure download folder exists
            folder = get_download_folder()
            ffmpeg_status = check_ffmpeg_status()

            return jsonify(
                {
                    "status": "success",
                    "settings": result["settings"],
                    "download_folder": folder,
                    "ffmpeg": ffmpeg_status,
                }
            )
        else:
            return jsonify(result), 400

    @app.route("/browse-folder", methods=["POST"])
    def browse_folder():
        """Return current download folder path for frontend to display"""
        from settings import get_download_folder

        return jsonify({"path": get_download_folder()})

    @app.route("/open-folder", methods=["POST"])
    def open_folder():
        """Open the download folder in file explorer"""
        from settings import get_download_folder
        import subprocess
        import platform

        folder = get_download_folder()

        try:
            if platform.system() == "Windows":
                subprocess.Popen(f'explorer "{folder}"')
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])

            return jsonify({"status": "success", "folder": folder})
        except Exception as e:
            return jsonify({"status": "error", "error": str(e)}), 500
