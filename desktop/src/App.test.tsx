import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import App from './App';

// global.fetch is now mocked in setupTests.ts

beforeEach(() => {
  (global.fetch as jest.Mock).mockClear();
  if (global.window.electronAPI && typeof global.window.electronAPI.invoke === 'function') {
    (global.window.electronAPI.invoke as jest.Mock).mockClear();
  }
});

describe('<App />', () => {
  test('renders Tracepaper Desktop header', () => {
    (global.fetch as jest.Mock).mockImplementationOnce(() => 
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ status: 'ok', message: 'Backend is healthy' }),
      })
    );
    render(<App />);
    const headerElement = screen.getByText(/Tracepaper Desktop/i);
    expect(headerElement).toBeInTheDocument();
  });

  test('displays loading message and then backend status', async () => {
    (global.fetch as jest.Mock).mockImplementationOnce(() => 
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ status: 'ok', message: 'Backend is healthy for test' }),
      })
    );
    render(<App />);
    expect(screen.getByText(/Connecting to backend.../i)).toBeInTheDocument();
    
    await waitFor(() => {
      expect(screen.getByText(/Backend status: ok - Backend is healthy for test/i)).toBeInTheDocument();
    });
  });

  test('handles backend connection error', async () => {
    (global.fetch as jest.Mock).mockImplementationOnce(() => 
      Promise.reject(new Error('Network error for test'))
    );
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText(/Error connecting to backend: Network error for test/i)).toBeInTheDocument();
    });
  });

  test('shows search input and button', () => {
    (global.fetch as jest.Mock).mockImplementationOnce(() => Promise.resolve({ ok: true, json: () => Promise.resolve({}) }));
    render(<App />);
    expect(screen.getByPlaceholderText(/Search your knowledge.../i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Search/i })).toBeInTheDocument();
  });

  test('calls electronAPI.invoke on Test IPC button click', async () => {
    global.window.electronAPI = {
      invoke: jest.fn().mockResolvedValue('mocked IPC success'),
    };
    (global.fetch as jest.Mock).mockImplementationOnce(() => Promise.resolve({ ok: true, json: () => Promise.resolve({}) }));
    
    render(<App />);
    const ipcButton = screen.getByRole('button', { name: /Test IPC/i });
    ipcButton.click();

    await waitFor(() => {
      expect(global.window.electronAPI?.invoke).toHaveBeenCalledWith('my-invokable-ipc', 'hello from renderer');
    });
  });
}); 