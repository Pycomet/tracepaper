import React, { useState, useEffect, FormEvent } from 'react';
import './styles/App.css';
import TimelineView from './components/TimelineView';
import { motion, AnimatePresence } from 'framer-motion';

// Define types for the data we expect
interface BackendStatus {
  status: string;
  message: string;
}

interface SourceData {
  id: string; // Assuming UUID is string here, adjust if it's a specific type
  type: string;
  url?: string;
  title?: string;
  created_at: string; // ISO date string
  // original_path?: string;
}

// Add new SummaryData interface
interface SummaryData {
  id: string;
  summary_text: string;
  model_used?: string;
  created_at: string;
}

export interface ContentItemData { // Exporting if Timeline components might use it directly
  id: string; // Assuming UUID is string
  text_content: string;
  content_hash: string;
  metadata_json?: string;
  processed_at?: string; // ISO date string
  source_id: string; // Assuming UUID is string
  created_at: string; // ISO date string
  source?: SourceData; // Optional, as it might not always be populated
  ai_summary?: SummaryData; // Add optional AI summary
}

// Define the global electronAPI if it exists on window
// This helps TypeScript understand the shape of window.electronAPI if preloaded
declare global {
  interface Window {
    electronAPI?: {
      invoke: (channel: string, ...args: any[]) => Promise<any>;
      // Define other methods like send, on if you use them from preload.js
    };
  }
}

// const POLLING_INTERVAL = 5000; // Polling will be handled by TimelineView

