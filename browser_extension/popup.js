// popup.js
document.addEventListener('DOMContentLoaded', () => {
  const sendButton = document.getElementById('sendToTracepaper');
  const statusElement = document.getElementById('status');

  // Listen for results from the background script
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "ingestionResult") {
      if (request.status === "success") {
        statusElement.textContent = request.message || "Success!";
        console.log("Popup: Ingestion success", request.data);
      } else if (request.status === "error") {
        statusElement.textContent = request.message || "Error processing page.";
        console.error("Popup: Ingestion error", request.message);
      }
      sendButton.disabled = false; // Re-enable button
    }
    // It's good practice to return true if you intend to use sendResponse asynchronously,
    // but for this listener, we're not responding back to the background script.
    return false; 
  });

  sendButton.addEventListener('click', async () => {
    statusElement.textContent = 'Processing...';
    sendButton.disabled = true;

    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

      if (tab && tab.id) {
        // Execute content script. The content script will send a "contentExtracted" message 
        // to the background script. The background script will then process and send an 
        // "ingestionResult" message back, which the listener above will catch.
        await chrome.scripting.executeScript({
          target: { tabId: tab.id },
          files: ['content_script.js']
        });
        
        // After executing the content script, we don't need to do much more here.
        // The content script messages background, background messages popup.
        // The original direct message to background from popup can be removed or simplified
        // as the primary trigger is now the content_script execution which then messages background.
        // However, sending a message like "ingestCurrentPage" can still be useful if background
        // needs to know the popup initiated the action, or to manage state.
        // For this flow, let's keep it to signal intent. 
        // The button will be re-enabled by the "ingestionResult" listener.
        chrome.runtime.sendMessage({ action: "ingestCurrentPage" }, (response) => {
            if (chrome.runtime.lastError) {
                // This callback is for the direct message to background. 
                // If it fails (e.g. background not ready), handle it, but the main status update
                // will come from the ingestionResult listener.
                console.error("Popup: Error sending ingestCurrentPage message:", chrome.runtime.lastError.message);
                if (!statusElement.textContent.startsWith("Success") && !statusElement.textContent.startsWith("Error")){
                    statusElement.textContent = "Error initiating process.";
                    sendButton.disabled = false;
                }
            } else {
                console.log("Popup: ingestCurrentPage message acknowledged by background.", response);
            }
        });

      } else {
        statusElement.textContent = 'Could not get active tab.';
        sendButton.disabled = false;
      }
    } catch (e) {
      console.error("Error in popup:", e);
      statusElement.textContent = `Error: ${e.message}`;
      sendButton.disabled = false;
    }
  });
}); 