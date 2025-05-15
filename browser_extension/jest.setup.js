// jest.setup.js

// Increase default timeout for Puppeteer tests as they can be slower
if (typeof jest !== 'undefined') {
    jest.setTimeout(30000); // 30 seconds
}

// You can add any global setup here, e.g., helper functions or mocks

// Example: Expose a helper to get the background page (service worker)
async function getBackgroundPage(browserInstance) {
    if (!browserInstance) {
        browserInstance = global.browser; // browser is globally available via jest-puppeteer
    }
    const targets = await browserInstance.targets();
    const backgroundPageTarget = targets.find(target => target.type() === 'service_worker'); // For MV3
    if (!backgroundPageTarget) {
        throw new Error('Background page (service worker) not found.');
    }
    const backgroundPage = await backgroundPageTarget.worker(); // For MV3, use .worker()
    if (!backgroundPage) {
        throw new Error('Could not get worker for background page target.');
    }
    return backgroundPage;
}

global.getBackgroundPage = getBackgroundPage; 