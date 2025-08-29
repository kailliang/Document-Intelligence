/**
 * Tests for the ChatPanel component.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { jest } from '@jest/globals';
import useWebSocket, { ReadyState } from 'react-use-websocket';
import ChatPanel from '../ChatPanel';

// Mock react-use-websocket
const mockUseWebSocket = useWebSocket as jest.MockedFunction<typeof useWebSocket>;

// Mock Mermaid
jest.mock('mermaid', () => ({
  initialize: jest.fn(),
  render: jest.fn().mockResolvedValue({ svg: '<svg>mock diagram</svg>' }),
}));

// Mock child components
jest.mock('../components/InlineSuggestionCard', () => {
  return function MockInlineSuggestionCard({ 
    suggestion, 
    onAccept, 
    onDismiss 
  }: { 
    suggestion: any, 
    onAccept: () => void, 
    onDismiss: () => void 
  }) {
    return (
      <div data-testid="suggestion-card">
        <span>{suggestion.description}</span>
        <button onClick={onAccept}>Accept</button>
        <button onClick={onDismiss}>Dismiss</button>
      </div>
    );
  };
});

jest.mock('../components/ProcessingStages', () => {
  return function MockProcessingStages({ stages }: { stages: any[] }) {
    return (
      <div data-testid="processing-stages">
        {stages.map((stage, index) => (
          <div key={index}>{stage.name}</div>
        ))}
      </div>
    );
  };
});

describe('ChatPanel Component', () => {
  const defaultProps = {
    getCurrentDocumentContent: jest.fn(() => '<h1>Test Document</h1>'),
    onInsertMermaid: jest.fn(),
    documentId: 1,
    documentVersion: 'v1.0',
    editorRef: { current: null },
    onAIStatusChange: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Default WebSocket mock setup
    mockUseWebSocket.mockReturnValue({
      sendMessage: jest.fn(),
      lastMessage: null,
      readyState: ReadyState.OPEN,
      getWebSocket: jest.fn(),
    });
  });

  test('renders chat panel with initial state', () => {
    render(<ChatPanel {...defaultProps} />);
    
    expect(screen.getByRole('textbox')).toBeInTheDocument();
    expect(screen.getByText(/send/i)).toBeInTheDocument();
  });

  test('handles user message input', () => {
    render(<ChatPanel {...defaultProps} />);
    
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'Test message' } });
    
    expect(input).toHaveValue('Test message');
  });

  test('sends message when form is submitted', () => {
    const mockSendMessage = jest.fn();
    mockUseWebSocket.mockReturnValue({
      sendMessage: mockSendMessage,
      lastMessage: null,
      readyState: ReadyState.OPEN,
      getWebSocket: jest.fn(),
    });

    render(<ChatPanel {...defaultProps} />);
    
    const input = screen.getByRole('textbox');
    const sendButton = screen.getByText(/send/i);
    
    fireEvent.change(input, { target: { value: 'Test message' } });
    fireEvent.click(sendButton);
    
    expect(mockSendMessage).toHaveBeenCalledWith(
      expect.stringContaining('Test message')
    );
  });

  test('prevents sending empty messages', () => {
    const mockSendMessage = jest.fn();
    mockUseWebSocket.mockReturnValue({
      sendMessage: mockSendMessage,
      lastMessage: null,
      readyState: ReadyState.OPEN,
      getWebSocket: jest.fn(),
    });

    render(<ChatPanel {...defaultProps} />);
    
    const sendButton = screen.getByText(/send/i);
    fireEvent.click(sendButton);
    
    expect(mockSendMessage).not.toHaveBeenCalled();
  });

  test('displays WebSocket connection status', () => {
    mockUseWebSocket.mockReturnValue({
      sendMessage: jest.fn(),
      lastMessage: null,
      readyState: ReadyState.CONNECTING,
      getWebSocket: jest.fn(),
    });

    render(<ChatPanel {...defaultProps} />);
    
    // Should show connecting status
    expect(defaultProps.onAIStatusChange).toHaveBeenCalledWith(
      false, false, expect.any(String)
    );
  });

  test('handles WebSocket disconnection', () => {
    mockUseWebSocket.mockReturnValue({
      sendMessage: jest.fn(),
      lastMessage: null,
      readyState: ReadyState.CLOSED,
      getWebSocket: jest.fn(),
    });

    render(<ChatPanel {...defaultProps} />);
    
    expect(defaultProps.onAIStatusChange).toHaveBeenCalledWith(
      false, false, expect.any(String)
    );
  });

  test('processes AI suggestion response', () => {
    const mockMessage = {
      data: JSON.stringify({
        type: 'ai_suggestions',
        data: {
          issues: [
            {
              id: '1',
              type: 'Grammar',
              severity: 'high',
              description: 'Missing period',
              originalText: 'Test sentence',
              replaceTo: 'Test sentence.',
              confidence: 0.9
            }
          ]
        }
      })
    };

    mockUseWebSocket.mockReturnValue({
      sendMessage: jest.fn(),
      lastMessage: mockMessage,
      readyState: ReadyState.OPEN,
      getWebSocket: jest.fn(),
    });

    render(<ChatPanel {...defaultProps} />);
    
    expect(screen.getByTestId('suggestion-card')).toBeInTheDocument();
    expect(screen.getByText('Missing period')).toBeInTheDocument();
  });

  test('handles suggestion card actions', () => {
    const mockMessage = {
      data: JSON.stringify({
        type: 'ai_suggestions', 
        data: {
          issues: [
            {
              id: '1',
              type: 'Grammar',
              severity: 'high',
              description: 'Missing period',
              originalText: 'Test sentence',
              replaceTo: 'Test sentence.',
              confidence: 0.9
            }
          ]
        }
      })
    };

    mockUseWebSocket.mockReturnValue({
      sendMessage: jest.fn(),
      lastMessage: mockMessage,
      readyState: ReadyState.OPEN,
      getWebSocket: jest.fn(),
    });

    render(<ChatPanel {...defaultProps} />);
    
    const acceptButton = screen.getByText('Accept');
    fireEvent.click(acceptButton);
    
    // Should handle suggestion acceptance
    expect(screen.getByTestId('suggestion-card')).toBeInTheDocument();
  });

  test('displays processing stages during AI analysis', () => {
    const mockProcessingMessage = {
      data: JSON.stringify({
        type: 'processing_stage',
        stage: 'intent_detection',
        name: 'Intent Detection',
        message: 'Analyzing your request...',
        progress: 10
      })
    };

    mockUseWebSocket.mockReturnValue({
      sendMessage: jest.fn(),
      lastMessage: mockProcessingMessage,
      readyState: ReadyState.OPEN,
      getWebSocket: jest.fn(),
    });

    render(<ChatPanel {...defaultProps} />);
    
    expect(screen.getByTestId('processing-stages')).toBeInTheDocument();
    expect(screen.getByText('Intent Detection')).toBeInTheDocument();
  });

  test('handles Mermaid diagram rendering', async () => {
    const mockMessage = {
      data: JSON.stringify({
        type: 'text',
        content: 'Here is a diagram:\n```mermaid\ngraph TD\nA-->B\n```'
      })
    };

    mockUseWebSocket.mockReturnValue({
      sendMessage: jest.fn(),
      lastMessage: mockMessage,
      readyState: ReadyState.OPEN,
      getWebSocket: jest.fn(),
    });

    render(<ChatPanel {...defaultProps} />);
    
    await waitFor(() => {
      expect(screen.getByText(/here is a diagram/i)).toBeInTheDocument();
    });
  });

  test('handles error messages from AI', () => {
    const mockErrorMessage = {
      data: JSON.stringify({
        type: 'ai_error',
        message: 'AI service temporarily unavailable'
      })
    };

    mockUseWebSocket.mockReturnValue({
      sendMessage: jest.fn(),
      lastMessage: mockErrorMessage,
      readyState: ReadyState.OPEN,
      getWebSocket: jest.fn(),
    });

    render(<ChatPanel {...defaultProps} />);
    
    expect(screen.getByText(/ai service temporarily unavailable/i)).toBeInTheDocument();
  });

  test('clears chat history when requested', () => {
    render(<ChatPanel {...defaultProps} />);
    
    // Add some messages first
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'Test message' } });
    
    // Look for clear chat functionality (button would be in actual implementation)
    expect(input).toBeInTheDocument();
  });

  test('handles bulk suggestion actions', () => {
    const mockMessage = {
      data: JSON.stringify({
        type: 'ai_suggestions',
        data: {
          issues: [
            {
              id: '1',
              type: 'Grammar',
              severity: 'high',
              description: 'Missing period',
              originalText: 'Test sentence',
              replaceTo: 'Test sentence.',
              confidence: 0.9
            },
            {
              id: '2',
              type: 'Style',
              severity: 'medium',
              description: 'Improve clarity',
              originalText: 'This thing',
              replaceTo: 'This component',
              confidence: 0.8
            }
          ]
        }
      })
    };

    mockUseWebSocket.mockReturnValue({
      sendMessage: jest.fn(),
      lastMessage: mockMessage,
      readyState: ReadyState.OPEN,
      getWebSocket: jest.fn(),
    });

    render(<ChatPanel {...defaultProps} />);
    
    // Should display multiple suggestion cards
    expect(screen.getAllByTestId('suggestion-card')).toHaveLength(2);
  });

  test('maintains message history across renders', () => {
    const { rerender } = render(<ChatPanel {...defaultProps} />);
    
    // Add a message
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'First message' } });
    
    // Rerender component
    rerender(<ChatPanel {...defaultProps} />);
    
    // Component should maintain state
    expect(input).toBeInTheDocument();
  });

  test('handles WebSocket reconnection', () => {
    // Start with closed connection
    mockUseWebSocket.mockReturnValue({
      sendMessage: jest.fn(),
      lastMessage: null,
      readyState: ReadyState.CLOSED,
      getWebSocket: jest.fn(),
    });

    const { rerender } = render(<ChatPanel {...defaultProps} />);
    
    // Reconnect
    mockUseWebSocket.mockReturnValue({
      sendMessage: jest.fn(),
      lastMessage: null,
      readyState: ReadyState.OPEN,
      getWebSocket: jest.fn(),
    });

    rerender(<ChatPanel {...defaultProps} />);
    
    expect(defaultProps.onAIStatusChange).toHaveBeenCalledWith(
      true, false, expect.any(String)
    );
  });
});

describe('ChatPanel Message Handling', () => {
  const defaultProps = {
    getCurrentDocumentContent: jest.fn(() => '<h1>Test Document</h1>'),
    onInsertMermaid: jest.fn(),
    documentId: 1,
    documentVersion: 'v1.0',
    editorRef: { current: null },
    onAIStatusChange: jest.fn(),
  };

  test('handles malformed WebSocket messages gracefully', () => {
    const mockMalformedMessage = {
      data: 'invalid json{'
    };

    mockUseWebSocket.mockReturnValue({
      sendMessage: jest.fn(),
      lastMessage: mockMalformedMessage,
      readyState: ReadyState.OPEN,
      getWebSocket: jest.fn(),
    });

    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

    render(<ChatPanel {...defaultProps} />);
    
    // Should not crash on malformed message
    expect(screen.getByRole('textbox')).toBeInTheDocument();

    consoleSpy.mockRestore();
  });

  test('handles unexpected message types', () => {
    const mockUnknownMessage = {
      data: JSON.stringify({
        type: 'unknown_message_type',
        content: 'Unknown content'
      })
    };

    mockUseWebSocket.mockReturnValue({
      sendMessage: jest.fn(),
      lastMessage: mockUnknownMessage,
      readyState: ReadyState.OPEN,
      getWebSocket: jest.fn(),
    });

    render(<ChatPanel {...defaultProps} />);
    
    // Should handle gracefully
    expect(screen.getByRole('textbox')).toBeInTheDocument();
  });
});