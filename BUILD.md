# YT Downloader - Build Instructions

## Prerequisites

- Node.js 20+
- Python 3.11+
- FFmpeg (for audio extraction)

## Development Mode

1. Install frontend dependencies:
   ```bash
   cd frontend
   npm install
   ```

2. Build frontend:
   ```bash
   npm run build
   ```

3. Install root dependencies:
   ```bash
   cd ..
   npm install
   ```

4. Run in development mode:
   ```bash
   npm start
   ```

## Build Production Executable

### 1. Build Frontend
```bash
cd frontend
npm run build
cd ..
```

### 2. Build Backend (Python to EXE)
```bash
cd backend
pip install pyinstaller
pyinstaller app.spec --distpath dist --clean -y
cd ..
```

### 3. Build Electron App
```bash
# Using electron-packager (simpler, portable)
npx @electron/packager . "YT Downloader" --platform=win32 --arch=x64 --out=dist-packaged --icon=icon.ico --overwrite
```

### 4. Copy Backend Resources
After packaging, copy these files to `dist-packaged/YT Downloader-win32-x64/resources/`:
- `backend/dist/app.exe`
- `icon.ico`
- `cookies.txt`

## Output

The final app is in: `dist-packaged/YT Downloader-win32-x64/`

Run: `YT Downloader.exe`

## App Structure

```
YT Downloader-win32-x64/
├── YT Downloader.exe    (Main Electron app)
├── resources/
│   ├── app.asar         (Frontend + main.js)
│   ├── app.exe          (Python backend)
│   ├── icon.ico
│   └── cookies.txt
└── ... (Electron runtime files)
```

## Icon

The app icon is located at `frontend/src/downloadicon.png` and converted to `icon.ico` for Windows.

To regenerate the icon:
```bash
node convert-icon.js
```
