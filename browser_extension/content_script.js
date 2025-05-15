console.log("Tracepaper content script loaded.");

/**
 * Attempts to extract the main textual content from the page.
 * This is a very basic implementation and will need significant improvement
 * to work reliably across different websites.
 */
function extractMainContent() {
  // Try common article tags
  const articleSelectors = ['article', '.post-content', '.entry-content', '.article-body', '[role="main"]'];
  for (const selector of articleSelectors) {
    const element = document.querySelector(selector);
    if (element) return element.innerText;
  }

  // Fallback: try the body, but this can be very noisy
  // Avoid if there are many script/style tags or very short content
  if (document.body && document.body.innerText.length > 200) { // Arbitrary length check
    // Basic cleaning: remove script and style content if innerText includes them (crude)
    let text = document.body.innerText;
    text = text.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, "");
    text = text.replace(/<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>/gi, "");
    if (text.trim().length > 100) return text.trim(); 
  }
  return "Could not automatically extract main content."; 
}

// The content script needs to be invoked by the popup/background to extract text
// and then send it back. 
// When executeScript is called with `files`, the script is executed in the page context.
// For the popup to get data back, this script should send a message.

// Send a message to the background script with the extracted content
// This allows the background script to coordinate everything.
(function() {
  const extractedText = extractMainContent();
  chrome.runtime.sendMessage({
    action: "contentExtracted",
    data: {
      text: extractedText,
      url: window.location.href,
      title: document.title
    }
  });
})(); 