function App(): JSX.Element {
  const [message, setMessage] = useState<string>('Connecting to backend...');
  const [backendUrl] = useState<string>('http://localhost:8000');
  const [searchText, setSearchText] = useState<string>('');
  const [searchResults, setSearchResults] = useState<ContentItemData[]>([]);
  const [isLoadingSearch, setIsLoadingSearch] = useState<boolean>(false);
  // const [timelineKey, setTimelineKey] = useState<number>(Date.now()); // No longer needed for polling trigger

  useEffect(() => {
    fetch(`${backendUrl}/health`)
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json() as Promise<BackendStatus>;
      })
      .then(data => setMessage(`Backend status: ${data.status} - ${data.message}`))
      .catch((error: Error) => setMessage(`Error connecting to backend: ${error.message}`))
  }, [backendUrl]);

  // Removed polling useEffect that changed timelineKey

  const handleSearch = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!searchText.trim()) {
      setSearchResults([]); 
      return;
    }
    setIsLoadingSearch(true);
    try {
      const response = await fetch(`${backendUrl}/search?query=${encodeURIComponent(searchText)}&k=5`);
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Search request failed' }));
        throw new Error(`Search failed: ${errorData.detail || response.statusText}`);
      }
      const results = await response.json() as ContentItemData[];
      setSearchResults(results);
    } catch (error) {
      console.error("Search error:", error);
      setSearchResults([{ 
        id: 'error-' + Date.now(), 
        text_content: error instanceof Error ? `Search failed: ${error.message}` : 'Search failed: Unknown error', 
        source: { id: 'error-source', title: 'Error', type: 'error', created_at: new Date().toISOString() },
        content_hash: '',
        source_id: 'error-source',
        created_at: new Date().toISOString(),
      }]);
    } finally {
      setIsLoadingSearch(false);
    }
  };

  const testIPC = async () => {
    if (window.electronAPI && window.electronAPI.invoke) {
      try {
        const response = await window.electronAPI.invoke('my-invokable-ipc', 'hello from renderer');
        console.log('IPC Response from main:', response);
        alert(`IPC Response: ${response}`);
      } catch (error) {
        console.error('Error invoking IPC:', error);
        const errorMessage = error instanceof Error ? error.message : String(error);
        alert(`IPC Error: ${errorMessage}`);
      }
    } else {
      alert('window.electronAPI.invoke not found. Ensure preload script is working.');
    }
  };

  // requestSummarization in App.tsx will now need to trigger a refresh in TimelineView
  // or TimelineView can have its own refresh mechanism after summarization.
  // For now, we assume TimelineView's internal polling will pick up the change.
  // Alternatively, pass a function to TimelineView to manually trigger its fetch.
  const [forceTimelineRefresh, setForceTimelineRefresh] = useState<number>(0);

  const requestSummarization = async (itemId: string): Promise<void> => {
    console.log(`Requesting summarization for item ID: ${itemId} at ${backendUrl}`);
    try {
      const response = await fetch(`${backendUrl}/content_items/${itemId}/summarize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Summarization request failed' }));
        throw new Error(`Summarization failed: ${errorData.detail || response.statusText}`);
      }
      await response.json(); // const summary = ...
      console.log('Summarization successful, triggering timeline refresh hint');
      // Hint TimelineView to refresh by changing a simple prop or via a callback
      setForceTimelineRefresh(prev => prev + 1);
    } catch (error) {
      console.error("Summarization error:", error);
      alert(`Failed to summarize item: ${error instanceof Error ? error.message : 'Unknown error'}`);
      // Potentially trigger a refresh even on error if UI needs to reset something
      // setForceTimelineRefresh(prev => prev + 1);
    }
  };

  const searchResultVariants = {
    hidden: { opacity: 0, y: 10 },
    visible: (i: number) => ({
      opacity: 1,
      y: 0,
      transition: {
        delay: i * 0.05, // Faster stagger for search results
        duration: 0.3,
        ease: "easeOut"
      }
    }),
    exit: {
      opacity: 0,
      y: -10,
      transition: {
        duration: 0.2,
        ease: "easeIn"
      }
    }
  };

  return (
    <div className="h-screen bg-gray-900 text-white flex flex-col font-sans overflow-hidden">
      <header className="w-full max-w-4xl mx-auto p-6 flex flex-col items-center shrink-0">
        <div className="flex items-center mb-4">
          <img src="/logo.png" alt="Tracepaper Logo" className="h-16 w-16 mr-4 filter invert"/>
          <h1 className="text-5xl font-bold text-purple-400">
            Tracepaper
          </h1>
        </div>
        <p className="text-center text-gray-400 text-sm mb-3">
          {message}
        </p>
        {/* <div className="text-center">
            <button 
                onClick={testIPC} 
                className="my-1 px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded-md text-xs text-gray-300"
            >
                Test IPC
            </button>
        </div> */}
      </header>
      
      <main className="w-full max-w-3xl mx-auto flex flex-col flex-grow overflow-hidden px-4 pb-4">
        <section className="bg-gray-800 p-6 rounded-lg shadow-xl mb-6 shrink-0">
          <form onSubmit={handleSearch} className="mb-6">
            <input 
              type="text" 
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              placeholder="Search your knowledge history..."
              className="w-full p-3 bg-gray-700 border border-gray-600 rounded-md focus:ring-purple-500 focus:border-purple-500 placeholder-gray-500"
            />
            <button 
              type="submit" 
              disabled={isLoadingSearch}
              className="mt-3 w-full p-3 bg-purple-600 hover:bg-purple-700 rounded-md font-semibold disabled:opacity-50 transition-colors duration-150"
            >
              {isLoadingSearch ? (
                <svg className="animate-spin h-5 w-5 mx-auto text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              ) : 'Search'}
            </button>
          </form>

          <div className="overflow-y-auto max-h-[calc(100vh-500px)]">
            <h2 className="text-2xl font-semibold mb-4 text-purple-300 sticky top-0 bg-gray-800 py-2 z-10">Search Results:</h2>
            {isLoadingSearch && searchResults.length === 0 && (
                <div className="flex justify-center items-center h-20">
                    <svg className="animate-spin h-8 w-8 text-purple-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                </div>
            )}
            {!isLoadingSearch && searchResults.length === 0 && searchText.trim() !== '' && (
                <p className="text-gray-500 italic">No results found for "{searchText}".</p>
            )}
            {!isLoadingSearch && searchResults.length === 0 && searchText.trim() === '' && (
                 <p className="text-gray-500 italic">Enter a search term to see results.</p>
            )}
            
            <ul className="space-y-3">
              <AnimatePresence initial={false}>
                {searchResults.map((item, index) => (
                  <motion.li 
                    key={item.id} 
                    custom={index}
                    variants={searchResultVariants}
                    initial="hidden"
                    animate="visible"
                    exit="exit"
                    className="p-4 bg-gray-700 rounded-md shadow-md hover:bg-gray-600 transition-colors duration-150"
                  >
                    <h3 className="text-lg font-semibold text-purple-400 mb-1">{item.source?.title || 'Ingested Text'}</h3>
                    <p className="text-sm text-gray-300 truncate_custom_lines leading-relaxed">{item.text_content}</p>
                    {item.source?.url && 
                      <a href={item.source.url} target="_blank" rel="noopener noreferrer" className="text-xs text-purple-500 hover:text-purple-300 hover:underline break-all mt-2 inline-block">
                        {item.source.url}
                      </a>}
                  </motion.li>
                ))}
              </AnimatePresence>
            </ul>
          </div>
        </section>

        {/* Fixed Timeline Title */}
        <h2 className="text-3xl font-semibold text-purple-300 text-center mb-6 shrink-0">
          My Knowledge Timeline
        </h2>

        <section className="flex-grow overflow-y-auto pb-4">
          <TimelineView 
            backendUrl={backendUrl} 
            onRequestSummarization={requestSummarization} 
            forceRefreshTrigger={forceTimelineRefresh} // Pass the trigger
          />
        </section>
      </main>
    </div>
  );
}

export default App; 