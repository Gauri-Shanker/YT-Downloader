# 🎬 YT Downloader

A powerful desktop application for downloading YouTube videos and audio with a modern UI. Built with **Electron + React** frontend and **Flask + Python** backend.

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)
![Python](https://img.shields.io/badge/python-3.10+-green.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)

---

## ✨ Features

### Download Modes
| Mode | Description | Output |
|------|-------------|--------|
| 🎵 **Audio** | Extract audio from videos | MP3 (192kbps) |
| 🎬 **Video** | Download video with audio | MP4 (up to 4K) |
| 🎵+🎬 **Both** | Download audio & video separately | MP3 + MP4 |
| ⚙️ **Custom** | Choose specific quality (360p-4K) | MP4 |

### Core Features
- **Bulk Downloads** - Process multiple videos at once
- **Auto-Retry** - Automatic retry with exponential backoff
- **Format Preview** - View all available formats with file sizes
- **Auto Best Quality** - One-click highest quality download
- **FFmpeg Integration** - Automatic video/audio merging
- **Cookies Support** - For age-restricted/private videos

### Desktop App Features
- **Configurable Settings** - Set download folder & FFmpeg path
- **One-Click Folder Access** - Open download folder from app
- **Native File Dialogs** - Browse and select folders easily
- **Custom App Icon** - Professional desktop appearance

---

## 🏗️ Project Structure

```
yt-desktop/
├── backend/                    # Flask Backend (Python)
│   ├── app.py                 # Flask entry point
│   ├── routes.py              # API endpoints
│   ├── downloader.py          # Download logic
│   ├── ydl_options.py         # yt-dlp configuration
│   ├── settings.py            # User settings management
│   ├── config.py              # App configuration
│   └── requirements.txt       # Python dependencies
│
├── frontend/                   # React Frontend
│   ├── src/
│   │   ├── App.jsx
│   │   └── components/
│   │       └── Downloader.jsx # Main UI component
│   └── package.json
│
├── main.js                     # Electron main process
├── preload.js                  # Electron preload script
└── package.json                # Electron dependencies
```

### Tech Stack
| Component | Technology |
|-----------|------------|
| Desktop | Electron |
| Frontend | React 18 + Vite |
| Backend | Flask (Python) |
| Downloader | yt-dlp |
| Media | FFmpeg |
| UI | Bootstrap 5 |

---

## 🚀 Installation

### Prerequisites
- **Python 3.10+** - [Download](https://www.python.org/downloads/)
- **Node.js 18+** - [Download](https://nodejs.org/)
- **FFmpeg** - [Download](https://ffmpeg.org/download.html)

### Setup

```bash
# Clone the repository
git clone https://github.com/Gauri-Shanker/YT-Downloader.git
cd YT-Downloader

# Install backend dependencies
cd backend
pip install -r requirements.txt

# Install frontend dependencies
cd ../frontend
npm install

# Install Electron dependencies (root)
cd ..
npm install
```

### Environment Configuration

Create a `.env` file in **both** the root directory and `backend/` folder:

**Root `.env`** (for Electron):
```env
# Backend Configuration
FLASK_ENV=production
DOWNLOAD_FOLDER=downloads
MAX_WORKERS=2
AUDIO_FORMAT=webm
RATE_LIMIT_DELAY=2.0
MAX_RETRIES=3
COOKIES_FILE=cookies.txt
DOWNLOAD_TIMEOUT=300

# Optional: Add proxy if needed
# PROXY=http://proxy.example.com:8080
```

**`backend/.env`** (for Flask):
```env
# Download settings
DOWNLOAD_FOLDER=downloads
MAX_WORKERS=2
AUDIO_FORMAT=mp3
RATE_LIMIT_DELAY=2.0
MAX_RETRIES=3

# Server settings
PORT=5000
DEBUG=True
DOWNLOAD_TIMEOUT=300
```

| Variable | Description | Default |
|----------|-------------|---------|
| `DOWNLOAD_FOLDER` | Where downloaded files are saved | `downloads` |
| `MAX_WORKERS` | Concurrent download threads | `2` |
| `AUDIO_FORMAT` | Audio output format (mp3/webm) | `mp3` |
| `RATE_LIMIT_DELAY` | Delay between requests (seconds) | `2.0` |
| `MAX_RETRIES` | Number of retry attempts | `3` |
| `DOWNLOAD_TIMEOUT` | Max download time (seconds) | `300` |
| `COOKIES_FILE` | Path to cookies.txt for auth | `cookies.txt` |
| `PORT` | Backend server port | `5000` |
| `DEBUG` | Enable debug mode | `True` |

> **Quick Setup:** Copy the example files:
> ```bash
> cp .env.example .env
> cp backend/.env.example backend/.env
> ```
> Then edit with your preferred settings.

### Run in Development

```bash
# Terminal 1: Start backend
cd backend
python app.py

# Terminal 2: Start frontend dev server
cd frontend
npm run dev

# Terminal 3: Start Electron
npm start
```

---

## 📦 Building

### Build Backend (PyInstaller)

```bash
cd backend
pyinstaller --onefile --name app --add-data "cookies.txt;." app.py
```

### Build Desktop App (Electron)

```bash
# Package for Windows
npx @electron/packager . "YT Downloader" --platform=win32 --arch=x64 --icon=icon.ico --out=dist-packaged --overwrite
```

---

## 📖 Usage

### Single Download
1. Paste YouTube URL
2. Select mode (Audio/Video/Both/Custom)
3. Click download button
4. File saved to download folder

### Bulk Download
1. Paste multiple URLs (one per line)
2. Select mode
3. Click download - all processed sequentially

### Custom Quality
1. Select ⚙️ Custom mode
2. Click "Get Formats"
3. Choose quality or click "Auto Best"

### Settings
Click the ⚙️ gear icon to configure:
- **Download Folder** - Where files are saved
- **FFmpeg Path** - Path to FFmpeg installation

---

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Server status |
| `/download-sync` | POST | Download with mode (audio/video/both) |
| `/formats` | POST | Get available formats |
| `/download-format` | POST | Download specific format |
| `/settings` | GET/POST | Get/Save user settings |

---

## 🔧 Troubleshooting

### FFmpeg not found
Install FFmpeg and ensure it's in PATH, or set the path in Settings.

### No formats available
- Video may be private/age-restricted (use cookies)
- Update yt-dlp: `pip install -U yt-dlp`

### Rate limiting (429 error)
Wait a few minutes before retrying. Use cookies for better success rate.

### Signature extraction failed
Ensure Node.js is installed and in PATH.

---

## 🍪 Cookies Setup (Optional)

For age-restricted or private videos:

1. Install browser extension "Get cookies.txt LOCALLY"
2. Go to YouTube while logged in
3. Export cookies
4. Save as `cookies.txt` in project root

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/NewFeature`)
3. Commit changes (`git commit -m 'Add NewFeature'`)
4. Push to branch (`git push origin feature/NewFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## ⚠️ Disclaimer

This tool is for personal use only. Please respect YouTube's Terms of Service and copyright laws. Only download content you have the right to download.

---

## 🙏 Acknowledgments

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - YouTube download library
- [FFmpeg](https://ffmpeg.org/) - Media processing
- [Electron](https://www.electronjs.org/) - Desktop framework
- [Flask](https://flask.palletsprojects.com/) - Backend framework
- [React](https://reactjs.org/) - Frontend library

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/Gauri-Shanker">Gauri-Shanker</a>
</p>
