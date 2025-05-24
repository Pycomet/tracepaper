import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from './App';

// Mock the TimelineView component to avoid complexity
jest.mock('./components/TimelineView', () => {
  return function MockTimelineView() {
    return <div data-testid="timeline-view">Timeline View Mock</div>;
  };
});

beforeEach(() => {
  (global.fetch as jest.Mock).mockClear();
  (global.alert as jest.Mock).mockClear();
  if (global.window.electronAPI && typeof global.window.electronAPI.invoke === 'function') {
    (global.window.electronAPI.invoke as jest.Mock).mockClear();
  }
});

describe('<App />', () => {
  test('renders Tracepaper Desktop header', () => {
    // Mock the health check
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ status: 'ok', message: 'Backend is healthy' }),
    });
    
    render(<App />);
    const headerElement = screen.getByText(/Tracepaper Desktop/i);
    expect(headerElement).toBeInTheDocument();
  });

  test('displays loading message and then backend status', async () => {
    // Mock the health check
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ status: 'ok', message: 'Backend is healthy for test' }),
    });
    
    render(<App />);
    expect(screen.getByText(/Connecting to backend.../i)).toBeInTheDocument();
    
    await waitFor(() => {
      expect(screen.getByText(/Backend status: ok - Backend is healthy for test/i)).toBeInTheDocument();
    });
  });

  test('handles backend connection error', async () => {
    // Mock health check failure
    (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error for test'));
    
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText(/Error connecting to backend: Network error for test/i)).toBeInTheDocument();
    });
  });

  test('shows search input and button', () => {
    // Mock the health check
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true, 
      json: () => Promise.resolve({ status: 'ok', message: 'Backend is healthy' })
    });
    
    render(<App />);
    expect(screen.getByPlaceholderText(/Search your knowledge.../i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Search/i })).toBeInTheDocument();
  });

  test('calls electronAPI.invoke on Test IPC button click', async () => {
    global.window.electronAPI = {
      invoke: jest.fn().mockResolvedValue('mocked IPC success'),
    };
    
    // Mock the health check
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true, 
      json: () => Promise.resolve({ status: 'ok', message: 'Backend is healthy' })
    });
    
    render(<App />);
    const ipcButton = screen.getByRole('button', { name: /Test IPC/i });
    await userEvent.click(ipcButton);

    await waitFor(() => {
      expect(global.window.electronAPI?.invoke).toHaveBeenCalledWith('my-invokable-ipc', 'hello from renderer');
    });
    
    // Check that alert was called
    expect(global.alert).toHaveBeenCalledWith('IPC Response: mocked IPC success');
  });

  test('renders timeline component', () => {
    // Mock the health check
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true, 
      json: () => Promise.resolve({ status: 'ok', message: 'Backend is healthy' })
    });
    
    render(<App />);
    expect(screen.getByTestId('timeline-view')).toBeInTheDocument();
  });
}); 