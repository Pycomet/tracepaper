const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const isDev = require('electron-is-dev');

function createWindow() {
  // Create the browser window.
  const mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      // Recommended for security: 
      // contextIsolation: true, (default true since Electron 12)
      // nodeIntegration: false, (default false since Electron 5)
      // enableRemoteModule: false, (default false since Electron 10)
    },
  });

  // Load the index.html of the app.
  // In development, load from the React dev server.
  // In production, load the built React app (index.html).
  const startUrl = isDev
    ? 'http://localhost:3000' // URL of React dev server
    : `file://${path.join(__dirname, '../build/index.html')}`; // Path to built React app

  mainWindow.loadURL(startUrl);

  // Open the DevTools automatically if in development.
  if (isDev) {
    mainWindow.webContents.openDevTools();
  }

  // mainWindow.on('closed', () => {
  //   // Dereference the window object, usually you would store windows
  //   // in an array if your app supports multi windows, this is the time
  //   // when you should delete the corresponding element.
  //   mainWindow = null;
  // });
}

// This method will be called when Electron has finished
// initialization and is ready to create browser windows.
// Some APIs can only be used after this event occurs.
app.whenReady().then(() => {
  createWindow();

  app.on('activate', () => {
    // On macOS it's common to re-create a window in the app when the
    // dock icon is clicked and there are no other windows open.
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

// Quit when all windows are closed, except on macOS. There, it's common
// for applications and their menu bar to stay active until the user quits
// explicitly with Cmd + Q.
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// In this file you can include the rest of your app's specific main process
// code. You can also put them in separate files and require them here.

// Example IPC handler (optional, for communication between main and renderer)
ipcMain.handle('my-invokable-ipc', async (event, ...args) => {
  console.log('IPC message received in main process:', ...args);
  return 'response from main process';
}); 