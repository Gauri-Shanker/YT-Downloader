# YouTube Audio Downloader - User Manual

Welcome to the **YouTube Audio Downloader**. This guide provides step-by-step instructions on how to use the application effectively, configure it to your needs, and troubleshoot any issues that might arise.

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- **Python 3.9+** installed on your computer.
- **Node.js** (for running the React frontend desktop app).

### 2. Installation
1. Navigate to the `backend` folder and install the dependencies.
   ```bash
   cd backend
   pip install -r requirements.txt
   ```
2. Navigate to the `yt-downloader` folder and install the frontend packages.
   ```bash
   cd yt-downloader
   npm install
   ```

### 3. Running the Application
To start the app, you need to run both the backend server and the frontend client.
1. **Start the API Server:**
   ```bash
   cd backend
   python app.py
   ```
2. **Start the Desktop Interface:**
   ```bash
   cd yt-downloader
   npm start
   ```
The interface will open and automatically route your downloads to the `downloads` folder in the project directory.

---

## ⚙️ How it Works
The application uses **yt-dlp** (an advanced YouTube data extraction tool) to find and extract the highest-quality audio format seamlessly in the background. It manages batch downloads efficiently and includes built-in rate-limiting, retries, and thread safety.

**By default:**
- Trims filenames automatically to prevent Windows `MAX_PATH` errors.
- Silences standard output completely to ensure absolute stability on Windows.
- Automatically handles concurrent extractions via hidden worker threads.

---

## 🛠️ Advanced Features & Configuration

### Using Proxies
If you are running a system proxy (like V2Ray, Clash, Webshare, etc.), the application will **automatically route traffic** through your Windows network proxy. This is highly recommended if you plan on downloading hundreds of videos to avoid YouTube IP "Bot" bans. No extra code changes are required!

### Using Cookies (For Age-Restricted & Private Videos)
If you encounter videos that require a login, you can safely pass your profile to the app:
1. Install an extension like `Get cookies.txt locally` on your browser.
2. Go to YouTube and log into your account.
3. Export your cookies and name the file exactly `cookies.txt`.
4. Place the file **directly into the application's root directory** (next to the `backend` folder). 
   *Note: Using cookies may occasionally cause YouTube to block audio formats if they suspect the request is machine-generated.*

---

## 🚨 Troubleshooting Common Errors

### 1. `[Errno 22] Invalid argument`
- **What it means:** A severe Windows OS-level socket error or thread crash.
- **How it's resolved:** This architecture includes a hardcoded `"quiet": True` protocol in `ydl_options.py`. This explicitly tells the workers not to stream their progress bar to hidden Windows system threads, which is the primary cause of `[Errno 22]`. Under zero circumstances should you change `quiet` to `False` on a Windows deployment!

### 2. `Sign in to confirm you’re not a bot (HTTP Error 429)`
- **What it means:** YouTube has temporarily blacklisted your IP Address for making too many rapid requests. You have been flagged as an extraction bot.
- **Solution A:** Temporarily enable a local system proxy or VPN to acquire a fresh residential IP.
- **Solution B:** Pause your downloading for 1 to 2 hours until the cooldown expires naturally.
- **Solution C:** Provide a `cookies.txt` file (see the "Using Cookies" section).

### 3. `Requested format is not available`
- **What it means:** The video exists, but YouTube is refusing to deliver the specific audio stream to this client.
- **Solution:** This almost exclusively occurs when you use a `cookies.txt` exported from Chrome, but YouTube’s advanced token validation (PO-Token) rejects the extraction. In these cases, simply delete the `cookies.txt` file from the directory so the application runs anonymously again. 

### 4. `SSL: CERTIFICATE_VERIFY_FAILED`
- **What it means:** Your local proxy or antivirus program is attempting to intercept HTTPS traffic without trusting the certificate.
- **Solution:** Add YouTube to the exclusion zone of your system proxy/firewall, or update Python's `certifi` package.

---

## 🆘 Reporting Issues & Keeping Updated

Because YouTube constantly updates its security and fingerprinting checks (sometimes daily), any application relying on YouTube extractors needs to stay updated. If a video fundamentally refuses to download regardless of proxies or cookies:

1. **Verify it is a core issue:** Update `yt-dlp` to the absolute latest version:
   ```bash
   pip install yt-dlp --upgrade
   ```
2. **If the issue continues:** It means YouTube has modified their site code and the extraction engine is broken globally. Please visit the official **[yt-dlp GitHub Repository Tracker](https://github.com/yt-dlp/yt-dlp/issues)**. Search for the error text to see if the maintainers have released a patch!
