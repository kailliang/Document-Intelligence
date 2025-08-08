import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import mermaid from "mermaid";
import useWebSocket, { ReadyState } from 'react-use-websocket';
import InlineSuggestionCard from './components/InlineSuggestionCard';
import ProcessingStages from './components/ProcessingStages';
import { findTextInDocument, replaceText } from './internal/HighlightExtension';

mermaid.initialize({ startOnLoad: true, theme: 'default' });

interface ChatMessage {
  id?: string; // Database message ID for API calls
  role: "user" | "assistant";
  content: string;
  timestamp?: Date;
  type?: "text" | "suggestion_cards" | "suggestion_summary";
  suggestions?: Suggestion[];
  summary?: SuggestionSummary;
}

interface SuggestionSummary {
  total_count: number;
  severity_counts: {high: number, medium: number, low: number};
  type_counts: Record<string, number>;
  accepted_count: number;
  dismissed_count: number;
}

interface ProcessingStage {
  id: string;
  name: string;
  message: string;
  progress: number;
  status: 'pending' | 'active' | 'completed' | 'error';
  agent: string;
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
  editorRef?: React.MutableRefObject<any>;
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
      {onInsert && (
        <div className="flex justify-center mt-3">
          <button
            onClick={() => onInsert(chart)}
            className="text-xs px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            📊 Insert into Document
          </button>
        </div>
      )}
    </div>
  );
}

