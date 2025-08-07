import { useState, useRef, useEffect } from "react";
import axios from "axios";
import ReactMarkdown from "react-markdown";
import mermaid from "mermaid";
mermaid.initialize({ startOnLoad: true, theme: 'default' });
interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp?: Date;
}

interface DiagramInsertion {
  insert_after_text: string;
  mermaid_syntax: string;
  diagram_type: string;
  title?: string;
}

interface ChatPanelProps {
  className?: string;
  getCurrentDocumentContent?: () => string;  // Added: callback to get current document content
  onDiagramInsertions?: (insertions: DiagramInsertion[]) => void;  // Added: diagram insertion callback
  onInsertMermaid?: (mermaidSyntax: string, title?: string) => void;  // Added: mermaid diagram insertion callback
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
        
        // Render Mermaid chart
        const { svg } = await mermaid.render(uniqueId, chart);
        
        if (ref.current && svg) {
          ref.current.innerHTML = svg;
          setIsRendered(true);
        }
      } catch (error) {
        console.error('Mermaid rendering failed:', error);
        if (ref.current) {
          ref.current.innerHTML = '<div class="text-red-500 text-sm p-2 border border-red-300 rounded bg-red-50">⚠️ Chart rendering failed, please check syntax</div>';
          setIsRendered(true); // Show error message
        }
      }
    };
    
    // Add small delay to ensure DOM is ready
    const timeoutId = setTimeout(renderMermaid, 10);
    
    return () => clearTimeout(timeoutId);
  }, [chart])
  // useEffect(() => {
  //   if (ref.current) {
  //     // ref.current.innerHTML = chart;

  //     //mermaid.contentLoaded();
  //   }
  // }, [chart]);

  const handleInsert = () => {
    if (onInsert) {
      onInsert(chart); // Pass the original mermaid syntax, not rendered SVG
    }
  };

  return <div>
    <div ref={ref} className="mermaid my-4" />
    {!isRendered && (
      <div className="text-gray-500 text-sm p-2">
        Rendering chart...
      </div>
    )}
    {isRendered && (
      <div>
        <button
          onClick={handleInsert}
          className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
        >
          Insert
        </button>
      </div>
    )}
  </div>;
}

export default function ChatPanel({ className, getCurrentDocumentContent, onDiagramInsertions, onInsertMermaid }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Re-initialize Mermaid to fix rendering issues
  useEffect(() => {
    const reinitializeMermaid = () => {
      mermaid.initialize({ 
        startOnLoad: true, 
        theme: 'default',
        securityLevel: 'loose'
      });
    };
    
    // Listen for document save events
    const handleDocumentSave = () => {
      setTimeout(() => {
        reinitializeMermaid();
        // Force re-render all Mermaid charts
        const mermaidElements = document.querySelectorAll('.mermaid');
        mermaidElements.forEach((element) => {
          if (element.innerHTML) {
            const content = element.getAttribute('data-chart');
            if (content) {
              element.innerHTML = content;
            }
          }
        });
      }, 100);
    };

    // Register event listener (if needed)
    window.addEventListener('document-saved', handleDocumentSave);
    
    return () => {
      window.removeEventListener('document-saved', handleDocumentSave);
    };
  }, []);

  // Send message
  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      role: "user",
      content: inputMessage,
      timestamp: new Date()
    };

    // Add user message
    setMessages(prev => [...prev, userMessage]);
    setInputMessage("");
    setIsLoading(true);

    try {
      // Build message history
      const messageHistory = [...messages, userMessage];

      // Get current document content
      const currentDocumentContent = getCurrentDocumentContent ? getCurrentDocumentContent() : "";

      // Call API with current document content
      const response = await axios.post("http://localhost:8000/api/chat", {
        messages: messageHistory.map(({ role, content }) => ({ role, content })),
        current_document_content: currentDocumentContent
      });

      // Add AI response
      const assistantMessage: ChatMessage = {
        role: "assistant",
        content: response.data.response,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, assistantMessage]);

      // Handle diagram insertion
      if (response.data.diagram_insertions && response.data.diagram_insertions.length > 0) {
        console.log("📊 Chat received diagram insertion request:", response.data.diagram_insertions);
        console.log("📊 onDiagramInsertions callback exists:", !!onDiagramInsertions);
        if (onDiagramInsertions) {
          console.log("📊 Calling diagram insertion callback...");
          onDiagramInsertions(response.data.diagram_insertions);
          console.log("📊 Diagram insertion callback called");
        } else {
          console.error("❌ Diagram insertion callback does not exist, cannot insert charts into document");
        }
      } else {
        console.log("📊 No diagram insertion data in AI response");
        console.log("📊 Full response:", response.data);
      }
    } catch (error) {
      console.error("Chat error:", error);

      // Add error message
      const errorMessage: ChatMessage = {
        role: "assistant",
        content: "Sorry, an error occurred. Please try again later.",
        timestamp: new Date()
      };

      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle Enter key sending
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className={`flex flex-col h-full bg-white rounded-lg shadow-sm ${className}`}>
      {/* Chat title */}
      <div className="px-4 py-3 border-b">
        <p className="text-xs text-gray-500" style={{ marginBottom: '0px' }}>Ask patent-related questions or request diagram generation</p>
      </div>

      {/* Message list */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            <p className="text-sm">Start a conversation, ask any patent-related questions</p>
            <div className="mt-4 space-y-2 text-xs text-gray-400">
              <p>Try these questions:</p>
              <p className="italic">"How to write a good patent claim?"</p>
              <p className="italic">"Help me generate a patent process flowchart"</p>
              <p className="italic">"Please generate a diagram based on the description provided."</p>
            </div>
          </div>
        ) : (
          messages.map((msg, index) => (
            <div
              key={index}
              className={`${msg.role === "user" ? "ml-auto" : "mr-auto"
                } max-w-[80%]`}
            >
              <div
                className={`rounded-lg px-4 py-2 ${msg.role === "user"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-800"
                  }`}
              >
                {msg.role === "user" ? (
                  <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                ) : (
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
                )}
              </div>
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
            placeholder="Enter message..."
            className="flex-1 px-3 py-2 border rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
            rows={1}
            disabled={isLoading}
            style={{ height: '5rem' }}
          />
          <button
            onClick={sendMessage}
            disabled={!inputMessage.trim() || isLoading}
            style={{
              position: 'absolute',
              bottom: '0.5rem',
              right: '0.5rem',
              borderRadius: '50%',
              height: '2.5rem',
              width: '2.5rem',
            }}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${!inputMessage.trim() || isLoading
              ? "bg-gray-300 text-gray-500 cursor-not-allowed"
              : "bg-blue-600 text-white hover:bg-blue-700"
              }`}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}