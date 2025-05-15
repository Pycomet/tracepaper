// browser_extension/tests/e2e.test.js

const MOCK_BACKEND_URL = 'http://localhost:8000/ingest/webpage';

describe('Tracepaper Browser Extension E2E Tests', () => {
  let backgroundPage;
  let mockFetchResponse = { success: true, message: "Mocked backend response" };
  let interceptedRequest = null;

  beforeAll(async () => {
    backgroundPage = await global.getBackgroundPage();
    if (!backgroundPage) {
      throw new Error("Could not get background page/service worker");
    }
    
    // Expose a function to the background page to capture fetch calls
    await backgroundPage.evaluate((expectedUrl) => {
      global.capturedRequests = []; // Store captured requests here
      const originalFetch = global.fetch;
      global.fetch = (url, options) => {
        if (url === expectedUrl) {
          global.capturedRequests.push({ url, options });
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ success: true, message: "Mocked backend response from test" }),
            text: () => Promise.resolve(JSON.stringify({ success: true, message: "Mocked backend response from test" }))
          });
        }
        return originalFetch(url, options);
      };
    }, MOCK_BACKEND_URL);
  });

  beforeEach(async () => {
    // Reset captured requests before each test
    await backgroundPage.evaluate(() => {
      global.capturedRequests = [];
    });
    interceptedRequest = null; // Reset local variable too
  });

  test('should inject content script and attempt to send data on page load', async () => {
    const page = await browser.newPage(); // `browser` is a global from jest-puppeteer
    
    // For MV3, need to ensure the service worker is active and listening for logs.
    // We can listen for console logs from the service worker.
    let injectionLogPromise = new Promise((resolve, reject) => {
        backgroundPage.on('console', msg => {
            if (msg.text().includes('Injected content_script.js')) {
                resolve(msg.text());
            }
        });
        // Timeout if log not found
        setTimeout(() => reject(new Error('Timeout waiting for injection log')), 10000);
    });

    await page.goto('https://example.com', { waitUntil: 'networkidle2' });

    // Wait for the injection log
    const injectionLog = await injectionLogPromise;
    expect(injectionLog).toContain('Injected content_script.js into tab');
    expect(injectionLog).toContain('https://example.com');

    // Wait a bit for the async operations (content script -> background -> fetch)
    await new Promise(resolve => setTimeout(resolve, 1000)); 

    // Check if fetch was called
    const capturedRequests = await backgroundPage.evaluate(() => global.capturedRequests);
    expect(capturedRequests.length).toBe(1);
    expect(capturedRequests[0].url).toBe(MOCK_BACKEND_URL);
    expect(capturedRequests[0].options.method).toBe('POST');
    const body = JSON.parse(capturedRequests[0].options.body);
    expect(body.source_url).toBe('https://example.com/');
    expect(body.source_title).toBe('Example Domain');
    // We can't easily assert the full text content here without more complex setup
    // but we can check that it's a non-empty string.
    expect(typeof body.text).toBe('string');
    expect(body.text.length).toBeGreaterThan(0);
    expect(body.source_type).toBe('webpage');

    await page.close();
  });

  // Add more tests here, e.g., for popup interaction, different page types, etc.
}); 