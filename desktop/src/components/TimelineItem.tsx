import React from 'react';
import { ContentItemData } from '../App'; // Import the shared type

interface TimelineItemProps {
  item: ContentItemData | null; // Allow item to be null
  onSummarizeRequest: (itemId: string) => void; // Add this prop
  // We will add onSummarize and backendUrl props later
}

// Helper function to format date (can be moved to a utils file later)
const formatDate = (dateString: string | undefined): string => {
  if (!dateString) return 'N/A';
  try {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch (error) {
    console.error("Error formatting date:", error);
    return dateString; // return original if formatting fails
  }
};

const TimelineItem: React.FC<TimelineItemProps> = ({ item, onSummarizeRequest }) => {
  if (!item) {
    return null;
  }

  const { text_content, source, created_at, ai_summary, id: itemId } = item; // Destructure ai_summary and id
  const title = source?.title || 'Ingested Content';
  const url = source?.url;
  const type = source?.type || 'Unknown';

  const handleSummarize = () => {
    // console.log(`Placeholder: Summarize button clicked for item ID: ${item.id}`);
    onSummarizeRequest(itemId); // Call the passed-in handler
  };

  return (
    <li className="mb-6 ms-4 p-4 bg-gray-800 rounded-lg shadow-md hover:shadow-lg transition-shadow duration-200 ease-in-out">
      <div className="absolute w-3 h-3 bg-purple-500 rounded-full mt-1.5 -start-1.5 border border-gray-900 dark:border-gray-700"></div>
      <time className="mb-1 text-sm font-normal leading-none text-purple-400">
        {formatDate(created_at)} - <span className="capitalize font-semibold">{type}</span>
      </time>
      <h3 className="text-xl font-semibold text-white mb-1">{title}</h3>
      {url && (
        <a 
          href={url} 
          target="_blank" 
          rel="noopener noreferrer" 
          className="text-xs text-purple-300 hover:text-purple-200 hover:underline break-all block mb-2"
        >
          {url}
        </a>
      )}
      <p className="mb-3 text-base font-normal text-gray-400 truncate_custom_lines">
        {text_content || 'No text content available.'}
      </p>
      
      {/* Display AI Summary */}
      {ai_summary && ai_summary.summary_text && (
        <div className="mt-3 pt-3 border-t border-gray-700">
          <h4 className="text-md font-semibold text-purple-300 mb-1">AI Summary:</h4>
          <p className="text-sm text-gray-300">{ai_summary.summary_text}</p>
          {ai_summary.model_used && (
            <p className="text-xs text-gray-500 mt-1">Model: {ai_summary.model_used}</p>
          )}
        </div>
      )}

      {/* Summarize Button */}
      {!ai_summary && (
        <div className="mt-3 pt-3 border-t border-gray-700">
          <button
            onClick={handleSummarize}
            className="px-3 py-1.5 text-sm bg-green-600 hover:bg-green-700 text-white rounded-md transition-colors"
          >
            Summarize
          </button>
        </div>
      )}
    </li>
  );
};

export default TimelineItem; 