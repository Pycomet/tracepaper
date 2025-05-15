const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electronAPI', {
  // Example: Expose a function to send an IPC message and get a response
  invoke: (channel, ...args) => ipcRenderer.invoke(channel, ...args),
  
  // Example: Expose a function to send a one-way IPC message
  send: (channel, ...args) => ipcRenderer.send(channel, ...args),
  
  // Example: Expose a function to receive IPC messages
  on: (channel, func) => {
    // Deliberately strip event as it includes `sender` 
    ipcRenderer.on(channel, (event, ...args) => func(...args));
    // Return a cleanup function
    return () => ipcRenderer.removeAllListeners(channel);
  },
  
  // You can expose other Node.js or Electron APIs here if absolutely necessary,
  // but prefer IPC for communication between renderer and main processes.
  // e.g., platform: process.platform
});

console.log('Preload script loaded.'); 