import React, { useState, useEffect } from "react";

const Downloader = () => {
  const [singleLink, setSingleLink] = useState("");
  const [bulkLinks, setBulkLinks] = useState("");
  const [status, setStatus] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [downloads, setDownloads] = useState([]);
  const [downloadMode, setDownloadMode] = useState("audio"); // audio | video | both | custom

  // Format selection state
  const [formats, setFormats] = useState(null);
  const [loadingFormats, setLoadingFormats] = useState(false);

  // Settings state
  const [showSettings, setShowSettings] = useState(false);
  const [settings, setSettings] = useState({
    download_folder: "",
    ffmpeg_path: "",
  });
  const [ffmpegStatus, setFfmpegStatus] = useState({ available: false });
  const [settingsLoading, setSettingsLoading] = useState(false);
  const [settingsSaved, setSettingsSaved] = useState(false);

  // Load settings on mount
  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const response = await fetch("http://localhost:5000/settings");
      if (response.ok) {
        const data = await response.json();
        setSettings(data.settings || {});
        setFfmpegStatus(data.ffmpeg || { available: false });
      }
    } catch (err) {
      console.error("Error loading settings:", err);
    }
  };

  const saveSettings = async () => {
    setSettingsLoading(true);
    setSettingsSaved(false);
    try {
      const response = await fetch("http://localhost:5000/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settings),
      });
      if (response.ok) {
        const data = await response.json();
        setSettings(data.settings || settings);
        setFfmpegStatus(data.ffmpeg || { available: false });
        setSettingsSaved(true);
        setTimeout(() => setSettingsSaved(false), 3000);
      }
    } catch (err) {
      console.error("Error saving settings:", err);
    } finally {
      setSettingsLoading(false);
    }
  };

  const openDownloadFolder = async () => {
    try {
      // Try Electron API first, fallback to backend
      if (window.electronAPI?.openPath) {
        await window.electronAPI.openPath(settings.download_folder);
      } else {
        await fetch("http://localhost:5000/open-folder", { method: "POST" });
      }
    } catch (err) {
      console.error("Error opening folder:", err);
    }
  };

  const browseFolder = async () => {
    try {
      if (window.electronAPI?.selectFolder) {
        const folder = await window.electronAPI.selectFolder();
        if (folder) {
          setSettings({ ...settings, download_folder: folder });
        }
      } else {
        // In browser, user must type the path manually
        alert("Folder selection is only available in the desktop app. Please type the path manually.");
      }
    } catch (err) {
      console.error("Error browsing folder:", err);
    }
  };

  const browseFfmpeg = async () => {
    try {
      if (window.electronAPI?.selectFolder) {
        const folder = await window.electronAPI.selectFolder();
        if (folder) {
          setSettings({ ...settings, ffmpeg_path: folder });
        }
      } else {
        alert("Folder selection is only available in the desktop app. Please type the path manually.");
      }
    } catch (err) {
      console.error("Error browsing FFmpeg folder:", err);
    }
  };

  // Fetch available formats for a URL
  const fetchFormats = async (url) => {
    if (!url.trim()) {
      setStatus("⚠️ Please enter a YouTube URL first");
      return;
    }

    setLoadingFormats(true);
    setFormats(null);
    setStatus("🔍 Fetching available formats...");

    try {
      const response = await fetch("http://localhost:5000/formats", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url.trim() }),
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch formats: ${response.status}`);
      }

      const data = await response.json();
      setFormats(data);
      setStatus(`✅ Found ${(data.video_audio?.length || 0) + (data.video_only?.length || 0)} video formats`);
    } catch (err) {
      console.error("Error fetching formats:", err);
      setStatus(`❌ Error: ${err.message}`);
    } finally {
      setLoadingFormats(false);
    }
  };

  // Download specific format
  const downloadFormat = async (formatInfo, autoBest = false) => {
    const url = singleLink.trim();
    if (!url) {
      setStatus("⚠️ No URL provided");
      return;
    }

    setIsLoading(true);
    const qualityLabel = autoBest ? "best quality" : (formatInfo?.height ? `${formatInfo.height}p` : "selected format");
    setStatus(`⏳ Downloading ${qualityLabel}...`);

    const downloadItem = {
      url,
      status: "downloading",
      mode: "custom",
      format: formatInfo,
      autoBest,
    };
    setDownloads([downloadItem]);

    try {
      const requestBody = { url };

      if (autoBest) {
        requestBody.auto_best = true;
      } else {
        requestBody.video_format_id = formatInfo.format_id;
        requestBody.has_audio = formatInfo.has_audio;
      }

      const response = await fetch("http://localhost:5000/download-format", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
      });

      const result = await response.json();

      if (result.status === "success") {
        setDownloads([{ ...downloadItem, ...result, status: "success" }]);
        setStatus(`✅ Downloaded: ${result.file}`);
      } else {
        setDownloads([{ ...downloadItem, ...result, status: "failed" }]);
        setStatus(`❌ Failed: ${result.error}`);
      }
    } catch (err) {
      console.error("Download error:", err);
      setDownloads([{ ...downloadItem, status: "failed", error: err.message }]);
      setStatus(`❌ Error: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  // Original download flow (audio/video/both modes)
  const startDownload = async (links, mode) => {
    const modeLabels = { audio: "🎵 Audio", video: "🎬 Video", both: "🎵+🎬 Both" };
    console.log(`🚀 Starting ${modeLabels[mode]} downloads...`);

    let completedCount = 0;
    const totalCount = links.length;

    for (let index = 0; index < links.length; index++) {
      const url = links[index];
      setStatus(`⏳ Processing ${index + 1}/${totalCount} (${modeLabels[mode]})...`);

      try {
        setDownloads((prev) =>
          prev.map((item) =>
            item.url === url ? { ...item, status: "downloading", mode } : item
          )
        );

        const response = await fetch("http://localhost:5000/download-sync", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url, mode }),
        });

        if (!response.ok) throw new Error(`Backend error: ${response.status}`);

        const result = await response.json();
        setDownloads((prev) =>
          prev.map((item) => (item.url === url ? { ...item, ...result } : item))
        );
        completedCount++;
      } catch (err) {
        console.error(`❌ Error downloading ${url}:`, err);
        setDownloads((prev) =>
          prev.map((item) =>
            item.url === url
              ? { ...item, status: "failed", error: err.message }
              : item
          )
        );
        completedCount++;
      }
    }

    setStatus(`✅ All ${completedCount}/${totalCount} downloads completed!`);
    setIsLoading(false);
  };

  const handleDownload = () => {
    if (downloadMode === "custom") {
      fetchFormats(singleLink);
      return;
    }

    let links = [];
    if (singleLink.trim()) links.push(singleLink.trim());
    if (bulkLinks.trim()) {
      links = [...links, ...bulkLinks.split("\n").map((l) => l.trim()).filter(Boolean)];
    }

    // Remove duplicates
    links = [...new Set(links)];

    if (links.length === 0) {
      setStatus("⚠️ Please enter at least one link");
      return;
    }

    // Clear input boxes after collecting links
    setSingleLink("");
    setBulkLinks("");

    setIsLoading(true);
    setFormats(null);
    const modeLabels = { audio: "🎵 Audio", video: "🎬 Video", both: "🎵+🎬 Both" };
    setStatus(`⏳ Starting ${modeLabels[downloadMode]} download for ${links.length} video(s)...`);

    setDownloads(links.map((l) => ({ url: l, status: "pending", mode: downloadMode })));
    startDownload(links, downloadMode);
  };

  const formatSize = (sizeMb, estimated = false) => {
    if (!sizeMb) return "~";
    const size = sizeMb >= 1000 ? `${(sizeMb / 1000).toFixed(1)} GB` : `${sizeMb.toFixed(1)} MB`;
    return estimated ? `~${size}` : size;
  };

  const formatDuration = (seconds) => {
    if (!seconds) return "";
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  const modes = [
    { id: "audio", label: "🎵 Audio", color: "#667eea, #764ba2" },
    { id: "video", label: "🎬 Video", color: "#e74c3c, #c0392b" },
    { id: "both", label: "🎵+🎬 Both", color: "#27ae60, #2ecc71" },
    { id: "custom", label: "⚙️ Custom", color: "#f39c12, #e67e22" },
  ];

  const modeDescriptions = {
    audio: "Extract audio as MP3 file",
    video: "Download video with audio merged (MP4)",
    both: "Download audio and video as separate files",
    custom: "Choose specific video quality (720p, 1080p, etc.)",
  };

  const getButtonGradient = () => {
    const gradients = {
      audio: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
      video: "linear-gradient(135deg, #e74c3c 0%, #c0392b 100%)",
      both: "linear-gradient(135deg, #27ae60 0%, #2ecc71 100%)",
      custom: "linear-gradient(135deg, #f39c12 0%, #e67e22 100%)",
    };
    return gradients[downloadMode];
  };

  return (
    <div className="min-vh-100 d-flex align-items-center justify-content-center p-4" style={{ background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)" }}>
      <div className="container" style={{ maxWidth: "1100px" }}>
        <div className="card border-0 shadow-xl rounded-4 overflow-hidden" style={{ backdropFilter: "blur(10px)", background: "rgba(255, 255, 255, 0.98)" }}>

          {/* Header */}
          <div className="card-header border-0 bg-transparent pt-5 pb-3 px-5">
            <div className="d-flex align-items-center gap-3 justify-content-between">
              <div className="d-flex align-items-center gap-3">
                <div className="rounded-3 p-2" style={{ background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)" }}>
                  <i className="fab fa-youtube text-white fs-4"></i>
                </div>
                <div>
                  <h1 className="display-6 fw-bold mb-0" style={{ background: "linear-gradient(135deg, #667eea, #764ba2)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text" }}>
                    YouTube Downloader
                  </h1>
                  <p className="text-muted small mt-1 mb-0">Download audio, video, or choose specific quality</p>
                </div>
              </div>
              <div className="d-flex gap-2">
                <button
                  className="btn btn-outline-secondary rounded-pill px-3"
                  onClick={openDownloadFolder}
                  title="Open Download Folder"
                >
                  <i className="fas fa-folder-open"></i>
                </button>
                <button
                  className="btn btn-outline-primary rounded-pill px-3"
                  onClick={() => setShowSettings(!showSettings)}
                  title="Settings"
                >
                  <i className="fas fa-cog"></i>
                </button>
              </div>
            </div>
          </div>

          {/* Settings Panel */}
          {showSettings && (
            <div className="px-5 pb-4">
              <div className="p-4 rounded-4" style={{ background: "#f0f4ff", border: "1px solid #d4deff" }}>
                <div className="d-flex justify-content-between align-items-center mb-3">
                  <h5 className="fw-bold mb-0"><i className="fas fa-cog me-2"></i>Settings</h5>
                  <button className="btn btn-sm btn-outline-secondary rounded-pill" onClick={() => setShowSettings(false)}>
                    <i className="fas fa-times"></i>
                  </button>
                </div>

                {/* Download Folder */}
                <div className="mb-3">
                  <label className="form-label fw-semibold">
                    <i className="fas fa-folder me-2 text-primary"></i>Download Folder
                  </label>
                  <div className="input-group">
                    <input
                      type="text"
                      className="form-control"
                      value={settings.download_folder || ""}
                      onChange={(e) => setSettings({ ...settings, download_folder: e.target.value })}
                      placeholder="e.g., C:\Users\YourName\Downloads\YT-Downloads"
                    />
                    <button className="btn btn-outline-secondary" onClick={browseFolder} title="Browse for folder">
                      <i className="fas fa-folder-open"></i>
                    </button>
                    <button className="btn btn-outline-primary" onClick={openDownloadFolder} title="Open folder in explorer">
                      <i className="fas fa-external-link-alt"></i>
                    </button>
                  </div>
                  <small className="text-muted">Where downloaded files will be saved</small>
                </div>

                {/* FFmpeg Path */}
                <div className="mb-3">
                  <label className="form-label fw-semibold">
                    <i className="fas fa-video me-2 text-success"></i>FFmpeg Path
                    {ffmpegStatus.available ? (
                      <span className="badge bg-success ms-2">Available</span>
                    ) : (
                      <span className="badge bg-warning text-dark ms-2">Not Found</span>
                    )}
                  </label>
                  <div className="input-group">
                    <input
                      type="text"
                      className="form-control"
                      value={settings.ffmpeg_path || ""}
                      onChange={(e) => setSettings({ ...settings, ffmpeg_path: e.target.value })}
                      placeholder="Leave empty for auto-detect, or enter path like C:\ffmpeg\bin"
                    />
                    <button className="btn btn-outline-secondary" onClick={browseFfmpeg} title="Browse for FFmpeg folder">
                      <i className="fas fa-folder-open"></i>
                    </button>
                  </div>
                  <small className="text-muted">
                    {ffmpegStatus.available ? (
                      <>FFmpeg found at: {ffmpegStatus.path} ({ffmpegStatus.source})</>
                    ) : (
                      <>FFmpeg is required for audio extraction. <a href="https://ffmpeg.org/download.html" target="_blank" rel="noreferrer">Download FFmpeg</a></>
                    )}
                  </small>
                </div>

                {/* Save Button */}
                <div className="d-flex justify-content-end gap-2">
                  {settingsSaved && (
                    <span className="text-success align-self-center me-2">
                      <i className="fas fa-check-circle me-1"></i>Saved!
                    </span>
                  )}
                  <button
                    className="btn btn-primary rounded-pill px-4"
                    onClick={saveSettings}
                    disabled={settingsLoading}
                  >
                    {settingsLoading ? (
                      <><span className="spinner-border spinner-border-sm me-2"></span>Saving...</>
                    ) : (
                      <><i className="fas fa-save me-2"></i>Save Settings</>
                    )}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Mode Selector */}
          <div className="px-5 pb-3">
            <div className="d-flex gap-2 justify-content-center flex-wrap">
              {modes.map((mode) => (
                <button
                  key={mode.id}
                  className={`btn rounded-pill px-4 py-2 fw-semibold ${downloadMode === mode.id ? "text-white" : "btn-outline-secondary"}`}
                  style={{
                    background: downloadMode === mode.id ? `linear-gradient(135deg, ${mode.color})` : "transparent",
                    border: downloadMode === mode.id ? "none" : "2px solid #dee2e6",
                  }}
                  onClick={() => { setDownloadMode(mode.id); setFormats(null); }}
                  disabled={isLoading}
                >
                  {mode.label}
                </button>
              ))}
            </div>
            <p className="text-muted small text-center mt-2 mb-0">{modeDescriptions[downloadMode]}</p>
          </div>

          <div className="card-body px-5 pb-5">
            <div className="row g-4">
              {/* Single Link */}
              <div className={downloadMode === "custom" ? "col-12" : "col-md-5"}>
                <div className="p-4 rounded-4 h-100" style={{ background: "#f8f9ff", border: "1px solid #e9ecef" }}>
                  <div className="d-flex align-items-center gap-2 mb-3">
                    <i className="fas fa-link text-primary"></i>
                    <h5 className="fw-semibold mb-0">YouTube Link</h5>
                  </div>
                  <input
                    type="text"
                    className="form-control form-control-lg border-0 rounded-3 py-3"
                    style={{ background: "white", boxShadow: "0 2px 8px rgba(0,0,0,0.04)" }}
                    placeholder="Paste YouTube link..."
                    value={singleLink}
                    onChange={(e) => { setSingleLink(e.target.value); setFormats(null); }}
                  />
                  <button
                    className="btn w-100 mt-4 py-3 rounded-3 fw-semibold text-white"
                    style={{ background: getButtonGradient(), opacity: isLoading || loadingFormats ? 0.7 : 1 }}
                    onClick={handleDownload}
                    disabled={isLoading || loadingFormats}
                  >
                    {isLoading || loadingFormats ? (
                      <><span className="spinner-border spinner-border-sm me-2"></span>{loadingFormats ? "Fetching..." : "Processing..."}</>
                    ) : (
                      <><i className={`fas ${downloadMode === "custom" ? "fa-search" : "fa-download"} me-2`}></i>{downloadMode === "custom" ? "Get Formats" : "Download"}</>
                    )}
                  </button>
                </div>
              </div>

              {/* Bulk Links (hidden in custom mode) */}
              {downloadMode !== "custom" && (
                <div className="col-md-7">
                  <div className="p-4 rounded-4 h-100" style={{ background: "#f8f9ff", border: "1px solid #e9ecef" }}>
                    <div className="d-flex align-items-center gap-2 mb-3">
                      <i className="fas fa-layer-group text-success"></i>
                      <h5 className="fw-semibold mb-0">Bulk Links</h5>
                      <span className="badge bg-light text-dark ms-2 rounded-pill px-3">One per line</span>
                    </div>
                    <textarea
                      className="form-control border-0 rounded-3 py-3"
                      rows="5"
                      style={{ background: "white", resize: "none", boxShadow: "0 2px 8px rgba(0,0,0,0.04)" }}
                      placeholder="Paste YouTube links (one per line)"
                      value={bulkLinks}
                      onChange={(e) => setBulkLinks(e.target.value)}
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Format Selection UI */}
            {downloadMode === "custom" && formats && (
              <div className="mt-4 p-4 rounded-4" style={{ background: "#f8f9ff", border: "1px solid #e9ecef" }}>
                {/* Video Info */}
                <div className="d-flex align-items-center gap-3 mb-4 pb-3 border-bottom flex-wrap">
                  {formats.thumbnail && (
                    <img src={formats.thumbnail} alt="Thumbnail" className="rounded-3" style={{ width: "120px", height: "68px", objectFit: "cover" }} />
                  )}
                  <div className="flex-grow-1">
                    <h5 className="fw-bold mb-1" style={{ fontSize: "1rem" }}>{formats.title}</h5>
                    <small className="text-muted">{formats.duration ? formatDuration(formats.duration) : ""}</small>
                  </div>
                  <button
                    className="btn btn-lg rounded-pill px-4 fw-semibold text-white"
                    style={{ background: "linear-gradient(135deg, #00b894 0%, #00cec9 100%)" }}
                    onClick={() => downloadFormat(null, true)}
                    disabled={isLoading}
                  >
                    <i className="fas fa-bolt me-2"></i>Auto Best
                  </button>
                </div>

                {/* Video + Audio */}
                {formats.video_audio?.length > 0 && (
                  <div className="mb-4">
                    <h6 className="fw-bold text-success mb-3"><i className="fas fa-check-circle me-2"></i>Video + Audio (Ready)</h6>
                    <div className="row g-2">
                      {formats.video_audio.map((fmt, idx) => (
                        <div key={idx} className="col-md-6 col-lg-4">
                          <button
                            className="btn w-100 p-3 rounded-3 text-start"
                            style={{ background: "white", border: "1px solid #e9ecef" }}
                            onClick={() => downloadFormat(fmt)}
                            disabled={isLoading}
                          >
                            <div className="d-flex justify-content-between align-items-center">
                              <div>
                                <span className="fw-bold text-dark">{fmt.height}p</span>
                                {fmt.fps > 30 && <span className="badge bg-warning text-dark ms-2" style={{ fontSize: "10px" }}>{fmt.fps}fps</span>}
                              </div>
                              <span className="badge bg-success">{fmt.ext.toUpperCase()}</span>
                            </div>
                            <small className="text-muted">{formatSize(fmt.size_mb, fmt.size_estimated)} • {fmt.vcodec?.split(".")[0] || "?"}</small>
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Video Only */}
                {formats.video_only?.length > 0 && (
                  <div>
                    <h6 className="fw-bold text-primary mb-3"><i className="fas fa-film me-2"></i>Video Only (Will merge audio)</h6>
                    <div className="row g-2">
                      {formats.video_only.map((fmt, idx) => (
                        <div key={idx} className="col-md-6 col-lg-4">
                          <button
                            className="btn w-100 p-3 rounded-3 text-start"
                            style={{ background: "white", border: "1px solid #e9ecef" }}
                            onClick={() => downloadFormat(fmt)}
                            disabled={isLoading}
                          >
                            <div className="d-flex justify-content-between align-items-center">
                              <div>
                                <span className="fw-bold text-dark">{fmt.height}p</span>
                                {fmt.fps > 30 && <span className="badge bg-warning text-dark ms-2" style={{ fontSize: "10px" }}>{fmt.fps}fps</span>}
                              </div>
                              <span className="badge bg-primary">{fmt.ext.toUpperCase()}</span>
                            </div>
                            <small className="text-muted">{formatSize(fmt.size_mb, fmt.size_estimated)} • {fmt.vcodec?.split(".")[0] || "?"} <span className="text-info">+ audio</span></small>
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {!formats.video_audio?.length && !formats.video_only?.length && (
                  <div className="text-center py-4 text-muted">
                    <i className="fas fa-exclamation-triangle fa-2x mb-2"></i>
                    <p>No MP4/WebM formats found</p>
                  </div>
                )}
              </div>
            )}

            {/* Status */}
            {status && <div className="mt-4 p-3 rounded-3 text-center">{status}</div>}

            {/* Results */}
            {downloads.length > 0 && (
              <div className="mt-4">
                {downloads.map((item, i) => (
                  <div key={i} className="p-3 border-bottom d-flex justify-content-between align-items-start">
                    <div style={{ width: "90%" }}>
                      <div className="d-flex align-items-center gap-2 flex-wrap">
                        {item.status === "pending" && "⏳"}
                        {item.status === "downloading" && "🔄"}
                        {item.status === "success" && "✅"}
                        {item.status === "failed" && "❌"}
                        <span style={{ wordBreak: "break-all", fontSize: "0.9rem" }}>{item.url}</span>
                        {item.mode && <span className="badge bg-secondary ms-2" style={{ fontSize: "10px" }}>{item.mode}</span>}
                        {item.format?.height && <span className="badge bg-info ms-1" style={{ fontSize: "10px" }}>{item.format.height}p</span>}
                        {item.autoBest && <span className="badge bg-success ms-1" style={{ fontSize: "10px" }}>Auto</span>}
                      </div>

                      {item.status === "downloading" && (
                        <div className="small text-muted mt-1">Processing...</div>
                      )}

                      {item.status === "success" && (
                        <div className="small text-success mt-2">
                          {item.files ? (
                            <>{item.files.map((f, j) => <div key={j}>{j === 0 ? "🎵" : "🎬"} {f}</div>)}</>
                          ) : (
                            <><div>📁 {item.file}</div><div className="text-muted" style={{ fontSize: "11px" }}>{item.path}</div>{item.size_mb && <div className="text-muted" style={{ fontSize: "11px" }}>Size: {item.size_mb} MB</div>}</>
                          )}
                        </div>
                      )}

                      {item.status === "failed" && (
                        <div className="small text-danger mt-2">{item.error || "Unknown error"}</div>
                      )}
                    </div>
                    {item.status === "downloading" && <span className="spinner-border spinner-border-sm"></span>}
                  </div>
                ))}
              </div>
            )}

            {/* Footer */}
            <div className="mt-4 pt-3 border-top text-center">
              <div className="d-flex flex-wrap justify-content-center gap-4">
                <small className="text-muted">🎵 MP3 Audio</small>
                <small className="text-muted">🎬 MP4/WebM Video</small>
                <small className="text-muted">⚙️ Custom Quality</small>
                <small className="text-muted">🔒 Secure</small>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Downloader;
