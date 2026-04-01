"""
YouTube Audio Downloader - Backend Server
Main entry point for Flask application with modular architecture
"""
import sys
import os
from flask import Flask, request
from flask_cors import CORS
from config import LOG_FILE, COOKIES_FILE, PORT, DEBUG
from logger import log_info, log_success, log_warning
from routes import register_routes

# Configure UTF-8 for Windows console
sys.stdout.reconfigure(encoding="utf-8")

# Create Flask app
app = Flask(__name__)
CORS(app)

# Register routes
register_routes(app)


if __name__ == "__main__":
    import shutil
    from config import MAX_WORKERS, DOWNLOAD_FOLDER, AUDIO_FORMAT, RATE_LIMIT_DELAY, MAX_RETRIES

    ffmpeg_available = shutil.which("ffmpeg") is not None

    log_info(f"\n{'='*80}")
    log_success(f"🚀 YouTube Audio Downloader Backend Server")
    log_info(f"{'='*80}")
    log_info(f"🌐 Server: http://localhost:{PORT}")
    log_info(f"📂 Download folder: {os.path.abspath(DOWNLOAD_FOLDER)}")
    log_info(f"🎵 Audio format: {AUDIO_FORMAT}")
    log_info(f"👥 Max concurrent workers: {MAX_WORKERS}")
    log_info(f"⏱️  Rate limit delay: {RATE_LIMIT_DELAY}s")
    log_info(f"🔄 Max retries per video: {MAX_RETRIES}")
    log_info(f"🍪 Cookies file: {os.path.abspath(COOKIES_FILE)} ({'✅ Found' if os.path.exists(COOKIES_FILE) else '❌ Not found'})")
    log_info(f"🎬 FFmpeg: {'✅ Available' if ffmpeg_available else '⚠️ NOT FOUND - Install FFmpeg for audio conversion!'}")
    log_info(f"📋 Logs: {os.path.abspath(LOG_FILE)}")
    log_info(f"{'='*80}\n")
    
    if not ffmpeg_available:
        log_warning("⚠️  FFmpeg not found! Audio will be downloaded in original format (webm/m4a).")
        log_warning("    Install FFmpeg: https://ffmpeg.org/download.html")
        log_warning("    Or use: winget install FFmpeg")

    app.run(port=PORT, debug=DEBUG, threaded=True)
