const { app, BrowserWindow, ipcMain, dialog, shell } = require("electron");
const { spawn } = require("child_process");
const path = require("path");

let pyProcess;
let mainWindow;

// IPC Handlers for settings dialogs
ipcMain.handle("dialog:openFolder", async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ["openDirectory"],
    title: "Select Download Folder",
  });
  return result.canceled ? null : result.filePaths[0];
});

ipcMain.handle("dialog:openFile", async (event, options) => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ["openFile"],
    title: options?.title || "Select File",
    filters: options?.filters || [{ name: "All Files", extensions: ["*"] }],
  });
  return result.canceled ? null : result.filePaths[0];
});

ipcMain.handle("shell:openPath", async (event, pathToOpen) => {
  if (pathToOpen) {
    shell.openPath(pathToOpen);
  }
});

ipcMain.handle("app:getPath", () => {
  return app.getPath("userData");
});

function getBackendPath() {
  if (app.isPackaged) {
    // After build (.exe) - backend is in resources
    return path.join(process.resourcesPath, "app.exe");
  } else {
    // Dev mode
    return path.join(__dirname, "backend", "app.py");
  }
}

function startBackend() {
  const backendPath = getBackendPath();
  console.log("Starting backend from:", backendPath);

  if (app.isPackaged) {
    // Run compiled EXE
    pyProcess = spawn(backendPath, [], {
      cwd: path.dirname(backendPath),
    });
  } else {
    // Run Python script in dev
    pyProcess = spawn("python", [backendPath], {
      cwd: path.join(__dirname, "backend"),
    });
  }

  pyProcess.stdout.on("data", (data) => {
    console.log(`BACKEND: ${data}`);
  });

  pyProcess.stderr.on("data", (data) => {
    console.error(`BACKEND ERROR: ${data}`);
  });

  pyProcess.on("error", (err) => {
    console.error("Failed to start backend:", err);
  });
}

function getIconPath() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, "icon.ico");
  }
  return path.join(__dirname, "icon.ico");
}

function getPreloadPath() {
  if (app.isPackaged) {
    return path.join(__dirname, "preload.js");
  }
  return path.join(__dirname, "preload.js");
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    icon: getIconPath(),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: getPreloadPath(),
    },
    show: false,
  });

  // Load the frontend
  if (app.isPackaged) {
    mainWindow.loadFile(path.join(__dirname, "frontend", "dist", "index.html"));
  } else {
    // In dev mode, load from Vite dev server or built files
    mainWindow.loadFile(path.join(__dirname, "frontend", "dist", "index.html"));
  }

  mainWindow.once("ready-to-show", () => {
    mainWindow.show();
    mainWindow.maximize();
  });

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

app.whenReady().then(() => {
  startBackend();
  // Give backend time to start
  setTimeout(createWindow, 2000);
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("activate", () => {
  if (mainWindow === null) {
    createWindow();
  }
});

app.on("will-quit", () => {
  if (pyProcess) {
    pyProcess.kill();
  }
});