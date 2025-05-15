import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import TimelineView from './TimelineView';
import { ContentItemData } from '../App'; // Import the shared type

// global.fetch is mocked in setupTests.ts

// Mock TimelineItem to prevent its complex rendering and focus on TimelineView logic
jest.mock('./TimelineItem', () => {
  // eslint-disable-next-line react/prop-types
  return function MockTimelineItem({ item }: { item: ContentItemData }) { // Add type for item prop
    return <div data-testid={`timeline-item-${item.id}`}>{item.text_content}</div>;
  };
});

beforeEach(() => {
  (global.fetch as jest.Mock).mockClear();
});

describe('<TimelineView />', () => {
  const backendUrl = 'http://testhost:1234';

  test('renders loading state initially', () => {
    (global.fetch as jest.Mock).mockImplementationOnce(() => new Promise(() => {})); // Keep it pending
    render(<TimelineView backendUrl={backendUrl} />);
    expect(screen.getByText(/Loading timeline.../i)).toBeInTheDocument();
  });

  test('fetches and displays timeline items successfully', async () => {
    const mockItems: ContentItemData[] = [
      { id: '1', text_content: 'Item 1', created_at: '2023-01-02T12:00:00Z', source: {id: 's1', type: 'A', created_at: '2023-01-02T12:00:00Z'}, content_hash:'h1', source_id:'s1' },
      { id: '2', text_content: 'Item 2', created_at: '2023-01-01T12:00:00Z', source: {id: 's2', type: 'B', created_at: '2023-01-01T12:00:00Z'}, content_hash:'h2', source_id:'s2' },
    ];
    (global.fetch as jest.Mock).mockImplementationOnce(() => 
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockItems),
      })
    );
    render(<TimelineView backendUrl={backendUrl} />);
    await waitFor(() => {
      expect(screen.getByText(/My Knowledge Timeline/i)).toBeInTheDocument();
      expect(screen.getByTestId('timeline-item-1')).toHaveTextContent('Item 1');
      expect(screen.getByTestId('timeline-item-2')).toHaveTextContent('Item 2');
    });
    const renderedItems = screen.getAllByText(/Item \d/);
    expect(renderedItems[0]).toHaveTextContent('Item 1');
    expect(renderedItems[1]).toHaveTextContent('Item 2');
  });

  test('displays error message on fetch failure', async () => {
    (global.fetch as jest.Mock).mockImplementationOnce(() => 
      Promise.reject(new Error('Failed to fetch test'))
    );
    render(<TimelineView backendUrl={backendUrl} />);
    await waitFor(() => {
      expect(screen.getByText(/Error loading timeline: Failed to fetch test/i)).toBeInTheDocument();
    });
  });

  test('displays message when no items are available', async () => {
    (global.fetch as jest.Mock).mockImplementationOnce(() => 
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve([]),
      })
    );
    render(<TimelineView backendUrl={backendUrl} />);
    await waitFor(() => {
      expect(screen.getByText(/No items in your timeline yet/i)).toBeInTheDocument();
    });
  });
}); 