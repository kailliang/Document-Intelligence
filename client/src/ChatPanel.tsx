import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import mermaid from "mermaid";
import useWebSocket, { ReadyState } from 'react-use-websocket';
import InlineSuggestionCard from './components/InlineSuggestionCard';

mermaid.initialize({ startOnLoad: true, theme: 'default' });

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp?: Date;
  type?: "text" | "suggestion_cards";
  suggestions?: Suggestion[];
}

interface Suggestion {
  id: string;
  type: string;
  severity: 'high' | 'medium' | 'low';
  paragraph: number;
  description: string;
  original_text: string;
  replace_to: string;
  confidence: number;
  agent: 'technical' | 'legal' | 'novelty' | 'lead';
  created_at: string;
}

interface DiagramInsertion {
  insert_after_text: string;
  mermaid_syntax: string;
  diagram_type: string;
  title?: string;
}

interface ChatPanelProps {
  className?: string;
  getCurrentDocumentContent?: () => string;
  onDiagramInsertions?: (insertions: DiagramInsertion[]) => void;
  onInsertMermaid?: (mermaidSyntax: string, title?: string) => void;
  documentId?: number;
  documentVersion?: string;
}

// Mermaid diagram component
function MermaidDiagram({ chart, onInsert }: { chart: string; onInsert?: (mermaidSyntax: string, title?: string) => void }) {
  const ref = useRef<HTMLDivElement>(null);
  const [isRendered, setIsRendered] = useState(false);

  useEffect(() => {
    const renderMermaid = async () => {
      if (!ref.current || !chart.trim()) return;
      
      try {
        setIsRendered(false);
        
        // Clear previous content
        ref.current.innerHTML = '';
        
        // Generate unique ID with timestamp to ensure uniqueness
        const uniqueId = `mermaid-${Date.now()}-${Math.random().toString(36).substr(2, 6)}`;
        
        // Re-initialize mermaid to ensure proper rendering
        mermaid.initialize({ 
          startOnLoad: false, 
          theme: 'default',
          securityLevel: 'loose',
          fontFamily: 'Arial, sans-serif'
        });
        
        // Render chart
        const { svg } = await mermaid.render(uniqueId, chart);
        
        if (ref.current) {
          ref.current.innerHTML = svg;
          setIsRendered(true);
        }
      } catch (error) {
        console.error("Mermaid rendering error:", error);
        if (ref.current) {
          ref.current.innerHTML = `<div style="color: red; padding: 10px; border: 1px solid red; border-radius: 4px;">
            <strong>Diagram rendering failed</strong><br/>
            Please check the syntax
          </div>`;
          setIsRendered(true);
        }
      }
    };

    renderMermaid();
  }, [chart]);

  return (
    <div className="my-4 p-3 bg-gray-50 border rounded-lg">
      {onInsert && (
        <div className="flex justify-end mb-2">
          <button
            onClick={() => onInsert(chart)}
            className="text-xs px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            📊 Insert into Document
          </button>
        </div>
      )}
      <div 
        ref={ref} 
        className="mermaid-container text-center"
        style={{ minHeight: isRendered ? 'auto' : '100px' }}
      />
      {!isRendered && (
        <div className="flex items-center justify-center py-4">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
          <span className="ml-2 text-sm text-gray-600">Rendering diagram...</span>
        </div>
      )}
    </div>
  );
}

