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
    
    let backgroundPageTarget = null;
    // Retry mechanism for finding the service worker target, as it might take a moment to initialize
    for (let i = 0; i < 10; i++) { // Retry up to 10 times (e.g., 5 seconds if 500ms delay)
        const targets = await browserInstance.targets();
        backgroundPageTarget = targets.find(target => target.type() === 'service_worker');
        if (backgroundPageTarget) break;
        await new Promise(resolve => setTimeout(resolve, 500)); // Wait 500ms before retrying
    }

    if (!backgroundPageTarget) {
        throw new Error('Background page (service worker) not found after retries.');
    }
    const backgroundPage = await backgroundPageTarget.worker(); // For MV3, use .worker()
    if (!backgroundPage) {
        throw new Error('Could not get worker for background page target.');
    }
    return backgroundPage;
}

global.getBackgroundPage = getBackgroundPage; 
