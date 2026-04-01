const { contextBridge, ipcRenderer } = require("electron");

// Expose protected methods to the renderer process
contextBridge.exposeInMainWorld("electronAPI", {
  // Open folder dialog
  selectFolder: () => ipcRenderer.invoke("dialog:openFolder"),
  // Open file dialog (for FFmpeg)
  selectFile: (options) => ipcRenderer.invoke("dialog:openFile", options),
  // Open path in explorer
  openPath: (path) => ipcRenderer.invoke("shell:openPath", path),
  // Get app info
  getAppPath: () => ipcRenderer.invoke("app:getPath"),
});
