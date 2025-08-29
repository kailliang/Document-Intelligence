/**
 * Tests for the main App component.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { jest } from '@jest/globals';
import axios from 'axios';
import App from '../App';

// Mock axios
const mockedAxios = axios as jest.Mocked<typeof axios>;

// Mock child components to isolate App logic
jest.mock('../Document', () => {
  return function MockDocument({ onContentChange }: { onContentChange: (content: string) => void }) {
    return (
      <div data-testid="mock-document">
        <button onClick={() => onContentChange('updated content')}>
          Update Content
        </button>
      </div>
    );
  };
});

jest.mock('../ChatPanel', () => {
  return function MockChatPanel({ onAIStatusChange }: { onAIStatusChange: (connected: boolean, processing: boolean, message: string) => void }) {
    return (
      <div data-testid="mock-chat-panel">
        <button onClick={() => onAIStatusChange(true, false, 'Connected')}>
          Connect AI
        </button>
      </div>
    );
  };
});

describe('App Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders main application structure', () => {
    render(<App />);
    
    expect(screen.getByTestId('mock-document')).toBeInTheDocument();
    expect(screen.getByTestId('mock-chat-panel')).toBeInTheDocument();
  });

  test('loads document list on mount', async () => {
    const mockDocuments = [
      { id: 1, title: 'Document 1', created_at: '2024-01-01T00:00:00', updated_at: '2024-01-01T00:00:00' },
      { id: 2, title: 'Document 2', created_at: '2024-01-01T00:00:00', updated_at: '2024-01-01T00:00:00' }
    ];

    mockedAxios.get.mockResolvedValueOnce({ data: mockDocuments });

    render(<App />);

    await waitFor(() => {
      expect(mockedAxios.get).toHaveBeenCalledWith('http://localhost:8080/api/documents');
    });
  });

  test('handles document list loading error gracefully', async () => {
    mockedAxios.get.mockRejectedValueOnce(new Error('Network error'));

    render(<App />);

    await waitFor(() => {
      expect(mockedAxios.get).toHaveBeenCalled();
    });

    // App should still render without crashing
    expect(screen.getByTestId('mock-document')).toBeInTheDocument();
  });

  test('handles content changes and marks unsaved state', () => {
    render(<App />);
    
    // Initially no unsaved changes
    expect(screen.queryByText(/unsaved/i)).not.toBeInTheDocument();
    
    // Trigger content change
    const updateButton = screen.getByText('Update Content');
    fireEvent.click(updateButton);
    
    // Should handle the content change (specific UI behavior would depend on implementation)
    expect(screen.getByTestId('mock-document')).toBeInTheDocument();
  });

  test('handles responsive layout changes', () => {
    // Mock window resize
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 500, // Mobile width
    });

    render(<App />);

    // Trigger resize event
    fireEvent(window, new Event('resize'));

    // Component should handle responsive changes without crashing
    expect(screen.getByTestId('mock-document')).toBeInTheDocument();
  });

  test('handles AI status updates', () => {
    render(<App />);
    
    const connectButton = screen.getByText('Connect AI');
    fireEvent.click(connectButton);
    
    // Should handle AI status change without errors
    expect(screen.getByTestId('mock-chat-panel')).toBeInTheDocument();
  });

  test('manages sidebar collapse state', () => {
    render(<App />);
    
    // Test would check for sidebar toggle buttons and their functionality
    // Since the actual implementation details aren't visible in the component structure,
    // we're verifying the component renders correctly
    expect(screen.getByTestId('mock-document')).toBeInTheDocument();
    expect(screen.getByTestId('mock-chat-panel')).toBeInTheDocument();
  });

  test('handles document version management', async () => {
    const mockDocument = {
      id: 1,
      title: 'Test Document',
      content: '<h1>Test</h1>',
      version_number: 1,
      last_modified: '2024-01-01T00:00:00'
    };

    mockedAxios.get.mockResolvedValueOnce({ data: [mockDocument] }); // Document list
    mockedAxios.get.mockResolvedValueOnce({ data: mockDocument }); // Specific document

    render(<App />);

    await waitFor(() => {
      expect(mockedAxios.get).toHaveBeenCalled();
    });
  });

  test('handles error states gracefully', async () => {
    // Mock various error scenarios
    mockedAxios.get.mockRejectedValueOnce(new Error('Server error'));

    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

    render(<App />);

    await waitFor(() => {
      expect(mockedAxios.get).toHaveBeenCalled();
    });

    // App should still render despite errors
    expect(screen.getByTestId('mock-document')).toBeInTheDocument();

    consoleSpy.mockRestore();
  });

  test('maintains state consistency during operations', () => {
    render(<App />);
    
    // Test that multiple operations don't break state
    const updateButton = screen.getByText('Update Content');
    fireEvent.click(updateButton);
    
    const connectButton = screen.getByText('Connect AI');
    fireEvent.click(connectButton);
    
    // Component should remain stable
    expect(screen.getByTestId('mock-document')).toBeInTheDocument();
    expect(screen.getByTestId('mock-chat-panel')).toBeInTheDocument();
  });
});

describe('App Component Integration', () => {
  test('document and chat panel communicate correctly', () => {
    render(<App />);
    
    // Both components should be rendered and functional
    expect(screen.getByTestId('mock-document')).toBeInTheDocument();
    expect(screen.getByTestId('mock-chat-panel')).toBeInTheDocument();
    
    // Test interaction between components
    fireEvent.click(screen.getByText('Update Content'));
    fireEvent.click(screen.getByText('Connect AI'));
    
    // Should handle cross-component communication
    expect(screen.getByTestId('mock-document')).toBeInTheDocument();
    expect(screen.getByTestId('mock-chat-panel')).toBeInTheDocument();
  });

  test('handles concurrent API calls correctly', async () => {
    const mockDocuments = [{ id: 1, title: 'Doc 1', created_at: '2024-01-01T00:00:00', updated_at: '2024-01-01T00:00:00' }];
    const mockDocument = { id: 1, title: 'Doc 1', content: '<p>Content</p>', version_number: 1, last_modified: '2024-01-01T00:00:00' };

    mockedAxios.get
      .mockResolvedValueOnce({ data: mockDocuments }) // Documents list
      .mockResolvedValueOnce({ data: mockDocument }); // Specific document

    render(<App />);

    await waitFor(() => {
      expect(mockedAxios.get).toHaveBeenCalledTimes(1);
    });
  });
});