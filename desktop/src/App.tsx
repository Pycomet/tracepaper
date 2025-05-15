import React, { useState, useEffect, FormEvent } from 'react';
import './styles/App.css';
import TimelineView from './components/TimelineView';

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

function App(): JSX.Element {
  const [message, setMessage] = useState<string>('Connecting to backend...');
  const [backendUrl] = useState<string>('http://localhost:8000');
  const [searchText, setSearchText] = useState<string>('');
  const [searchResults, setSearchResults] = useState<ContentItemData[]>([]);
  const [isLoadingSearch, setIsLoadingSearch] = useState<boolean>(false);
  const [timelineKey, setTimelineKey] = useState<number>(Date.now()); // Used to force re-render TimelineView

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

  const handleSearch = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!searchText.trim()) return;
    setIsLoadingSearch(true);
    setSearchResults([]);
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
      // Ensure the error structure matches ContentItemData or handle differently
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

  // New function to call the backend for summarization
  const requestSummarization = async (itemId: string): Promise<void> => {
    console.log(`Requesting summarization for item ID: ${itemId} at ${backendUrl}`);
    try {
      const response = await fetch(`${backendUrl}/content_items/${itemId}/summarize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        // body: JSON.stringify({ max_length: 150, min_length: 30 }) // Optional: pass parameters
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Summarization request failed' }));
        throw new Error(`Summarization failed: ${errorData.detail || response.statusText}`);
      }
      const summary = await response.json() as SummaryData;
      console.log('Summarization successful:', summary);
      // Trigger a refresh of the timeline view to show the new summary
      // This is a simple way to refresh; a more granular update would be better for performance
      setTimelineKey(Date.now()); 
    } catch (error) {
      console.error("Summarization error:", error);
      alert(`Failed to summarize item: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white flex flex-col items-center p-4">
      <header className="w-full max-w-4xl mx-auto p-6">
        <h1 className="text-5xl font-bold text-center text-purple-400 mb-4">
          Tracepaper Desktop
        </h1>
        <p className="text-center text-gray-400 mb-2">
          {message}
        </p>
        <div className="text-center">
            <button 
                onClick={testIPC} 
                className="my-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded-md text-sm"
            >
                Test IPC
            </button>
        </div>
      </header>
      
      <main className="w-full max-w-3xl mx-auto">
        <section className="bg-gray-800 p-6 rounded-lg shadow-xl mb-10">
          <form onSubmit={handleSearch} className="mb-6">
            <input 
              type="text" 
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              placeholder="Search your knowledge..." 
              className="w-full p-3 bg-gray-700 border border-gray-600 rounded-md focus:ring-purple-500 focus:border-purple-500"
            />
            <button 
              type="submit" 
              disabled={isLoadingSearch}
              className="mt-3 w-full p-3 bg-purple-600 hover:bg-purple-700 rounded-md font-semibold disabled:opacity-50"
            >
              {isLoadingSearch ? 'Searching...' : 'Search'}
            </button>
          </form>

          <div>
            <h2 className="text-2xl font-semibold mb-3 text-purple-300">Search Results:</h2>
            {searchResults.length === 0 && !isLoadingSearch && (
              <p className="text-gray-500">No results yet. Try a search!</p>
            )}
            {isLoadingSearch && <p className="text-gray-500">Loading results...</p>}
            <ul className="space-y-3">
              {searchResults.map((item) => (
                <li key={item.id} className="p-4 bg-gray-700 rounded-md shadow">
                  <h3 className="text-lg font-semibold text-purple-400">{item.source?.title || 'Ingested Text'}</h3>
                  <p className="text-sm text-gray-300 truncate_custom_lines">{item.text_content}</p>
                  {item.source?.url && 
                    <a href={item.source.url} target="_blank" rel="noopener noreferrer" className="text-xs text-purple-400 hover:underline break-all">
                      {item.source.url}
                    </a>}
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section>
          <TimelineView backendUrl={backendUrl} onRequestSummarization={requestSummarization} key={timelineKey} />
        </section>
      </main>
    </div>
  );
}

export default App; 