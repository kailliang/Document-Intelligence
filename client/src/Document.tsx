import Editor from "./internal/Editor";
import useWebSocket from "react-use-websocket";
import { useCallback, useEffect, useState } from "react";

// TypeScript interfaces for AI suggestions
interface AISuggestion {
  type: string;
  severity: 'high' | 'medium' | 'low';
  paragraph: number;
  description: string;
  text?: string;  // 新增：精确的原始文本
  suggestion: string;
}

interface AIResponse {
  issues: AISuggestion[];
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
  onAISuggestions?: (suggestions: AISuggestion[]) => void;  // AI建议回调
  onProcessingStatus?: (isProcessing: boolean, message?: string) => void;  // 处理状态回调
  onManualAnalysis?: (analysisFunction: () => void) => void;  // 注册手动分析函数的回调
}

const SOCKET_URL = "ws://localhost:8000/ws";

export default function Document({ 
  onContentChange, 
  content, 
  onAISuggestions,
  onProcessingStatus,
  onManualAnalysis
}: DocumentProps) {
  const [isAIProcessing, setIsAIProcessing] = useState(false);
  const [lastAnalyzedContent, setLastAnalyzedContent] = useState<string>("");

  const { sendMessage, lastMessage, readyState } = useWebSocket(SOCKET_URL, {
    onOpen: () => {
      console.log("🔌 WebSocket Connected");
      onProcessingStatus?.(false, "AI助手已连接");
    },
    onClose: () => {
      console.log("🔌 WebSocket Disconnected");
      onProcessingStatus?.(false, "AI助手已断开连接");
    },
    shouldReconnect: (_closeEvent) => true,
    // 配置重连策略
    reconnectAttempts: 5,
    reconnectInterval: 3000,
  });

  useEffect(() => {
    if (lastMessage !== null) {
      // 移除messageHistory更新，防止无限循环
      
      try {
        // 解析WebSocket消息
        const message: WebSocketMessage = JSON.parse(lastMessage.data);
        console.log("📨 收到AI消息:", message);
        
        // 根据消息类型处理
        switch (message.type) {
          case 'processing_start':
            console.log("🤖 AI开始处理文档");
            setIsAIProcessing(true);
            onProcessingStatus?.(true, message.message || "AI正在分析文档...");
            break;
            
          case 'ai_suggestions':
            console.log("✨ 收到AI建议:", message.data);
            setIsAIProcessing(false);
            if (message.data?.issues) {
              onAISuggestions?.(message.data.issues);
              onProcessingStatus?.(false, `AI分析完成，发现${message.data.issues.length}个建议`);
            }
            break;
            
          case 'validation_error':
            console.warn("⚠️ 文档验证错误:", message.message);
            setIsAIProcessing(false);
            onProcessingStatus?.(false, `验证错误: ${message.message}`);
            break;
            
          case 'ai_error':
            console.error("❌ AI服务错误:", message.message);
            setIsAIProcessing(false);
            onProcessingStatus?.(false, `AI错误: ${message.message}`);
            break;
            
          case 'server_error':
            console.error("❌ 服务器错误:", message.message, message.details);
            setIsAIProcessing(false);
            // 显示更友好的错误消息
            if (message.message?.includes('OPENAI_API_KEY')) {
              onProcessingStatus?.(false, "⚠️ AI服务未配置，请联系管理员");
            } else {
              onProcessingStatus?.(false, `服务器错误: ${message.message}`);
            }
            break;
            
          case 'status':
            console.log("ℹ️ 状态消息:", message.message);
            onProcessingStatus?.(false, message.message || "");
            break;
            
          case 'connection_success':
            console.log("✅ AI服务连接成功:", message.message);
            onProcessingStatus?.(false, message.message || "AI服务已就绪");
            break;
            
          default:
            console.log("📝 未知消息类型:", message);
        }
        
      } catch (error) {
        console.error("❌ 解析WebSocket消息失败:", error, lastMessage.data);
      }
    }
  }, [lastMessage, onAISuggestions, onProcessingStatus]);

  // 手动触发AI分析
  const triggerManualAnalysis = useCallback(() => {
    // 检查WebSocket连接状态和处理状态
    // readyState: 0=CONNECTING, 1=OPEN, 2=CLOSING, 3=CLOSED
    if (readyState !== 1) {
      console.warn("⚠️ WebSocket未连接，无法进行AI分析，状态:", readyState);
      onProcessingStatus?.(false, "AI助手未连接");
      return;
    }
    
    if (isAIProcessing) {
      console.log("⏳ AI正在处理中，跳过新请求");
      onProcessingStatus?.(false, "AI正在处理中，请稍候...");
      return;
    }
    
    if (!content.trim()) {
      console.log("📄 文档内容为空，跳过AI分析");
      onProcessingStatus?.(false, "文档内容为空");
      return;
    }
    
    console.log("📤 手动触发AI分析，内容长度:", content.length);
    setLastAnalyzedContent(content); // 记录已分析的内容
    sendMessage(content);
  }, [content, readyState, isAIProcessing, sendMessage, onProcessingStatus]);

  // 注册手动分析函数
  useEffect(() => {
    if (onManualAnalysis) {
      onManualAnalysis(triggerManualAnalysis);
    }
  }, [triggerManualAnalysis, onManualAnalysis]);

  const handleEditorChange = (content: string) => {
    onContentChange(content);
    // 移除自动AI分析：sendEditorContent(content);
  };

  // 移除自动AI分析功能
  // useEffect(() => {
  //   console.log("📊 文档状态:", { 
  //     hasContent: !!content, 
  //     contentLength: content?.length,
  //     readyState, 
  //     isAIProcessing,
  //     isAIEnabled
  //   });
  //   
  //   // 只有在AI开启时才自动分析
  //   if (isAIEnabled && content && readyState === 1 && !isAIProcessing && content !== lastAnalyzedContent) {
  //     console.log("📄 AI开启，立即分析文档内容");
  //     sendEditorContent(content);
  //   }
  // }, [content, readyState, isAIProcessing, sendEditorContent, lastAnalyzedContent, isAIEnabled]);

  return (
    <div className="w-full h-full flex flex-col">
      {/* 编辑器容器 - 使用flex-1和overflow-y-auto实现正确滚动 */}
      <div className="flex-1 overflow-y-auto p-4">
        <Editor handleEditorChange={handleEditorChange} content={content} />
      </div>
      
      {/* 调试信息 - 可选显示 */}
      {import.meta.env.DEV && (
        <div className="fixed bottom-20 left-4 bg-black bg-opacity-75 text-white text-xs p-2 rounded z-50">
          WebSocket: {readyState === 1 ? 'Open' : `State:${readyState}`} | AI处理: {isAIProcessing ? '进行中' : '空闲'}
        </div>
      )}
    </div>
  );
}
