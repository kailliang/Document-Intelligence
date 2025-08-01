import Editor from "./internal/Editor";
import useWebSocket, { ReadyState } from "react-use-websocket";
import { useCallback, useEffect, useState, useRef } from "react";

// TypeScript interfaces for AI suggestions
interface AISuggestion {
  type: string;
  severity: 'high' | 'medium' | 'low';
  paragraph: number;
  description: string;
  text?: string;  // 新增：精确的原始文本
  suggestion: string;
  originalText?: string;  // 新增：原始文本（用于精确匹配）
  replaceTo?: string;     // 新增：建议替换的文本
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
  onEditorReady?: (editor: any) => void;  // 新增：编辑器实例回调
}

// 使用增强版WebSocket端点（支持Function Calling）
const SOCKET_URL = import.meta.env.VITE_USE_ENHANCED_WS === 'true' 
  ? "ws://localhost:8000/ws/enhanced"
  : "ws://localhost:8000/ws";

export default function Document({ 
  onContentChange, 
  content, 
  onAISuggestions,
  onProcessingStatus,
  onManualAnalysis,
  onEditorReady
}: DocumentProps) {
  const [isAIProcessing, setIsAIProcessing] = useState(false);
  // const [lastAnalyzedContent, setLastAnalyzedContent] = useState<string>("");  // 暂时注释，将来可能需要
  const [isWebSocketReady, setIsWebSocketReady] = useState(false);
  
  // 添加编辑器实例引用
  const editorRef = useRef<any>(null);

  const { sendMessage, lastMessage, readyState } = useWebSocket(SOCKET_URL, {
    onOpen: () => {
      console.log("🔌 WebSocket Connected to:", SOCKET_URL);
      setIsWebSocketReady(true);
      onProcessingStatus?.(false, "AI助手已连接");
    },
    onClose: () => {
      console.log("🔌 WebSocket Disconnected");
      setIsWebSocketReady(false);
      onProcessingStatus?.(false, "AI助手已断开连接");
    },
    shouldReconnect: (_closeEvent) => true,
    // 配置重连策略
    reconnectAttempts: 5,
    reconnectInterval: 3000,
    // 共享WebSocket连接，防止多个实例
    share: true
  });

  // 检查WebSocket是否可以发送消息（更宽松的检查）
  const isSocketActuallyReady = useCallback(() => {
    // 允许在CONNECTING状态也尝试发送，因为可能已经可用
    return isWebSocketReady && (readyState === ReadyState.OPEN || readyState === ReadyState.CONNECTING);
  }, [isWebSocketReady, readyState]);

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
            // 稍微延迟一下确保WebSocket完全就绪
            setTimeout(() => {
              setIsWebSocketReady(true);
              onProcessingStatus?.(false, message.message || "AI服务已就绪");
            }, 500);
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
    console.log("🔍 触发分析时的调试信息:", {
      readyState,
      isWebSocketReady,
      ReadyStateEnum: ReadyState,
      isReadyStateOpen: readyState === ReadyState.OPEN,
      expectedOpenValue: 1,
      actualReadyState: readyState,
      socketURL: SOCKET_URL
    });
    
    // 获取编辑器中的最新内容，而不是使用props中的content
    let currentContent = content; // 默认使用props内容
    
    // 如果编辑器实例存在，直接从编辑器获取最新内容
    if (editorRef?.current) {
      try {
        currentContent = editorRef.current.getHTML() || content;
        console.log("📝 从编辑器获取最新内容，长度:", currentContent.length);
      } catch (error) {
        console.warn("⚠️ 无法从编辑器获取内容，使用props内容:", error);
      }
    }
    
    console.log("📄 将要分析的内容长度:", currentContent.length);
    
    // 使用更宽松的连接检查
    if (!isSocketActuallyReady()) {
      if (readyState === ReadyState.CONNECTING) {
        console.log("🔄 WebSocket连接中，但仍尝试发送");
        onProcessingStatus?.(false, "WebSocket连接中，正在尝试...");
        // 不return，继续尝试发送
      } else if (readyState === ReadyState.CLOSED || readyState === ReadyState.CLOSING) {
        console.warn("⚠️ WebSocket已断开，无法进行AI分析，状态:", readyState);
        onProcessingStatus?.(false, "AI助手连接已断开，请刷新页面");
        return;
      } else {
        console.warn("⚠️ WebSocket状态异常，状态:", readyState);
        onProcessingStatus?.(false, "WebSocket状态异常，正在尝试...");
        // 仍然尝试发送，可能会自动重连
      }
    }
    
    if (isAIProcessing) {
      console.log("⏳ AI正在处理中，跳过新请求");
      onProcessingStatus?.(false, "AI正在处理中，请稍候...");
      return;
    }
    
    if (!currentContent.trim()) {
      console.log("📄 文档内容为空，跳过AI分析");
      onProcessingStatus?.(false, "文档内容为空");
      return;
    }
    
    console.log("📤 手动触发AI分析，内容长度:", currentContent.length);
    // setLastAnalyzedContent(content); // 记录已分析的内容 - 暂时注释
    
    try {
      // 先设置处理状态
      onProcessingStatus?.(true, "正在发送分析请求...");
      
      sendMessage(currentContent); // 使用最新的内容而不是props中的content
      console.log("✅ AI分析请求已发送");
      
      // 发送成功后更新状态
      onProcessingStatus?.(true, "AI正在分析文档...");
      
    } catch (error) {
      console.error("❌ 发送AI分析请求失败:", error);
      onProcessingStatus?.(false, `发送请求失败: ${error instanceof Error ? error.message : '未知错误'}`);
      
      // 如果是WebSocket连接问题，提供重连建议
      if (readyState !== ReadyState.OPEN) {
        setTimeout(() => {
          onProcessingStatus?.(false, "连接异常，请稍后重试或刷新页面");
        }, 2000);
      }
    }
  }, [isSocketActuallyReady, isAIProcessing, sendMessage, onProcessingStatus, readyState]); // 移除content依赖
  
  // 处理编辑器实例就绪
  const handleEditorReady = useCallback((editor: any) => {
    editorRef.current = editor;
    console.log('📝 Document: 编辑器实例已准备就绪');
    // 同时调用App.tsx的回调
    if (onEditorReady) {
      onEditorReady(editor);
    }
  }, [onEditorReady]);

  // 注册手动分析函数
  useEffect(() => {
    if (onManualAnalysis) {
      console.log('📝 Document: 注册手动分析函数');
      onManualAnalysis(triggerManualAnalysis);
    }
    // 只在组件挂载时注册一次，不需要依赖 triggerManualAnalysis
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [onManualAnalysis]);

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
        <Editor 
          handleEditorChange={handleEditorChange} 
          content={content} 
          onEditorReady={handleEditorReady}
        />
      </div>
      
    </div>
  );
}
