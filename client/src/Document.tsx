import Editor from "./internal/Editor";
import useWebSocket, { ReadyState } from "react-use-websocket";
import { useCallback, useEffect, useState, useRef } from "react";

// TypeScript interfaces for AI suggestions
interface AISuggestion {
  type: string;
  severity: 'high' | 'medium' | 'low';
  paragraph: number;
  description: string;
  text?: string;  // Added: precise original text
  suggestion: string;
  originalText?: string;  // Added: original text (for precise matching)
  replaceTo?: string;     // Added: suggested replacement text
}

interface DiagramInsertion {
  insert_after_text: string;
  mermaid_syntax: string;
  diagram_type: string;
  title?: string;
}

interface AIResponse {
  issues: AISuggestion[];
  diagram_insertions?: DiagramInsertion[];
}

interface WebSocketMessage {
  type: 'ai_suggestions' | 'processing_start' | 'validation_error' | 'ai_error' | 'server_error' | 'status' | 'connection_success';
  message?: string;
  data?: AIResponse;
  timestamp?: string;
  details?: string;
}

export interface DocumentProps {
  onContentChange: (content: string) => void;
  content: string;
  onAISuggestions?: (suggestions: AISuggestion[]) => void;  // AI suggestions callback
  onProcessingStatus?: (isProcessing: boolean, message?: string) => void;  // Processing status callback
  onManualAnalysis?: (analysisFunction: () => void) => void;  // Register manual analysis function callback
  onEditorReady?: (editor: any) => void;  // Added: editor instance callback
  onDiagramInsertions?: (insertions: DiagramInsertion[]) => void;  // Added: diagram insertion callback
}

// Use enhanced WebSocket endpoint (supports Function Calling)
const SOCKET_URL = import.meta.env.VITE_USE_ENHANCED_WS === 'true' 
  ? "ws://localhost:8000/ws/enhanced"
  : "ws://localhost:8000/ws";

export default function Document({ 
  onContentChange, 
  content, 
  onAISuggestions,
  onProcessingStatus,
  onManualAnalysis,
  onEditorReady,
  onDiagramInsertions
}: DocumentProps) {
  const [isAIProcessing, setIsAIProcessing] = useState(false);
  
  // Add editor instance reference
  const editorRef = useRef<any>(null);

  const { sendMessage, lastMessage, readyState } = useWebSocket(SOCKET_URL, {
    onOpen: () => {
      console.log("🔌 WebSocket Connected to:", SOCKET_URL);
      onProcessingStatus?.(false, "AI assistant connected");
    },
    onClose: () => {
      console.log("🔌 WebSocket Disconnected");
      onProcessingStatus?.(false, "AI assistant disconnected");
    },
    shouldReconnect: (_closeEvent) => true,
    // Configure reconnection strategy
    reconnectAttempts: 5,
    reconnectInterval: 3000,
    // Share WebSocket connection, prevent multiple instances
    share: true
  });


  useEffect(() => {
    if (lastMessage !== null) {
      // Remove messageHistory updates to prevent infinite loops
      
      try {
        // Parse WebSocket message
        const message: WebSocketMessage = JSON.parse(lastMessage.data);
        console.log("📨 Received AI message:", message);
        
        // Handle based on message type
        switch (message.type) {
          case 'processing_start':
            console.log("🤖 AI started processing document");
            setIsAIProcessing(true);
            onProcessingStatus?.(true, message.message || "AI is analysing document...");
            break;
            
          case 'ai_suggestions':
            console.log("✨ Received AI suggestions:", message.data);
            setIsAIProcessing(false);
            if (message.data?.issues) {
              onAISuggestions?.(message.data.issues);
              let statusMessage = `AI analysis complete, found ${message.data.issues.length} suggestions`;
              
              // Handle diagram insertions
              if (message.data?.diagram_insertions && message.data.diagram_insertions.length > 0) {
                console.log("📊 Received diagram insertion requests:", message.data.diagram_insertions);
                onDiagramInsertions?.(message.data.diagram_insertions);
                statusMessage += `, ${message.data.diagram_insertions.length} diagram insertions`;
              }
              
              onProcessingStatus?.(false, statusMessage);
            }
            break;
            
          case 'validation_error':
            console.warn("⚠️ Document validation error:", message.message);
            setIsAIProcessing(false);
            onProcessingStatus?.(false, `Validation error: ${message.message}`);
            break;
            
          case 'ai_error':
            console.error("❌ AI service error:", message.message);
            setIsAIProcessing(false);
            onProcessingStatus?.(false, `AI error: ${message.message}`);
            break;
            
          case 'server_error':
            console.error("❌ Server error:", message.message, message.details);
            setIsAIProcessing(false);
            // Display more user-friendly error message
            if (message.message?.includes('OPENAI_API_KEY')) {
              onProcessingStatus?.(false, "⚠️ AI service not configured, please contact administrator");
            } else {
              onProcessingStatus?.(false, `Server error: ${message.message}`);
            }
            break;
            
          case 'status':
            console.log("ℹ️ Status message:", message.message);
            onProcessingStatus?.(false, message.message || "");
            break;
            
          case 'connection_success':
            console.log("✅ AI service connected successfully:", message.message);
            // Slight delay to ensure WebSocket is fully ready
            setTimeout(() => {
              onProcessingStatus?.(false, message.message || "AI service ready");
            }, 500);
            break;
            
          default:
            console.log("📝 Unknown message type:", message);
        }
        
      } catch (error) {
        console.error("❌ Failed to parse WebSocket message:", error, lastMessage.data);
      }
    }
  }, [lastMessage, onAISuggestions, onProcessingStatus]);

  // Manually trigger AI analysis
  const triggerManualAnalysis = useCallback(() => {
    console.log("🔍 Triggering AI analysis, WebSocket state:", readyState);
    
    // Get latest content from editor or fallback to props
    const currentContent = editorRef?.current?.getHTML() || content;
    
    
    // Check WebSocket connection state
    if (readyState === ReadyState.CLOSED || readyState === ReadyState.CLOSING) {
      onProcessingStatus?.(false, "AI assistant connection lost, please refresh page");
      return;
    }
    
    if (isAIProcessing) {
      onProcessingStatus?.(false, "AI is analysing, please wait...");
      return;
    }
    
    if (!currentContent.trim()) {
      onProcessingStatus?.(false, "Document content is empty");
      return;
    }
    
    
    try {
      onProcessingStatus?.(true, "Sending analysis request...");
      sendMessage(currentContent);
      onProcessingStatus?.(true, "AI is analysing document...");
      
    } catch (error) {
      console.error("❌ Failed to send AI analysis request:", error);
      onProcessingStatus?.(false, `Request failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }, [isAIProcessing, sendMessage, onProcessingStatus, readyState]);
  
  // Handle editor instance ready
  const handleEditorReady = useCallback((editor: any) => {
    editorRef.current = editor;
    onEditorReady?.(editor);
  }, [onEditorReady]);

  // Register manual analysis function
  useEffect(() => {
    onManualAnalysis?.(triggerManualAnalysis);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [onManualAnalysis]);

  const handleEditorChange = (content: string) => {
    onContentChange(content);
  };


  return (
    <div className="w-full h-full flex flex-col">
      {/* Editor container - use flex-1 and overflow-y-auto for proper scrolling */}
      <div className="flex-1 overflow-y-auto p-4">
        <Editor 
          handleEditorChange={handleEditorChange} 
          content={content} 
          onEditorReady={handleEditorReady}
        />
      </div>
      
    </div>
  );
}