export default function ChatPanel({ 
  className, 
  getCurrentDocumentContent,
  onDiagramInsertions,
  onInsertMermaid,
  documentId,
  documentVersion = "v1.0"
}: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // WebSocket connection to unified chat endpoint
  const socketUrl = `ws://localhost:8000/ws/chat`;
  const { sendJsonMessage, lastJsonMessage, readyState } = useWebSocket(socketUrl, {
    shouldReconnect: () => true,
    reconnectInterval: 3000,
    reconnectAttempts: 10,
  });

  // Auto-scroll to latest message
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load chat history when document or version changes
  useEffect(() => {
    const loadChatHistory = async () => {
      if (!documentId || !documentVersion) return;

      try {
        console.log(`Loading chat history for document ${documentId}, version ${documentVersion}`);
        
        const response = await fetch(`http://localhost:8000/api/chat/history/${documentId}/${documentVersion}`);
        const data = await response.json();
        
        if (data.success && data.messages) {
          // Convert loaded messages to ChatMessage format
          const loadedMessages: ChatMessage[] = data.messages.map((msg: any) => {
            const baseMessage: ChatMessage = {
              role: msg.type === 'user' ? 'user' : 'assistant',
              content: msg.content,
              timestamp: new Date(msg.timestamp),
              type: msg.type === 'suggestion_cards' ? 'suggestion_cards' : 'text'
            };

            // Add suggestions if this is a suggestion_cards message
            if (msg.type === 'suggestion_cards' && msg.metadata?.suggestion_cards) {
              baseMessage.suggestions = msg.metadata.suggestion_cards.filter((card: any) => {
                // Only include cards that haven't been acted upon
                const cardActions = msg.metadata.card_actions || {};
                return !cardActions[card.id];
              });
            }

            return baseMessage;
          });
          
          setMessages(loadedMessages);
          console.log(`Loaded ${loadedMessages.length} chat messages`);
        } else {
          // No chat history yet, start with empty messages
          setMessages([]);
        }
      } catch (error) {
        console.error('Failed to load chat history:', error);
        // Start with empty messages on error
        setMessages([]);
      }
    };

    loadChatHistory();
  }, [documentId, documentVersion]);

  // Handle WebSocket messages
  useEffect(() => {
    if (!lastJsonMessage) return;

    const message = lastJsonMessage as any;
    
    switch (message.type) {
      case 'connection_success':
        console.log('✅ WebSocket connected:', message.message);
        break;
        
      case 'processing_start':
        setIsLoading(true);
        break;
        
      case 'assistant_response':
        setIsLoading(false);
        
        // Process AI response messages
        if (message.messages && Array.isArray(message.messages)) {
          message.messages.forEach((aiMessage: any) => {
            if (aiMessage.type === 'text') {
              // Regular text message
              const assistantMessage: ChatMessage = {
                role: "assistant",
                content: aiMessage.content,
                timestamp: new Date(),
                type: "text"
              };
              setMessages(prev => [...prev, assistantMessage]);
            } else if (aiMessage.type === 'suggestion_cards' && aiMessage.cards) {
              // Suggestion cards message
              const suggestionMessage: ChatMessage = {
                role: "assistant",
                content: "Here are my suggestions for improving your document:",
                timestamp: new Date(),
                type: "suggestion_cards",
                suggestions: aiMessage.cards
              };
              setMessages(prev => [...prev, suggestionMessage]);
            }
          });
        }
        break;
        
      case 'workflow_error':
      case 'processing_error':
      case 'validation_error':
        setIsLoading(false);
        const errorMessage: ChatMessage = {
          role: "assistant",
          content: `Error: ${message.message}`,
          timestamp: new Date()
        };
        setMessages(prev => [...prev, errorMessage]);
        break;
        
      default:
        console.log('Received unknown message type:', message.type);
    }
  }, [lastJsonMessage]);

  // Document save event listener (for Mermaid re-rendering)
  useEffect(() => {
    const handleDocumentSave = () => {
      console.log('📄 Document saved, triggering Mermaid re-render');
      // Force re-render mermaid diagrams
      setTimeout(() => {
        const mermaidElements = document.querySelectorAll('.mermaid-container');
        mermaidElements.forEach(element => {
          const event = new Event('mermaid-rerender', { bubbles: true });
          element.dispatchEvent(event);
        });
      }, 500);
    };

    window.addEventListener('document-saved', handleDocumentSave);
    
    return () => {
      window.removeEventListener('document-saved', handleDocumentSave);
    };
  }, []);

  // Send message via WebSocket
  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading || readyState !== ReadyState.OPEN) return;

    const userMessage: ChatMessage = {
      role: "user",
      content: inputMessage,
      timestamp: new Date()
    };

    // Add user message immediately
    setMessages(prev => [...prev, userMessage]);
    setInputMessage("");
    setIsLoading(true);

    try {
      // Get current document content
      const currentDocumentContent = getCurrentDocumentContent ? getCurrentDocumentContent() : "";

      // Send message via WebSocket
      sendJsonMessage({
        message: inputMessage,
        document_content: currentDocumentContent,
        document_id: documentId,
        document_version: documentVersion
      });

    } catch (error) {
      console.error("Error sending message:", error);
      setIsLoading(false);
      
      // Add error message
      const errorMessage: ChatMessage = {
        role: "assistant",
        content: "Sorry, I couldn't send your message. Please try again.",
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    }
  };

  // Handle suggestion card actions
  const handleSuggestionAccept = async (cardId: string) => {
    console.log('Accepting suggestion:', cardId);
    
    // Find the message containing this card to get message ID
    const messageWithCard = messages.find(msg => 
      msg.suggestions?.some(s => s.id === cardId)
    );
    
    if (messageWithCard && documentId && documentVersion) {
      try {
        // Call API to mark card as accepted
        const response = await fetch(
          `http://localhost:8000/api/chat/suggestion-action/${documentId}/${documentVersion}/${Date.now()}?card_id=${cardId}&action=accepted`,
          { method: 'POST' }
        );
        
        if (response.ok) {
          console.log('✅ Suggestion accepted successfully');
        }
      } catch (error) {
        console.error('Failed to accept suggestion:', error);
      }
    }
    
    // Remove the suggestion card from messages (optimistic update)
    setMessages(prev => 
      prev.map(msg => ({
        ...msg,
        suggestions: msg.suggestions?.filter(s => s.id !== cardId)
      })).filter(msg => 
        msg.type !== 'suggestion_cards' || (msg.suggestions && msg.suggestions.length > 0)
      )
    );
  };

  const handleSuggestionDismiss = async (cardId: string) => {
    console.log('Dismissing suggestion:', cardId);
    
    // Find the message containing this card to get message ID
    const messageWithCard = messages.find(msg => 
      msg.suggestions?.some(s => s.id === cardId)
    );
    
    if (messageWithCard && documentId && documentVersion) {
      try {
        // Call API to mark card as dismissed
        const response = await fetch(
          `http://localhost:8000/api/chat/suggestion-action/${documentId}/${documentVersion}/${Date.now()}?card_id=${cardId}&action=dismissed`,
          { method: 'POST' }
        );
        
        if (response.ok) {
          console.log('✅ Suggestion dismissed successfully');
        }
      } catch (error) {
        console.error('Failed to dismiss suggestion:', error);
      }
    }
    
    // Remove the suggestion card from messages (optimistic update)
    setMessages(prev => 
      prev.map(msg => ({
        ...msg,
        suggestions: msg.suggestions?.filter(s => s.id !== cardId)
      })).filter(msg => 
        msg.type !== 'suggestion_cards' || (msg.suggestions && msg.suggestions.length > 0)
      )
    );
  };

  const handleSuggestionCopy = async (cardId: string) => {
    console.log('Copying suggestion:', cardId);
    const allSuggestions = messages.flatMap(msg => msg.suggestions || []);
    const suggestion = allSuggestions.find(s => s.id === cardId);
    
    if (suggestion) {
      try {
        await navigator.clipboard.writeText(suggestion.replace_to);
        console.log('✅ Suggestion copied to clipboard');
        // TODO: Show success notification
      } catch (error) {
        console.error('Failed to copy suggestion:', error);
      }
    }
  };

  // Handle Enter key for sending
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // Get connection status
  const getConnectionStatus = () => {
    switch (readyState) {
      case ReadyState.CONNECTING:
        return { text: "Connecting...", color: "text-yellow-600" };
      case ReadyState.OPEN:
        return { text: "Connected", color: "text-green-600" };
      case ReadyState.CLOSING:
        return { text: "Disconnecting...", color: "text-yellow-600" };
      case ReadyState.CLOSED:
        return { text: "Disconnected", color: "text-red-600" };
      default:
        return { text: "Unknown", color: "text-gray-600" };
    }
  };

  const connectionStatus = getConnectionStatus();

  return (
    <div className={`flex flex-col h-full bg-white rounded-lg shadow-sm ${className}`}>
      {/* Chat title with connection status */}
      <div className="px-4 py-3 border-b">
        <div className="flex items-center justify-between">
          <p className="text-xs text-gray-500 flex-1">
            Ask questions or request document analysis
          </p>
          <div className={`text-xs ${connectionStatus.color} flex items-center gap-1`}>
            <div className={`w-2 h-2 rounded-full ${
              readyState === ReadyState.OPEN ? 'bg-green-500' : 
              readyState === ReadyState.CONNECTING ? 'bg-yellow-500' : 'bg-red-500'
            }`}></div>
            {connectionStatus.text}
          </div>
        </div>
      </div>

      {/* Message list */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            <p className="text-sm">Start a conversation with the AI Assistant</p>
            <div className="mt-4 space-y-2 text-xs text-gray-400">
              <p>Try asking:</p>
              <p className="italic">"Please analyze this document for issues"</p>
              <p className="italic">"How can I improve the patent claims?"</p>
              <p className="italic">"Generate a process flowchart"</p>
            </div>
          </div>
        ) : (
          messages.map((msg, index) => (
            <div
              key={index}
              className={`${msg.role === "user" ? "ml-auto" : "mr-auto"} max-w-[90%]`}
            >
              {msg.role === "user" ? (
                // User message
                <div className="bg-blue-600 text-white rounded-lg px-4 py-2">
                  <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                </div>
              ) : (
                // Assistant message
                <div className="space-y-3">
                  {msg.type === "suggestion_cards" && msg.suggestions && msg.suggestions.length > 0 ? (
                    // Suggestion cards
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                      <InlineSuggestionCard 
                        suggestions={msg.suggestions}
                        onAccept={handleSuggestionAccept}
                        onDismiss={handleSuggestionDismiss}
                        onCopy={handleSuggestionCopy}
                      />
                    </div>
                  ) : (
                    // Regular text message
                    <div className="bg-gray-100 text-gray-800 rounded-lg px-4 py-2">
                      <div className="text-sm">
                        <ReactMarkdown
                          components={{
                            code({ className, children, ...props }: any) {
                              const match = /language-(\w+)/.exec(className || '');
                              const isMermaid = match && match[1] === 'mermaid';
                              const isInline = (props as any)?.inline;

                              if (!isInline && isMermaid) {
                                return <MermaidDiagram chart={String(children).replace(/\n$/, '')} onInsert={onInsertMermaid} />;
                              }

                              return (
                                <code
                                  className={`${!isInline ? 'block bg-gray-800 text-gray-100 p-3 rounded my-2 overflow-x-auto' : 'bg-gray-200 px-1 rounded'}`}
                                  {...props}
                                >
                                  {children}
                                </code>
                              );
                            }
                          }}
                        >
                          {msg.content}
                        </ReactMarkdown>
                      </div>
                    </div>
                  )}
                </div>
              )}
              
              {msg.timestamp && (
                <p className="text-xs text-gray-400 mt-1 px-1">
                  {msg.timestamp.toLocaleTimeString()}
                </p>
              )}
            </div>
          ))
        )}

        {isLoading && (
          <div className="mr-auto max-w-[80%]">
            <div className="bg-gray-100 rounded-lg px-4 py-2">
              <div className="flex items-center space-x-2">
                <div className="animate-bounce h-2 w-2 bg-gray-400 rounded-full"></div>
                <div className="animate-bounce h-2 w-2 bg-gray-400 rounded-full delay-100"></div>
                <div className="animate-bounce h-2 w-2 bg-gray-400 rounded-full delay-200"></div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="border-t p-4">
        <div className="flex gap-2" style={{ position: 'relative' }}>
          <textarea
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={readyState === ReadyState.OPEN ? "Enter message..." : "Connecting..."}
            className="flex-1 px-3 py-2 border rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
            rows={1}
            disabled={isLoading || readyState !== ReadyState.OPEN}
            style={{ height: '5rem' }}
          />
          <button
            onClick={sendMessage}
            disabled={!inputMessage.trim() || isLoading || readyState !== ReadyState.OPEN}
            style={{
              position: 'absolute',
              bottom: '0.5rem',
              right: '0.5rem',
            }}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              !inputMessage.trim() || isLoading || readyState !== ReadyState.OPEN
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-blue-600 text-white hover:bg-blue-700'
            }`}
          >
            {isLoading ? 'Sending...' : 'Send'}
          </button>
        </div>
      </div>
    </div>
  );
}