const path = require('path'); // Add path module

module.exports = {
  launch: {
    headless: process.env.HEADLESS !== 'false', // Run in headless mode unless HEADLESS=false
    slowMo: process.env.SLOWMO ? parseInt(process.env.SLOWMO) : 0, // Slow down operations if SLOWMO is set
    dumpio: true, // Dump browser console logs to Node's process.stdout
    args: [
      '--no-sandbox', // Required for running in Docker
      '--disable-setuid-sandbox', // Required for running in Docker
      // `--disable-extensions-except=${path.resolve('./')}`, // Temporarily removed
      `--load-extension=${path.resolve('./')}` // Load our extension from the current directory (browser_extension)
    ]
  },
  browserContext: 'default' // Can be 'incognito' if needed
}; 