export default function ChatPanel({ 
  className, 
  getCurrentDocumentContent,
  onInsertMermaid,
  documentId,
  documentVersion = "v1.0",
  editorRef
}: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [highlightedCardId, setHighlightedCardId] = useState<string | null>(null);
  const [currentProcessingStage, setCurrentProcessingStage] = useState<ProcessingStage | null>(null);
  const [allProcessingStages, setAllProcessingStages] = useState<ProcessingStage[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const highlightTimeoutRef = useRef<number | null>(null);

  // Predefined processing stages configuration
  const defaultStages: ProcessingStage[] = [
    { id: "intent_detection", name: "Intent Detection", message: "Analyzing your request...", progress: 10, status: 'pending', agent: "system" },
    { id: "agent_selection", name: "Agent Selection", message: "Selecting appropriate AI agents...", progress: 20, status: 'pending', agent: "system" },
    { id: "document_parsing", name: "Document Parsing", message: "Processing document content...", progress: 30, status: 'pending', agent: "technical" },
    { id: "legal_analysis", name: "Legal Analysis", message: "Legal agent investigating compliance...", progress: 50, status: 'pending', agent: "legal" },
    { id: "technical_analysis", name: "Technical Analysis", message: "Technical agent reviewing structure...", progress: 70, status: 'pending', agent: "technical" },
    { id: "generating_suggestions", name: "Generating Suggestions", message: "Preparing improvement suggestions...", progress: 85, status: 'pending', agent: "ai_enhanced" },
    { id: "finalizing_results", name: "Finalizing Results", message: "Finalizing analysis results...", progress: 95, status: 'pending', agent: "system" }
  ];

  // WebSocket connection to unified chat endpoint
  const socketUrl = `ws://localhost:8000/ws/chat`;
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);
  const maxReconnectAttempts = 10;
  
  const { sendJsonMessage, lastJsonMessage, readyState } = useWebSocket(socketUrl, {
    shouldReconnect: (closeEvent) => {
      // Implement exponential backoff and error handling
      console.log('WebSocket closed:', closeEvent);
      
      // Don't reconnect if it's a permanent error (4000-4999 range)
      if (closeEvent?.code >= 4000 && closeEvent?.code < 5000) {
        console.error('Permanent WebSocket error, not reconnecting:', closeEvent.reason);
        setConnectionError(`Connection failed: ${closeEvent.reason}`);
        return false;
      }
      
      // Stop reconnecting after max attempts
      if (reconnectAttempts >= maxReconnectAttempts) {
        console.error('Max reconnection attempts reached');
        setConnectionError('Unable to connect after multiple attempts. Please refresh the page.');
        return false;
      }
      
      setReconnectAttempts(prev => prev + 1);
      setConnectionError(`Reconnecting... (attempt ${reconnectAttempts + 1}/${maxReconnectAttempts})`);
      return true;
    },
    reconnectInterval: 3000,
    reconnectAttempts: maxReconnectAttempts,
    onOpen: () => {
      console.log('WebSocket connected successfully');
      setConnectionError(null);
      setReconnectAttempts(0);
    },
    onClose: (event) => {
      console.log('WebSocket closed:', event.code, event.reason);
      if (event.code !== 1000) { // 1000 is normal closure
        setConnectionError('Connection lost. Attempting to reconnect...');
      }
    },
    onError: (error) => {
      console.error('WebSocket error:', error);
      setConnectionError('Connection error occurred');
    },
    retryOnError: true,
    filter: (message) => {
      // Validate incoming messages
      try {
        const data = JSON.parse(message.data);
        return data && typeof data === 'object';
      } catch {
        console.warn('Received invalid JSON message, filtering out');
        return false;
      }
    },
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
              id: msg.id?.toString(), // Include database ID
              role: msg.type === 'user' ? 'user' : 'assistant',
              content: msg.content,
              timestamp: new Date(msg.timestamp),
              type: msg.type === 'suggestion_cards' ? 'suggestion_cards' : 
                    msg.type === 'suggestion_summary' ? 'suggestion_summary' : 'text'
            };

            // Add suggestions if this is a suggestion_cards message
            if (msg.type === 'suggestion_cards' && msg.suggestion_cards) {
              // Filter out cards that have been acted upon (accepted/dismissed)
              const activeCards = msg.suggestion_cards.filter((card: any) => {
                // Check if this card has been acted upon
                const cardActions = msg.metadata?.card_actions || {};
                const cardStatus = cardActions[card.id];
                // Only show cards that haven't been acted upon
                return !cardStatus || (cardStatus !== 'accepted' && cardStatus !== 'dismissed');
              });
              
              // Only include suggestions if there are active cards
              if (activeCards.length > 0) {
                baseMessage.suggestions = activeCards;
              } else {
                // No active cards, don't include this message
                return null;
              }
            }

            return baseMessage;
          }).filter((msg: ChatMessage | null) => msg !== null) as ChatMessage[]; // Filter out null messages (empty suggestion card sets)
          
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

  // Cleanup highlight timeout on unmount
  useEffect(() => {
    return () => {
      if (highlightTimeoutRef.current) {
        clearTimeout(highlightTimeoutRef.current);
        highlightTimeoutRef.current = null;
      }
    };
  }, []);

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
        // Initialize processing stages
        setAllProcessingStages(defaultStages);
        setCurrentProcessingStage(null);
        break;

      case 'processing_stage':
        // Handle individual processing stage updates
        const stageData = message;
        const updatedStages = allProcessingStages.length > 0 ? allProcessingStages : defaultStages;
        
        // Update stages with current stage status
        const newStages = updatedStages.map(stage => {
          if (stage.id === stageData.stage) {
            return {
              ...stage,
              name: stageData.name || stage.name,
              message: stageData.message || stage.message,
              progress: stageData.progress || stage.progress,
              status: 'active' as const,
              agent: stageData.agent || stage.agent
            };
          } else if (defaultStages.findIndex(s => s.id === stage.id) < defaultStages.findIndex(s => s.id === stageData.stage)) {
            // Mark earlier stages as completed
            return { ...stage, status: 'completed' as const };
          }
          return stage;
        });
        
        setAllProcessingStages(newStages);
        setCurrentProcessingStage(newStages.find(s => s.id === stageData.stage) || null);
        break;
        
      case 'assistant_response':
        setIsLoading(false);
        // Clear processing stages when response is complete
        setCurrentProcessingStage(null);
        setAllProcessingStages([]);
        
        // Process AI response messages
        if (message.messages && Array.isArray(message.messages)) {
          message.messages.forEach((aiMessage: any) => {
            if (aiMessage.type === 'text') {
              // Regular text message
              const assistantMessage: ChatMessage = {
                id: aiMessage.message_id?.toString(),
                role: "assistant",
                content: aiMessage.content,
                timestamp: new Date(),
                type: "text"
              };
              setMessages(prev => [...prev, assistantMessage]);
            } else if (aiMessage.type === 'suggestion_summary') {
              // Summary message (always persistent)
              const summaryMessage: ChatMessage = {
                id: aiMessage.message_id?.toString(),
                role: "assistant", 
                content: aiMessage.content,
                timestamp: new Date(),
                type: "suggestion_summary",
                summary: aiMessage.summary
              };
              setMessages(prev => [...prev, summaryMessage]);
            } else if (aiMessage.type === 'suggestion_cards' && aiMessage.cards) {
              // Suggestion cards message
              const suggestionMessage: ChatMessage = {
                id: aiMessage.message_id?.toString(),
                role: "assistant",
                content: "详细建议：",
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

  // Send message via WebSocket with retry logic
  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    // Check connection state and handle accordingly
    if (readyState === ReadyState.CONNECTING) {
      // Wait for connection with timeout
      console.log('WebSocket is connecting, waiting...');
      setConnectionError('Connecting...');
      return;
    }
    
    if (readyState !== ReadyState.OPEN) {
      setConnectionError('Not connected. Please wait for reconnection.');
      return;
    }

    const userMessage: ChatMessage = {
      role: "user",
      content: inputMessage,
      timestamp: new Date()
    };

    // Add user message immediately
    setMessages(prev => [...prev, userMessage]);
    const messageToSend = inputMessage;
    setInputMessage("");
    setIsLoading(true);

    try {
      // Get current document content
      const currentDocumentContent = getCurrentDocumentContent ? getCurrentDocumentContent() : "";

      // Send message via WebSocket with retry
      const sendWithRetry = async (retries = 3) => {
        try {
          sendJsonMessage({
            message: messageToSend,
            document_content: currentDocumentContent,
            document_id: documentId,
            document_version: documentVersion
          });
        } catch (error) {
          console.error(`Send attempt failed (${4 - retries} of 3):`, error);
          
          if (retries > 0) {
            // Wait before retry with exponential backoff
            await new Promise(resolve => setTimeout(resolve, (4 - retries) * 1000));
            await sendWithRetry(retries - 1);
          } else {
            throw error;
          }
        }
      };

      await sendWithRetry();

    } catch (error) {
      console.error("Error sending message after retries:", error);
      setIsLoading(false);
      setConnectionError('Failed to send message. Please check your connection and try again.');
      
      // Add error message
      const errorMessage: ChatMessage = {
        role: "assistant",
        content: "Sorry, I couldn't send your message due to a connection issue. Please try again.",
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    }
  };

  // Handle suggestion card highlighting
  const handleSuggestionHighlight = (suggestion: Suggestion) => {
    console.log('🖱️ Clicking suggestion card for highlighting:', suggestion);
    
    if (!editorRef?.current) {
      console.error('❌ Editor instance not available');
      return;
    }

    // Clear previous highlight timeout
    if (highlightTimeoutRef.current) {
      clearTimeout(highlightTimeoutRef.current);
      highlightTimeoutRef.current = null;
    }

    // Clear existing highlights
    editorRef.current.chain().clearTemporaryHighlights().run();

    // Find text in document
    const { state } = editorRef.current;
    const searchText = suggestion.original_text;
    
    if (!searchText || !searchText.trim()) {
      console.warn('⚠️ No original text available for highlighting');
      return;
    }

    console.log('🔍 Searching for text:', searchText.substring(0, 50) + '...');
    
    try {
      const textPosition = findTextInDocument(state.doc, searchText);
      
      if (textPosition) {
        console.log('✅ Text found at position:', textPosition);
        
        // Apply temporary highlight with severity-based styling
        const severityClass = suggestion.severity || 'medium';
        editorRef.current
          .chain()
          .addTemporaryHighlight(textPosition.from, textPosition.to, severityClass)
          .run();
        
        // Scroll to the highlighted text
        editorRef.current
          .chain()
          .focus()
          .setTextSelection(textPosition.from)
          .scrollIntoView()
          .run();
        
        // Set highlighted state
        setHighlightedCardId(suggestion.id);
        
        // Auto-clear highlight after 5 seconds
        highlightTimeoutRef.current = window.setTimeout(() => {
          editorRef.current?.chain().clearTemporaryHighlights().run();
          setHighlightedCardId(null);
          highlightTimeoutRef.current = null;
        }, 5000);
        
        console.log('🎯 Text highlighted and scrolled into view successfully');
      } else {
        console.warn('⚠️ Text not found in document');
        
        // Try alternative search with partial matching
        console.log('🔄 Attempting fuzzy text search...');
        const trimmedSearch = searchText.trim().substring(0, 30);
        const fallbackPosition = findTextInDocument(state.doc, trimmedSearch);
        
        if (fallbackPosition) {
          console.log('✅ Fallback text found at position:', fallbackPosition);
          editorRef.current
            .chain()
            .addTemporaryHighlight(fallbackPosition.from, fallbackPosition.to, 'medium')
            .run();
          
          // Scroll to the highlighted text
          editorRef.current
            .chain()
            .focus()
            .setTextSelection(fallbackPosition.from)
            .scrollIntoView()
            .run();
          
          setHighlightedCardId(suggestion.id);
          
          highlightTimeoutRef.current = window.setTimeout(() => {
            editorRef.current?.chain().clearTemporaryHighlights().run();
            setHighlightedCardId(null);
            highlightTimeoutRef.current = null;
          }, 5000);
        } else {
          console.error('❌ Text highlighting failed - text not found');
        }
      }
    } catch (error) {
      console.error('❌ Error during text highlighting:', error);
    }
  };

  // Handle suggestion card actions
  const handleSuggestionAccept = async (cardId: string) => {
    console.log('Accepting suggestion:', cardId);
    
    // Find the suggestion data
    const allSuggestions = messages.flatMap(msg => msg.suggestions || []);
    const suggestion = allSuggestions.find(s => s.id === cardId);
    
    if (!suggestion) {
      console.error('❌ Suggestion not found:', cardId);
      // Show error message to user
      const errorMessage: ChatMessage = {
        role: "assistant",
        content: "Error: Could not find suggestion to accept. Please try again.",
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
      return;
    }

    // Replace text in the document using editor
    if (editorRef?.current && suggestion.original_text && suggestion.replace_to) {
      console.log('🔄 Replacing text in document...');
      console.log('Original:', suggestion.original_text.substring(0, 50) + '...');
      console.log('Replace with:', suggestion.replace_to.substring(0, 50) + '...');
      
      try {
        const success = replaceText(editorRef.current, suggestion.original_text, suggestion.replace_to);
        
        if (success) {
          console.log('✅ Text replacement successful');
          
          // Clear any existing highlights
          if (highlightTimeoutRef.current) {
            clearTimeout(highlightTimeoutRef.current);
            highlightTimeoutRef.current = null;
          }
          editorRef.current.chain().clearTemporaryHighlights().run();
          setHighlightedCardId(null);
          
        } else {
          console.warn('⚠️ Text replacement failed - text not found');
          
          // Try partial replacement as fallback
          const trimmedOriginal = suggestion.original_text.trim().substring(0, 30);
          const fallbackSuccess = replaceText(editorRef.current, trimmedOriginal, suggestion.replace_to);
          
          if (fallbackSuccess) {
            console.log('✅ Fallback text replacement successful');
          } else {
            console.error('❌ Both exact and fallback text replacement failed');
            // Still proceed with removing the card since user clicked accept
          }
        }
      } catch (error) {
        console.error('❌ Error during text replacement:', error);
        // Show error message to user
        const errorMessage: ChatMessage = {
          role: "assistant",
          content: "Error: Failed to apply suggestion to document. Please try applying manually.",
          timestamp: new Date()
        };
        setMessages(prev => [...prev, errorMessage]);
      }
    } else {
      console.error('❌ Missing editor ref or suggestion text data');
      // Show error message to user
      const errorMessage: ChatMessage = {
        role: "assistant",
        content: "Error: Editor not ready or suggestion data missing. Please try again.",
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    }
    
    // Find the message containing this card for API call
    const messageWithCard = messages.find(msg => 
      msg.suggestions?.some(s => s.id === cardId)
    );
    
    if (messageWithCard && messageWithCard.id && documentId && documentVersion) {
      try {
        // Use actual database message ID
        const messageId = messageWithCard.id;
        
        // Call API to mark card as accepted
        const response = await fetch(
          `http://localhost:8000/api/chat/suggestion-action/${documentId}/${documentVersion}/${messageId}?card_id=${cardId}&action=accepted`,
          { method: 'POST' }
        );
        
        if (response.ok) {
          console.log('✅ Suggestion marked as accepted in database');
          // Remove the suggestion card from messages (optimistic update after successful DB update)
          setMessages(prev => 
            prev.map(msg => ({
              ...msg,
              suggestions: msg.suggestions?.filter(s => s.id !== cardId)
            })).filter(msg => 
              // Keep summary messages always, only filter empty suggestion_cards
              msg.type === 'suggestion_summary' || 
              msg.type !== 'suggestion_cards' || 
              (msg.suggestions && msg.suggestions.length > 0)
            )
          );
        } else {
          console.error('Failed to update suggestion status in database');
          // Show error message if database update fails
          const errorMessage: ChatMessage = {
            role: "assistant",
            content: "Error: Failed to save suggestion status. The suggestion may reappear when you reload.",
            timestamp: new Date()
          };
          setMessages(prev => [...prev, errorMessage]);
        }
      } catch (error) {
        console.error('Failed to mark suggestion as accepted:', error);
        // Show error message on network failure
        const errorMessage: ChatMessage = {
          role: "assistant",
          content: "Error: Network error while saving suggestion status. Please try again.",
          timestamp: new Date()
        };
        setMessages(prev => [...prev, errorMessage]);
      }
    } else {
      // Still remove from UI even if we can't update database (for UX)
      console.warn('No message ID available, performing local-only removal');
      setMessages(prev => 
        prev.map(msg => ({
          ...msg,
          suggestions: msg.suggestions?.filter(s => s.id !== cardId)
        })).filter(msg => 
          // Keep summary messages always, only filter empty suggestion_cards
          msg.type === 'suggestion_summary' || 
          msg.type !== 'suggestion_cards' || 
          (msg.suggestions && msg.suggestions.length > 0)
        )
      );
    }
  };

  const handleSuggestionDismiss = async (cardId: string) => {
    console.log('Dismissing suggestion:', cardId);
    
    // Find the message containing this card to get message ID
    const messageWithCard = messages.find(msg => 
      msg.suggestions?.some(s => s.id === cardId)
    );
    
    if (messageWithCard && messageWithCard.id && documentId && documentVersion) {
      try {
        // Use actual database message ID
        const messageId = messageWithCard.id;
        
        // Call API to mark card as dismissed
        const response = await fetch(
          `http://localhost:8000/api/chat/suggestion-action/${documentId}/${documentVersion}/${messageId}?card_id=${cardId}&action=dismissed`,
          { method: 'POST' }
        );
        
        if (response.ok) {
          console.log('✅ Suggestion dismissed successfully');
          // Remove the suggestion card from messages (optimistic update after successful DB update)
          setMessages(prev => 
            prev.map(msg => ({
              ...msg,
              suggestions: msg.suggestions?.filter(s => s.id !== cardId)
            })).filter(msg => 
              // Keep summary messages always, only filter empty suggestion_cards
              msg.type === 'suggestion_summary' || 
              msg.type !== 'suggestion_cards' || 
              (msg.suggestions && msg.suggestions.length > 0)
            )
          );
        } else {
          console.error('Failed to update suggestion status in database');
          // Show error message if database update fails
          const errorMessage: ChatMessage = {
            role: "assistant",
            content: "Error: Failed to save dismiss status. The suggestion may reappear when you reload.",
            timestamp: new Date()
          };
          setMessages(prev => [...prev, errorMessage]);
        }
      } catch (error) {
        console.error('Failed to dismiss suggestion:', error);
        // Show error message on network failure
        const errorMessage: ChatMessage = {
          role: "assistant",
          content: "Error: Network error while saving dismiss status. Please try again.",
          timestamp: new Date()
        };
        setMessages(prev => [...prev, errorMessage]);
      }
    } else {
      // Still remove from UI even if we can't update database (for UX)
      console.warn('No message ID available, performing local-only removal');
      setMessages(prev => 
        prev.map(msg => ({
          ...msg,
          suggestions: msg.suggestions?.filter(s => s.id !== cardId)
        })).filter(msg => 
          // Keep summary messages always, only filter empty suggestion_cards
          msg.type === 'suggestion_summary' || 
          msg.type !== 'suggestion_cards' || 
          (msg.suggestions && msg.suggestions.length > 0)
        )
      );
    }
  };

  const handleSuggestionCopy = async (cardId: string) => {
    console.log('Copying suggestion:', cardId);
    const allSuggestions = messages.flatMap(msg => msg.suggestions || []);
    const suggestion = allSuggestions.find(s => s.id === cardId);
    
    if (suggestion) {
      try {
        await navigator.clipboard.writeText(suggestion.replace_to);
        console.log('✅ Suggestion copied to clipboard');
        // Show success message to user
        const successMessage: ChatMessage = {
          role: "assistant",
          content: "✅ Suggestion copied to clipboard successfully!",
          timestamp: new Date()
        };
        setMessages(prev => [...prev, successMessage]);
      } catch (error) {
        console.error('Failed to copy suggestion:', error);
        // Show error message to user
        const errorMessage: ChatMessage = {
          role: "assistant",
          content: "Error: Failed to copy suggestion to clipboard. Please copy manually.",
          timestamp: new Date()
        };
        setMessages(prev => [...prev, errorMessage]);
      }
    }
  };

  // Handle Enter key for sending
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };



  // Get connection status display
  const getConnectionStatus = () => {
    switch (readyState) {
      case ReadyState.CONNECTING:
        return { text: "Connecting...", color: "text-yellow-600", bgColor: "bg-yellow-100" };
      case ReadyState.OPEN:
        return { text: "Connected", color: "text-green-600", bgColor: "bg-green-100" };
      case ReadyState.CLOSING:
        return { text: "Disconnecting...", color: "text-orange-600", bgColor: "bg-orange-100" };
      case ReadyState.CLOSED:
        return { text: "Disconnected", color: "text-red-600", bgColor: "bg-red-100" };
      default:
        return { text: "Unknown", color: "text-gray-600", bgColor: "bg-gray-100" };
    }
  };

  const connectionStatus = getConnectionStatus();

  return (
    <div className={`flex flex-col h-full bg-white rounded-lg shadow-sm relative ${className}`}>
      {/* Connection status bar */}
      {(connectionError || readyState !== ReadyState.OPEN) && (
        <div className={`px-4 py-2 text-xs border-b ${connectionStatus.bgColor}`}>
          <div className="flex items-center justify-between">
            <span className={`flex items-center ${connectionStatus.color}`}>
              <div className={`w-2 h-2 rounded-full mr-2 ${
                readyState === ReadyState.OPEN ? 'bg-green-400' : 
                readyState === ReadyState.CONNECTING ? 'bg-yellow-400 animate-pulse' : 'bg-red-400'
              }`}></div>
              {connectionError || connectionStatus.text}
            </span>
            {connectionError && readyState === ReadyState.CLOSED && (
              <button
                onClick={() => window.location.reload()}
                className="text-xs px-2 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Refresh Page
              </button>
            )}
          </div>
        </div>
      )}

      {/* Message list */}
      <div className="flex-1 overflow-y-auto p-4 pb-24 space-y-3">
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
              className={`${msg.role === "user" ? "ml-auto max-w-[90%]" : msg.type === "suggestion_cards" ? "mr-auto max-w-[98%]" : "mr-auto max-w-[90%]"}`}
            >
              {msg.role === "user" ? (
                // User message
                <div className="flex items-start gap-2 justify-end">
                  <div className="bg-blue-100 text-blue-800 rounded-lg px-4 py-2">
                    <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                  </div>
                  <div className="w-8 h-8 rounded-full bg-purple-100 flex items-center justify-center flex-shrink-0">
                    <span className="text-lg">👽</span>
                  </div>
                </div>
              ) : (
                // Assistant message
                <div className="space-y-3">
                  {msg.type === "suggestion_summary" ? (
                    // Summary message (always visible)
                    <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                      <div className="text-sm text-green-800">
                        <ReactMarkdown>
                          {msg.content}
                        </ReactMarkdown>
                      </div>
                    </div>
                  ) : msg.type === "suggestion_cards" && msg.suggestions && msg.suggestions.length > 0 ? (
                    // Suggestion cards
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                      <InlineSuggestionCard 
                        suggestions={msg.suggestions}
                        onAccept={handleSuggestionAccept}
                        onDismiss={handleSuggestionDismiss}
                        onCopy={handleSuggestionCopy}
                        onHighlight={handleSuggestionHighlight}
                        highlightedCardId={highlightedCardId || undefined}
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

        {isLoading && currentProcessingStage && (
          <div className="mr-auto max-w-[90%]">
            <ProcessingStages 
              currentStage={currentProcessingStage}
              allStages={allProcessingStages}
              className="max-w-lg"
            />
          </div>
        )}
        
        {isLoading && !currentProcessingStage && (
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

      {/* Floating input area */}
      <div className="absolute bottom-4 left-4 right-4">
        <div className="bg-white rounded-full shadow-lg border-t border-gray-100 px-2 py-3 flex items-center gap-3">
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              connectionError ? "Connection error - check network" :
              readyState === ReadyState.OPEN ? "Ask any question..." : 
              readyState === ReadyState.CONNECTING ? "Connecting..." :
              "Not connected"
            }
            className="flex-1 text-sm placeholder-gray-400 bg-transparent focus:outline-none border-none focus:ring-0 focus:border-transparent"
            style={{ 
              border: 'none', 
              outline: 'none', 
              boxShadow: 'none',
              background: 'transparent',
              WebkitAppearance: 'none',
              MozAppearance: 'none',
              appearance: 'none'
            }}
            disabled={isLoading || (readyState !== ReadyState.OPEN && readyState !== ReadyState.CONNECTING)}
          />
          <button
            onClick={sendMessage}
            disabled={!inputMessage.trim() || isLoading || readyState !== ReadyState.OPEN}
            className={`w-10 h-10 rounded-full flex items-center justify-center transition-colors ${
              !inputMessage.trim() || isLoading || readyState !== ReadyState.OPEN
                ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                : 'bg-red-500 text-white hover:bg-red-600'
            }`}
            style={{ borderRadius: '50%' }}
          >
            {isLoading ? (
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
            ) : (
              <svg className="w-5 h-5 transform rotate-90" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}