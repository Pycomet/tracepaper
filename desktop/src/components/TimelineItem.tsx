import React, { useState } from 'react';
import { ContentItemData } from '../App'; // Import the shared type

interface TimelineItemProps {
  item: ContentItemData | null; // Allow item to be null
  onSummarizeRequest: (itemId: string) => Promise<void>; // Changed to Promise<void> to allow await
  // We will add onSummarize and backendUrl props later
}

// Helper function to format date (can be moved to a utils file later)
const formatDate = (dateString: string | undefined): string => {
  if (!dateString) return 'N/A';
  try {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
    });
  } catch (error) {
    console.error("Error formatting date:", error);
    return dateString; // return original if formatting fails
  }
};

// Helper function to get an icon based on source type (simple version)
const SourceTypeIcon: React.FC<{ type: string }> = ({ type }) => {
  let iconClasses = "fas "; // Font Awesome base class
  let color = "text-gray-400";

  switch (type.toLowerCase()) {
    case 'webpage':
      iconClasses += "fa-globe";
      color = "text-blue-400";
      break;
    case 'file':
      iconClasses += "fa-file-alt";
      color = "text-green-400";
      break;
    default:
      iconClasses += "fa-question-circle";
  }
  // return <i className={`${iconClasses} ${color} mr-2`}></i>; 
  // Using text for now if FontAwesome is not set up
  if (type.toLowerCase() === 'webpage') return <span className="text-blue-400 mr-1 text-sm">🌐</span>;
  if (type.toLowerCase() === 'file') return <span className="text-green-400 mr-1 text-sm">📄</span>;
  return <span className="text-gray-400 mr-1 text-sm">❔</span>;
};

const TimelineItem: React.FC<TimelineItemProps> = ({ item, onSummarizeRequest }) => {
  const [isSummarizing, setIsSummarizing] = useState(false);

  if (!item) {
    return null;
  }

  const { text_content, source, created_at, ai_summary, id: itemId } = item; // Destructure ai_summary and id
  const title = source?.title || 'Ingested Content';
  const url = source?.url;
  const type = source?.type || 'Unknown';

  const handleSummarize = async () => {
    if (isSummarizing) return;
    setIsSummarizing(true);
    try {
      await onSummarizeRequest(itemId);
      // App.tsx handles timeline refresh, which will provide new item prop with summary
    } catch (error) {
      console.error("Error during summarization request from TimelineItem:", error);
      // Error is alerted by App.tsx, button will re-enable
    } finally {
      setIsSummarizing(false); // Re-enable button if summary appears or if error occurs
    }
  };

  return (
    <li className="ms-6">
      <div className="absolute w-4 h-4 bg-purple-600 rounded-full -start-[9px] border-2 border-gray-900 ring-2 ring-gray-700"></div>
      <div className="p-5 bg-gray-800 rounded-xl shadow-lg hover:shadow-purple-500/30 transition-shadow duration-300 ease-in-out relative overflow-hidden">
        <div className="flex justify-between items-start mb-2">
          <time className="block text-xs font-normal leading-none text-purple-400 mb-1.5">
            {formatDate(created_at)}
          </time>
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-purple-700 text-purple-200 capitalize">
            <SourceTypeIcon type={type} />
            {type}
          </span>
        </div>
        
        <h3 className="text-xl font-bold text-white mb-1.5 leading-tight">{title}</h3>
        
        {url && (
          <a 
            href={url} 
            target="_blank" 
            rel="noopener noreferrer" 
            className="text-xs text-purple-300 hover:text-purple-100 hover:underline break-all block mb-3 transition-colors duration-150"
          >
            {url}
          </a>
        )}
        
        <p className="mb-4 text-sm font-normal text-gray-300 leading-relaxed truncate_custom_lines">
          {text_content || 'No text content available.'}
        </p>
        
        {ai_summary && ai_summary.summary_text && (
          <div className="mt-4 pt-4 border-t border-gray-700">
            <h4 className="text-base font-semibold text-purple-300 mb-1.5">AI Summary:</h4>
            <p className="text-sm text-gray-200 whitespace-pre-wrap leading-relaxed">{ai_summary.summary_text}</p>
            {ai_summary.model_used && (
              <p className="text-xs text-gray-500 mt-2">Model: {ai_summary.model_used}</p>
            )}
          </div>
        )}

        {!ai_summary?.summary_text && (
          <div className="mt-4 pt-4 border-t border-gray-700 flex justify-end">
            <button
              onClick={handleSummarize}
              disabled={isSummarizing}
              className={`px-4 py-2 text-sm font-medium rounded-lg transition-all duration-200 ease-in-out flex items-center justify-center 
                         ${isSummarizing 
                           ? 'bg-gray-600 text-gray-400 cursor-not-allowed' 
                           : 'bg-green-600 hover:bg-green-500 text-white shadow-md hover:shadow-lg'}`}
            >
              {isSummarizing ? (
                <>
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Summarizing...
                </>
              ) : (
                'Summarize with AI'
              )}
            </button>
          </div>
        )}
      </div>
    </li>
  );
};

export default TimelineItem; 