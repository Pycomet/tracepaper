import React from 'react';
import { render, screen } from '@testing-library/react';
import TimelineItem from './TimelineItem';
import { ContentItemData } from '../App'; // Import the shared type

describe('<TimelineItem />', () => {
  const mockItem: ContentItemData = {
    id: '1',
    text_content: 'This is a test item content.',
    created_at: '2023-01-01T12:00:00Z',
    source: {
      id: 'source-1',
      title: 'Test Source Title',
      url: 'http://example.com/test',
      type: 'webpage',
      created_at: '2023-01-01T11:00:00Z'
    },
    content_hash: 'hash1',
    source_id: 'source-1'
  };

  test('renders item content correctly', () => {
    render(<TimelineItem item={mockItem} />);
    expect(screen.getByText('Test Source Title')).toBeInTheDocument();
    expect(screen.getByText('This is a test item content.')).toBeInTheDocument();
    expect(screen.getByText('http://example.com/test')).toBeInTheDocument();
    expect(screen.getByText(/January 1, 2023/i)).toBeInTheDocument();
    expect(screen.getByText(/Webpage/i)).toBeInTheDocument();
  });

  const minimalItem: ContentItemData = {
    id: '2',
    text_content: 'Minimal content.',
    created_at: '2023-02-01T10:00:00Z',
    // No source object, but source_id and content_hash are mandatory for ContentItemData
    source_id: 'source-minimal',
    content_hash: 'hash-minimal',
    // source property itself is optional in ContentItemData, 
    // so TimelineItem should handle its absence gracefully.
  };

  test('renders correctly with minimal data (optional source object)', () => {
    render(<TimelineItem item={minimalItem} />);
    expect(screen.getByText('Ingested Content')).toBeInTheDocument(); // Default title due to no source.title
    expect(screen.getByText('Minimal content.')).toBeInTheDocument();
    // Type comes from source.type, if source is undefined, it defaults to 'Unknown' in TimelineItem
    expect(screen.getByText(/Unknown/i)).toBeInTheDocument(); 
  });

  test('does not render if item is null', () => {
    const { container } = render(<TimelineItem item={null} />);
    expect(container.firstChild).toBeNull();
  });
}); 