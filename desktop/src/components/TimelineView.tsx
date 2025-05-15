import React, { useState, useEffect } from 'react';
import TimelineItem from './TimelineItem';
import { ContentItemData } from '../App'; // Import the shared type

interface TimelineViewProps {
  backendUrl: string;
  onRequestSummarization: (itemId: string) => Promise<void>;
}

const TimelineView: React.FC<TimelineViewProps> = ({ backendUrl, onRequestSummarization }) => {
  const [timelineItems, setTimelineItems] = useState<ContentItemData[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchTimelineItems = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await fetch(`${backendUrl}/content_items?limit=20`);
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({ detail: 'Failed to fetch timeline items' }));
          throw new Error(`Failed to fetch timeline items: ${errorData.detail || response.statusText}`);
        }
        const data = await response.json() as ContentItemData[];
        const sortedData = data.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
        setTimelineItems(sortedData);
      } catch (err) {
        console.error("Error fetching timeline items:", err);
        setError(err instanceof Error ? err.message : String(err));
        setTimelineItems([]);
      } finally {
        setIsLoading(false);
      }
    };

    if (backendUrl) {
      fetchTimelineItems();
    }
  }, [backendUrl]);

  return (
    <div className="mt-10 w-full">
      <h2 className="text-3xl font-semibold mb-6 text-purple-300 text-center">My Knowledge Timeline</h2>
      
      {isLoading && <p className="text-center text-gray-400">Loading timeline...</p>}
      {error && <p className="text-center text-red-400">Error loading timeline: {error}</p>}
      
      {!isLoading && !error && timelineItems.length === 0 && (
        <p className="text-center text-gray-500">No items in your timeline yet. Start ingesting content!</p>
      )}

      {!isLoading && !error && timelineItems.length > 0 && (
        <ol className="relative border-s border-gray-700 ms-2">
          {timelineItems.map(item => (
            <TimelineItem 
              key={item.id} 
              item={item} 
              onSummarizeRequest={onRequestSummarization}
            />
          ))}
        </ol>
      )}
    </div>
  );
};

export default TimelineView; 