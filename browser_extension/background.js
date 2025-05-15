// background.js
// This script will handle messages and interact with the backend.

const BACKEND_API_URL = "http://localhost:8000/ingest/webpage"; // Target endpoint

chrome.runtime.onInstalled.addListener(() => {
  console.log("Tracepaper Companion extension installed.");
  // You could set up default settings here using chrome.storage.sync.set
});

// async function getCurrentTab() { // This function is not used currently, can be removed or kept for future use.
//   let [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
//   return tab;
// }

// Listen for messages from popup or content script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "ingestCurrentPage") {
    console.log("Background: Received ingestCurrentPage request from popup.");
    // The popup initiates content script injection. Content script sends "contentExtracted".
    // No direct async response needed here as "contentExtracted" handles the core logic.
    return false; 

  } else if (request.action === "contentExtracted") {
    console.log("Background: Received contentExtracted from content script:", request.data);
    const { url, title, text } = request.data;
    if (!url || !title) {
      console.error("Background: Missing URL or title from content script.");
      // Notify popup about the error if it's waiting.
      chrome.runtime.sendMessage({action: "ingestionResult", status: "error", message: "Content script failed to provide URL or title." });
      return false;
    }

    sendToBackend(url, title, text)
      .then(backendResponse => {
        console.log("Background: Backend response received", backendResponse);
        // Notification already handled by sendToBackend via ingestionResult message
      })
      .catch(error => {
        console.error("Background: Error sending to backend", error);
        // Notification already handled by sendToBackend via ingestionResult message
      });
    // No direct async response to content script.
    return false; 
  } else if (request.action === "ingestWebpage") { // This was the duplicated listener's content
    console.log("Background: Received ingestWebpage request (now consolidated)", request.data);
    // This action seems redundant if popup triggers ingestCurrentPage, 
    // which leads to contentExtracted. If this is for a different flow, it needs clarity.
    // For now, assuming it's an old path. If it's needed, its logic for getting tab details and
    // calling sendToBackend would need to be fully implemented.
    // Example: sendToBackend(request.data.url, request.data.title, request.data.extractedText);
    sendResponse({ status: "received_ingestWebpage", data: request.data }); // Acknowledge message
    return true; // Indicates you wish to send a response asynchronously (if needed)
  }
  // It's good practice to return true from the event listener if you will be calling sendResponse asynchronously.
  // For actions that complete synchronously or don't send a response, return false or nothing.
  return false; // Default for unhandled actions, or synchronous completion without response.
});

async function sendToBackend(url, title, textContent) {
  console.log(`Background: Sending to backend: ${title} (${url})`);
  try {
    const response = await fetch(BACKEND_API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        source_url: url, 
        source_title: title, 
        text: textContent, 
        source_type: 'webpage'
      }),
    });

    if (response.ok) {
      const result = await response.json();
      console.log('Background: Successfully sent to backend:', result);
      chrome.runtime.sendMessage({action: "ingestionResult", status: "success", message: "Page sent to Tracepaper!", data: result });
      return result;
    } else {
      const errorText = await response.text();
      console.error('Background: Error sending to backend:', response.status, response.statusText, errorText);
      chrome.runtime.sendMessage({action: "ingestionResult", status: "error", message: `Backend Error: ${response.status} ${response.statusText}. ${errorText}` });
      throw new Error(`Backend error: ${response.status} ${errorText}`);
    }
  } catch (error) {
    console.error('Background: Network or other error sending to backend:', error);
    chrome.runtime.sendMessage({action: "ingestionResult", status: "error", message: `Network Error: ${error.message}` });
    throw error;
  }
}

// New: Listener for tab updates to automatically process pages
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  // Check if the tab loading is complete and it's an HTTP/HTTPS URL
  if (changeInfo.status === 'complete' && tab.url && (tab.url.startsWith('http://') || tab.url.startsWith('https://'))) {
    console.log(`Background: Tab ${tabId} updated and complete. URL: ${tab.url}`);
    
    // Prevent processing on Chrome Web Store or other chrome:// pages for safety/permissions
    if (tab.url.startsWith('chrome://') || tab.url.startsWith('https://chrome.google.com/webstore')) {
        console.log(`Background: Skipping processing for Chrome internal or webstore page: ${tab.url}`);
        return;
    }

    // Inject the content script to extract page content
    chrome.scripting.executeScript({
      target: { tabId: tabId },
      files: ['content_script.js']
    }).then(() => {
      console.log(`Background: Injected content_script.js into tab ${tabId} for URL: ${tab.url}`);
    }).catch(err => {
      console.error(`Background: Failed to inject content_script.js into tab ${tabId}: ${err}`);
    });
  }
});

// Note on popup.js communication:
// popup.js sends "ingestCurrentPage" -> background.js
// background.js (via popup action or onUpdated) injects content_script.js
// content_script.js extracts data -> sends "contentExtracted" to background.js
// background.js receives "contentExtracted" -> calls sendToBackend
// sendToBackend on success/error -> sends "ingestionResult" (globally)
// popup.js should listen for "ingestionResult" to update its UI. 