import React, { useState, useEffect, useCallback } from 'react';
import TimelineItem from './TimelineItem';
import { ContentItemData } from '../App'; // Import the shared type
import { motion, AnimatePresence } from 'framer-motion'; // Import framer-motion

const POLLING_INTERVAL = 10000; // 10 seconds for background polling

interface TimelineViewProps {
  backendUrl: string;
  onRequestSummarization: (itemId: string) => Promise<void>;
  forceRefreshTrigger?: number; // Optional: to allow parent to hint a refresh
}

const TimelineView: React.FC<TimelineViewProps> = ({ backendUrl, onRequestSummarization, forceRefreshTrigger }) => {
  const [timelineItems, setTimelineItems] = useState<ContentItemData[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTimelineItems = useCallback(async (isBackgroundUpdate = false) => {
    if (!isBackgroundUpdate) {
      setIsLoading(true); 
    }
    // Don't clear main error for background updates, only for explicit loads
    if (!isBackgroundUpdate) setError(null); 

    try {
      const response = await fetch(`${backendUrl}/content_items?limit=20&sort_by=created_at&sort_order=desc`);
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to fetch timeline items' }));
        throw new Error(`Failed to fetch timeline items: ${errorData.detail || response.statusText}`);
      }
      const newFetchedItems = await response.json() as ContentItemData[];
      
      setTimelineItems(prevItems => {
        const combinedItemsMap = new Map<string, ContentItemData>();

        // Add previous items to map
        prevItems.forEach(item => combinedItemsMap.set(item.id, item));
        // Add/update with new items (new ones will be added, existing ones updated)
        newFetchedItems.forEach(item => combinedItemsMap.set(item.id, item));

        // Convert map back to array and sort
        const mergedItems = Array.from(combinedItemsMap.values());
        mergedItems.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
        
        return mergedItems.slice(0, 50); // Keep the list to a manageable size (e.g., latest 50)
      });

      // Clear main error if fetch was successful after a previous error
      if (!isBackgroundUpdate && error) setError(null);

    } catch (err) {
      console.error("Error fetching timeline items:", err);
      if (!isBackgroundUpdate) { 
        setError(err instanceof Error ? err.message : String(err));
        // setTimelineItems([]); // Optionally clear items on major fetch error, or keep stale data
      } else {
        console.warn("Background timeline poll failed:", err); 
      }
    } finally {
      if (!isBackgroundUpdate) {
        setIsLoading(false);
      }
    }
  }, [backendUrl, error]); // Added error to dependency array for clearing it

  // Initial fetch and fetch on forceRefreshTrigger change
  useEffect(() => {
    if (backendUrl) {
      console.log("TimelineView: Initial fetch or forceRefreshTrigger changed, fetching...");
      fetchTimelineItems(false); 
    }
  }, [backendUrl, forceRefreshTrigger, fetchTimelineItems]);

  // Background polling interval
  useEffect(() => {
    if (!backendUrl) return;

    const intervalId = setInterval(() => {
      console.log("TimelineView: Background polling for updates...");
      fetchTimelineItems(true); 
    }, POLLING_INTERVAL);

    return () => clearInterval(intervalId); 
  }, [backendUrl, fetchTimelineItems]);

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: (i: number) => ({
      opacity: 1,
      y: 0,
      transition: {
        delay: i * 0.1, // Stagger animation
        duration: 0.4,
        ease: "easeOut"
      }
    }),
    exit: {
      opacity: 0,
      y: -20,
      transition: {
        duration: 0.3,
        ease: "easeIn"
      }
    }
  };

  return (
    <div className="w-full">
      {isLoading && (
        <div className="flex justify-center items-center h-40 pt-10">
          <svg className="animate-spin h-10 w-10 text-purple-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        </div>
      )}
      {/* Show error only if not loading (to prevent error flashing during load) */}
      {!isLoading && error && <p className="text-center text-red-500 bg-red-900 bg-opacity-50 p-3 rounded-md mt-4">Error loading timeline: {error}</p>}
      
      {!isLoading && !error && timelineItems.length === 0 && (
        <p className="text-center text-gray-500 italic pt-10">No items in your timeline yet. Start ingesting content or check back later.</p>
      )}

      {/* Render timeline items if not initial loading, even if there was a background error */}
      {(!isLoading || timelineItems.length > 0) && !error && (
        <ol className="relative border-s-2 border-gray-700 ms-4">
          <AnimatePresence initial={false}>
            {timelineItems.map((item, index) => (
              <motion.li
                key={item.id} 
                custom={index} 
                variants={itemVariants}
                initial="hidden"
                animate="visible"
                exit="exit"
                layout // Add layout prop for smoother animations when list changes
                className="mb-8" 
              >
                <TimelineItem 
                  item={item} 
                  onSummarizeRequest={onRequestSummarization}
                />
              </motion.li>
            ))}
          </AnimatePresence>
        </ol>
      )}
    </div>
  );
};

export default TimelineView; 