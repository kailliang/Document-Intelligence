import Document from "./Document";
import { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";
import LoadingOverlay from "./internal/LoadingOverlay";
import Logo from "./assets/logo.png";
import ChatPanel from "./ChatPanel";
import { findTextInDocument, replaceText } from "./internal/HighlightExtension";

const BACKEND_URL = "http://localhost:8000";

// 项目名称映射
const PROJECT_NAMES: Record<number, string> = {
  1: "无线光遗传学设备",
  2: "微流控血液充氧设备"
};

// TypeScript interfaces for better type safety
interface DocumentVersion {
  id: number;
  version_number: number;
  content: string;
  is_active: boolean;
  created_at: string;
  document_id: number;
}


interface DocumentWithCurrentVersion {
  id: number;
  title: string;
  content: string;
  version_number: number;
  last_modified: string;
}

// AI建议相关的接口
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

interface AppState {
  currentDocument: DocumentWithCurrentVersion | null;
  documentVersions: DocumentVersion[];
  isLoading: boolean;
  leftSidebarCollapsed: boolean;
  rightSidebarCollapsed: boolean;
  hasUnsavedChanges: boolean;  // 跟踪是否有未保存的更改
  aiSuggestions: AISuggestion[];  // AI建议
  aiProcessingStatus: string;     // AI处理状态消息
  isAIProcessing: boolean;        // AI是否正在处理
  deleteDialog: {                 // 删除确认对话框状态
    isOpen: boolean;
    versionNumber: number | null;
  };
  activeRightTab: 'suggestions' | 'chat';  // 右侧栏活跃标签页
}

function App() {
  // 整合状态管理
  const [appState, setAppState] = useState<AppState>({
    currentDocument: null,
    documentVersions: [],
    isLoading: false,
    leftSidebarCollapsed: false,
    rightSidebarCollapsed: false,
    hasUnsavedChanges: false,
    aiSuggestions: [],
    aiProcessingStatus: "AI助手已关闭",
    isAIProcessing: false,
    deleteDialog: {
      isOpen: false,
      versionNumber: null
    },
    activeRightTab: 'suggestions'
  });

  // 响应式布局检测
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);
  
  useEffect(() => {
    const handleResize = () => {
      const mobile = window.innerWidth < 768;
      setIsMobile(mobile);
      
      // 在移动端自动折叠侧边栏
      if (mobile && (!appState.leftSidebarCollapsed || !appState.rightSidebarCollapsed)) {
        setAppState(prev => ({
          ...prev,
          leftSidebarCollapsed: true,
          rightSidebarCollapsed: true,
        }));
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [appState.leftSidebarCollapsed, appState.rightSidebarCollapsed]);

  const [currentDocumentContent, setCurrentDocumentContent] = useState<string>("");
  const [activeHighlightIndex, setActiveHighlightIndex] = useState<number | null>(null);
  
  // 高亮清除定时器引用
  const highlightTimerRef = useRef<number | null>(null);
  
  // TipTap编辑器实例引用
  const editorRef = useRef<any>(null);

  /**
   * 处理文档内容变化
   * Handle document content changes and mark as unsaved
   */
  const handleContentChange = (newContent: string) => {
    setCurrentDocumentContent(newContent);
    
    // 内容变化时清除段落高亮和定时器
    if (editorRef.current) {
      editorRef.current.commands.clearTemporaryHighlights();
    }
    setActiveHighlightIndex(null);
    if (highlightTimerRef.current) {
      clearTimeout(highlightTimerRef.current);
      highlightTimerRef.current = null;
    }
    
    // 如果内容与当前文档内容不同，标记为有未保存更改
    if (appState.currentDocument && newContent !== appState.currentDocument.content) {
      setAppState(prev => ({ ...prev, hasUnsavedChanges: true }));
    } else {
      setAppState(prev => ({ ...prev, hasUnsavedChanges: false }));
    }
  };

  // 不再默认加载第一个专利文档
  // 用户需要主动选择项目

  /**
   * 加载专利文档及其版本历史
   * Load a patent document with version control support
   */
  const loadPatent = async (documentNumber: number) => {
    setAppState(prev => ({ ...prev, isLoading: true }));
    console.log("Loading patent with versions:", documentNumber);
    
    try {
      // 获取文档当前版本内容（向后兼容）
      const documentResponse = await axios.get(`${BACKEND_URL}/document/${documentNumber}`);
      const documentData: DocumentWithCurrentVersion = documentResponse.data;
      
      // 获取所有版本历史
      const versionsResponse = await axios.get(`${BACKEND_URL}/api/documents/${documentNumber}/versions`);
      const versions: DocumentVersion[] = versionsResponse.data;
      
      setAppState(prev => ({ 
        ...prev, 
        currentDocument: documentData,
        documentVersions: versions,
        isLoading: false,
        hasUnsavedChanges: false,  // 重置未保存状态
        aiSuggestions: [],         // 清空AI建议
        aiProcessingStatus: "AI助手已关闭"  // 更新状态消息
      }));
      setCurrentDocumentContent(documentData.content);
      
    } catch (error) {
      console.error("Error loading document:", error);
      setAppState(prev => ({ ...prev, isLoading: false }));
    }
  };

  /**
   * 保存专利文档到当前版本
   * Save the current patent document to the backend (updates current version)
   */
  const savePatent = async (documentNumber: number) => {
    if (!appState.currentDocument) return;
    
    setAppState(prev => ({ ...prev, isLoading: true }));
    try {
      await axios.post(`${BACKEND_URL}/save/${documentNumber}`, {
        content: currentDocumentContent,
      });
      
      // 更新文档的最后修改时间并重置未保存状态
      setAppState(prev => ({
        ...prev,
        currentDocument: prev.currentDocument ? {
          ...prev.currentDocument,
          last_modified: new Date().toISOString(),
        } : null,
        isLoading: false,
        hasUnsavedChanges: false  // 保存后重置未保存状态
      }));
      
    } catch (error) {
      console.error("Error saving document:", error);
      setAppState(prev => ({ ...prev, isLoading: false }));
    }
  };

  /**
   * 创建新版本
   * Create a new version of the document
   */
  const createNewVersion = async () => {
    if (!appState.currentDocument) return;
    
    setAppState(prev => ({ ...prev, isLoading: true }));
    try {
      // 创建新版本（空文档）
      await axios.post(`${BACKEND_URL}/api/documents/${appState.currentDocument.id}/versions`, {});
      
      // 重新加载文档和版本历史
      await loadPatent(appState.currentDocument.id);
      
    } catch (error) {
      console.error("Error creating new version:", error);
      setAppState(prev => ({ ...prev, isLoading: false }));
    }
  };

  /**
   * 切换到指定版本
   * Switch to a specific version
   */
  const switchToVersion = async (versionNumber: number) => {
    if (!appState.currentDocument) return;
    
    setAppState(prev => ({ ...prev, isLoading: true }));
    try {
      // 切换版本
      const response = await axios.post(`${BACKEND_URL}/api/documents/${appState.currentDocument.id}/switch-version`, {
        version_number: versionNumber,
      });
      
      const updatedDocument: DocumentWithCurrentVersion = response.data;
      
      setAppState(prev => ({
        ...prev,
        currentDocument: updatedDocument,
        isLoading: false,
        hasUnsavedChanges: false,  // 切换版本后重置未保存状态
        aiSuggestions: [],         // 清空AI建议
        aiProcessingStatus: "AI助手已关闭"  // 更新状态消息
      }));
      setCurrentDocumentContent(updatedDocument.content);
      
      // 重新获取版本列表以更新激活状态
      const versionsResponse = await axios.get(`${BACKEND_URL}/api/documents/${appState.currentDocument.id}/versions`);
      setAppState(prev => ({
        ...prev,
        documentVersions: versionsResponse.data
      }));
      
    } catch (error) {
      console.error("Error switching version:", error);
      setAppState(prev => ({ ...prev, isLoading: false }));
    }
  };

  /**
   * 删除指定版本
   * Delete a specific version
   */
  // 打开删除确认对话框
  const openDeleteDialog = (versionNumber: number) => {
    setAppState(prev => ({
      ...prev,
      deleteDialog: {
        isOpen: true,
        versionNumber
      }
    }));
  };

  // 关闭删除确认对话框
  const closeDeleteDialog = () => {
    setAppState(prev => ({
      ...prev,
      deleteDialog: {
        isOpen: false,
        versionNumber: null
      }
    }));
  };

  // 确认删除版本
  const confirmDeleteVersion = async () => {
    if (!appState.currentDocument || !appState.deleteDialog.versionNumber) return;
    
    const versionNumber = appState.deleteDialog.versionNumber;
    closeDeleteDialog();
    
    setAppState(prev => ({ ...prev, isLoading: true }));
    try {
      // 删除版本
      await axios.delete(`${BACKEND_URL}/api/documents/${appState.currentDocument.id}/versions/${versionNumber}`);
      
      // 重新加载文档和版本历史
      await loadPatent(appState.currentDocument.id);
      
    } catch (error: any) {
      console.error("Error deleting version:", error);
      // 显示错误信息
      const errorMessage = error.response?.data?.detail || "删除版本失败";
      alert(errorMessage);
      setAppState(prev => ({ ...prev, isLoading: false }));
    }
  };

  /**
   * 处理AI建议回调
   * Handle AI suggestions from WebSocket
   */
  const handleAISuggestions = useCallback((suggestions: AISuggestion[]) => {
    console.log("🎯 更新AI建议:", suggestions.length, "个建议");
    setAppState(prev => {
      // 防止重复设置相同的建议
      if (JSON.stringify(prev.aiSuggestions) === JSON.stringify(suggestions)) {
        console.log("🔄 建议未改变，跳过更新");
        return prev;
      }
      return {
        ...prev,
        aiSuggestions: suggestions,
        isAIProcessing: false
      };
    });
  }, []);

  /**
   * 处理AI处理状态回调
   * Handle AI processing status updates
   */
  const handleAIProcessingStatus = useCallback((isProcessing: boolean, message?: string) => {
    console.log("📊 AI状态更新:", { isProcessing, message });
    setAppState(prev => ({
      ...prev,
      isAIProcessing: isProcessing,
      aiProcessingStatus: message || (isProcessing ? "AI处理中..." : "AI待机中")
    }));
  }, []);

  /**
   * 通过文本内容高亮编辑器中的段落
   * Highlight paragraph in editor by matching text content
   */
  const highlightParagraphByText = useCallback((suggestion: AISuggestion) => {
    console.log(`🎯 开始通过文本匹配高亮段落，严重程度: ${suggestion.severity}`);
    
    if (!editorRef.current) {
      console.warn('❌ 编辑器实例未找到');
      return;
    }

    const editor = editorRef.current;
    
    // 使用新的ProseMirror API进行文本匹配和高亮
    if (suggestion.originalText || suggestion.text) {
      const searchText = suggestion.originalText || suggestion.text || '';
      const position = findTextInDocument(editor.state.doc, searchText);
      
      if (position) {
        // 清除之前的高亮
        editor.commands.clearTemporaryHighlights();
        // 添加临时高亮
        editor.commands.addTemporaryHighlight(position.from, position.to, suggestion.severity);
        
        // 不设置光标选中，只添加高亮和滚动
        editor.commands.focus();
        
        // 等待高亮装饰渲染完成后滚动到居中位置
        setTimeout(() => {
          if (editorRef.current) {
            // 通过CSS选择器找到高亮元素
            const highlightElement = editorRef.current.view.dom.querySelector(
              `.temporary-highlight-${suggestion.severity}`
            );
            
            if (highlightElement) {
              // 找到真正的滚动容器并检查元素可见性
              const scrollContainer = findScrollContainer(highlightElement);
              const containerRect = scrollContainer.getBoundingClientRect();
              const elementRect = highlightElement.getBoundingClientRect();
              
              // 相对于滚动容器计算可见性
              const isVisible = 
                elementRect.top >= containerRect.top && 
                elementRect.bottom <= containerRect.bottom;
              
              // 添加调试信息
              console.log('📊 可见性调试信息:', {
                scrollContainer: scrollContainer.className || scrollContainer.tagName,
                containerRect: { top: containerRect.top, bottom: containerRect.bottom, height: containerRect.height },
                elementRect: { top: elementRect.top, bottom: elementRect.bottom, height: elementRect.height },
                isVisible
              });
              
              // 直接用viewport坐标判断可见性 - 简单明了
              const isInViewport = 
                elementRect.bottom > 0 && 
                elementRect.top < window.innerHeight;
              
              // 检查是否有足够的内容可见（至少20px）
              const visibleHeight = Math.min(elementRect.bottom, window.innerHeight) - Math.max(elementRect.top, 0);
              const hasEnoughVisible = visibleHeight >= 20;
              
              console.log('📊 简化可见性检查:', {
                elementRect,
                isInViewport,
                visibleHeight,
                hasEnoughVisible,
                windowHeight: window.innerHeight
              });
              
              if (isInViewport && hasEnoughVisible) {
                console.log('✅ 元素在viewport中且有足够内容可见，无需滚动');
              } else {
                // 元素不在viewport或可见内容不足 - 需要滚动到合理位置
                console.log('📊 元素需要滚动到可见位置');
                
                highlightElement.scrollIntoView({
                  behavior: 'smooth',
                  block: 'center',
                  inline: 'nearest'
                });
                console.log('✅ 滚动到center位置');
              }
            } else {
              console.warn('❌ 未找到高亮元素，使用备用滚动方案');
              // 备用方案：设置光标位置触发滚动
              editorRef.current.commands.setTextSelection(position.from);
            }
          }
        }, 100); // 增加延迟确保高亮装饰已渲染
        
        console.log(`✅ 成功高亮文本: "${searchText.substring(0, 50)}..."`);
      } else {
        console.warn(`❌ 未找到文本: "${searchText.substring(0, 50)}..."`);
      }
    }
  }, []);

  /**
   * 处理建议卡片点击事件
   * Handle suggestion card click
   */
  const handleSuggestionClick = useCallback((suggestion: AISuggestion, index: number) => {
    console.log('🖱️ 点击建议卡片:', suggestion);
    
    // 清除之前的定时器
    if (highlightTimerRef.current) {
      clearTimeout(highlightTimerRef.current);
      highlightTimerRef.current = null;
    }
    
    // 设置当前激活的建议
    setActiveHighlightIndex(index);
    
    // 使用文本高亮
    highlightParagraphByText(suggestion);
    
    // 3秒后自动清除高亮和激活状态
    highlightTimerRef.current = setTimeout(() => {
      console.log('⏰ 3秒后自动清除高亮');
      if (editorRef.current) {
        editorRef.current.commands.clearTemporaryHighlights();
      }
      setActiveHighlightIndex(null);
      highlightTimerRef.current = null;
    }, 3000);
  }, [highlightParagraphByText]);

  // 组件卸载时清理定时器
  useEffect(() => {
    return () => {
      if (highlightTimerRef.current) {
        clearTimeout(highlightTimerRef.current);
      }
    };
  }, []);

  /**
   * 找到元素的真正滚动容器
   * Find the actual scroll container for an element
   */
  const findScrollContainer = (element: Element): Element => {
    let parent = element.parentElement;
    while (parent) {
      const style = getComputedStyle(parent);
      if (
        style.overflow === 'scroll' || 
        style.overflow === 'auto' || 
        style.overflowY === 'scroll' || 
        style.overflowY === 'auto'
      ) {
        console.log('🔍 找到滚动容器:', parent.className || parent.tagName);
        return parent;
      }
      parent = parent.parentElement;
    }
    console.log('🔍 未找到滚动容器，使用document.documentElement');
    return document.documentElement;
  };

  /**
   * 切换侧边栏显示状态
   * Toggle sidebar visibility
   */
  const toggleLeftSidebar = () => {
    setAppState(prev => ({ 
      ...prev, 
      leftSidebarCollapsed: !prev.leftSidebarCollapsed 
    }));
  };

  const toggleRightSidebar = () => {
    setAppState(prev => ({ 
      ...prev, 
      rightSidebarCollapsed: !prev.rightSidebarCollapsed 
    }));
  };

  /**
   * 手动触发AI分析
   * Manually trigger AI analysis
   */
  const [manualAnalysisFunction, setManualAnalysisFunction] = useState<(() => void) | null>(null);
  
  const triggerAIAnalysis = () => {
    if (!appState.currentDocument) {
      console.error('请先选择一个文档');
      return;
    }

    if (!manualAnalysisFunction) {
      console.warn('AI分析函数未就绪，请确保文档已加载');
      return;
    }

    console.log('🚀 触发AI分析');
    manualAnalysisFunction();
  };

  const registerManualAnalysis = useCallback((analysisFunction: () => void) => {
    console.log('📌 App: 接收到手动分析函数');
    setManualAnalysisFunction(() => analysisFunction);
  }, []);

  /**
   * 处理编辑器实例准备就绪
   * Handle editor instance ready
   */
  const handleEditorReady = useCallback((editor: any) => {
    editorRef.current = editor;
    console.log('📝 编辑器实例已准备就绪', editor);
  }, []);

  /**
   * 接受AI建议并应用到文档
   * Accept AI suggestion and apply to document
   */
  const acceptSuggestion = useCallback((suggestion: AISuggestion, index: number) => {
    console.log('✅ 接受建议:', suggestion);
    
    // 使用新的替换函数
    if (suggestion.originalText && suggestion.replaceTo && editorRef.current) {
      const success = replaceText(editorRef.current, suggestion.originalText, suggestion.replaceTo);
      
      if (success) {
        console.log('✅ 文本替换成功');
      } else {
        console.warn('❌ 未找到要替换的文本:', suggestion.originalText);
        // TODO: 显示错误提示给用户
      }
    } else if (suggestion.text && suggestion.suggestion && editorRef.current) {
      // 兼容旧格式：使用text和suggestion字段
      const success = replaceText(editorRef.current, suggestion.text, suggestion.suggestion);
      
      if (!success) {
        console.warn('❌ 未找到要替换的文本:', suggestion.text);
      }
    }
    
    // 从建议列表中移除
    setAppState(prev => ({
      ...prev,
      aiSuggestions: prev.aiSuggestions.filter((_, i) => i !== index)
    }));
  }, []);

  /**
   * 拷贝建议内容到剪贴板
   * Copy suggestion content to clipboard
   */
  const copySuggestion = useCallback((suggestion: AISuggestion) => {
    const textToCopy = suggestion.replaceTo || suggestion.suggestion;
    navigator.clipboard.writeText(textToCopy).then(() => {
      console.log('📋 已复制到剪贴板:', textToCopy);
      // TODO: 显示成功提示
    }).catch(err => {
      console.error('复制失败:', err);
    });
  }, []);

  /**
   * 关闭/忽略建议
   * Close/ignore suggestion
   */
  const closeSuggestion = useCallback((index: number) => {
    console.log('❌ 关闭建议:', index);
    setAppState(prev => ({
      ...prev,
      aiSuggestions: prev.aiSuggestions.filter((_, i) => i !== index)
    }));
  }, []);

  return (
    <div className="flex flex-col h-screen w-full bg-gray-50">
      {/* 加载遮罩层 */}
      {appState.isLoading && <LoadingOverlay />}
      
      {/* Header - 保持原有设计但优化样式 */}
      <header className="flex items-center justify-center w-full bg-gradient-to-r from-gray-900 to-gray-800 text-white shadow-lg z-50 h-16">
        <img src={Logo} alt="Logo" className="h-10" />
        <h1 className="ml-4 text-xl font-semibold">Patent Review System</h1>
      </header>

      {/* 主内容区域 - 三栏布局 */}
      <div className="flex flex-1 overflow-hidden">
        
        {/* 移动端遮罩层 */}
        {isMobile && !appState.leftSidebarCollapsed && (
          <div 
            className="mobile-overlay z-40 lg:hidden"
            onClick={() => setAppState(prev => ({ ...prev, leftSidebarCollapsed: true }))}
          />
        )}
        
        {/* 左侧栏 - 项目和版本管理区 */}
        <aside className={`
          ${appState.leftSidebarCollapsed ? 'w-12' : 'w-80'} 
          ${isMobile && !appState.leftSidebarCollapsed ? 'fixed left-0 top-16 bottom-0 z-50' : 'relative'}
          bg-white border-r border-gray-200 shadow-sm transition-all duration-300 ease-in-out
          flex flex-col
        `}>
          {/* 左侧栏头部 */}
          <div className="flex items-center justify-between p-4 border-b border-gray-200">
            {!appState.leftSidebarCollapsed && (
              <h2 className="text-lg font-semibold text-gray-800">项目管理</h2>
            )}
            <button
              onClick={toggleLeftSidebar}
              className="p-2 rounded-md hover:bg-gray-100 transition-colors duration-200"
              aria-label="Toggle left sidebar"
            >
              <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                      d={appState.leftSidebarCollapsed ? "M9 5l7 7-7 7" : "M15 19l-7-7 7-7"} />
              </svg>
            </button>
          </div>

          {/* 左侧栏内容 */}
          {!appState.leftSidebarCollapsed && (
            <div className="flex-1 p-4 space-y-4">
              {/* 项目选择区域 */}
              <div className="space-y-2">
                <div className="space-y-2">
                  <button
                    onClick={() => loadPatent(1)}
                    className={`w-full p-3 text-left rounded-lg border transition-all duration-200 ${
                      appState.currentDocument?.id === 1
                        ? 'bg-blue-50 border-blue-200 text-blue-800'
                        : 'bg-white border-gray-200 hover:bg-gray-50 text-gray-700'
                    }`}
                  >
                    <div className="font-medium">{PROJECT_NAMES[1]}</div>
                  </button>
                  
                  <button
                    onClick={() => loadPatent(2)}
                    className={`w-full p-3 text-left rounded-lg border transition-all duration-200 ${
                      appState.currentDocument?.id === 2
                        ? 'bg-blue-50 border-blue-200 text-blue-800'
                        : 'bg-white border-gray-200 hover:bg-gray-50 text-gray-700'
                    }`}
                  >
                    <div className="font-medium">{PROJECT_NAMES[2]}</div>
                  </button>
                </div>
              </div>

              {/* 版本管理区域 - 只有选中项目时才显示 */}
              {appState.currentDocument && (
                <div className="border-t border-gray-200 pt-4">
                  <div className="space-y-3">
                    {/* 当前版本信息 */}
                    <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-green-800">当前版本</span>
                        <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full">
                          v{appState.currentDocument.version_number}.0
                        </span>
                      </div>
                      <div className="text-xs text-green-600 mt-1">
                        修改于 {new Date(appState.currentDocument.last_modified).toLocaleString()}
                      </div>
                    </div>
                    
                    {/* 创建新版本按钮 */}
                    <button 
                      onClick={createNewVersion}
                      disabled={appState.isLoading}
                      className="w-full p-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors duration-200"
                    >
                      {appState.isLoading ? '创建中...' : '+ 创建新版本'}
                    </button>

                    {/* 版本历史列表 */}
                    {appState.documentVersions.length > 1 && (
                      <div className="space-y-2">
                        <h4 className="text-xs font-medium text-gray-700 uppercase tracking-wide">版本历史</h4>
                        <div className="max-h-32 overflow-y-auto space-y-1">
                          {appState.documentVersions.map((version) => (
                            <div
                              key={version.id}
                              className={`relative group rounded-md text-xs transition-all duration-200 border ${
                                version.version_number === appState.currentDocument?.version_number
                                  ? 'bg-blue-100 text-blue-800 border-blue-200'
                                  : 'bg-gray-50 text-gray-700 border-gray-200'
                              } ${appState.isLoading ? 'opacity-50' : ''}`}
                            >
                              {/* 版本信息区域 - 可点击切换 */}
                              <button
                                onClick={() => switchToVersion(version.version_number)}
                                disabled={appState.isLoading || version.version_number === appState.currentDocument?.version_number}
                                className={`w-full p-3 text-left rounded-md transition-all duration-200 ${
                                  version.version_number === appState.currentDocument?.version_number
                                    ? ''
                                    : 'hover:bg-gray-100'
                                } ${appState.isLoading ? 'cursor-not-allowed' : 'cursor-pointer'}`}
                              >
                                <div className="flex items-center justify-between mb-1">
                                  <span className="font-medium text-sm">v{version.version_number}.0</span>
                                  {version.version_number === appState.currentDocument?.version_number && (
                                    <span className="text-xs bg-blue-200 text-blue-800 px-2 py-0.5 rounded-full">当前</span>
                                  )}
                                </div>
                                <div className="text-xs text-gray-500">
                                  创建于 {new Date(version.created_at).toLocaleString('zh-CN', {
                                    month: 'short',
                                    day: 'numeric',
                                    hour: '2-digit',
                                    minute: '2-digit'
                                  })}
                                </div>
                              </button>
                              
                              {/* 删除按钮 - 只有在超过1个版本时才显示 */}
                              {appState.documentVersions.length > 1 && (
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    openDeleteDialog(version.version_number);
                                  }}
                                  disabled={appState.isLoading}
                                  className="absolute top-2 right-2 w-6 h-6 flex items-center justify-center rounded-full bg-red-100 text-red-600 hover:bg-red-200 transition-colors duration-200 opacity-0 group-hover:opacity-100"
                                  title="删除版本"
                                  aria-label="删除版本"
                                >
                                  <span className="text-xs">×</span>
                                </button>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* 操作按钮组 - 只有选中项目时才显示 */}
              {appState.currentDocument && (
                <div className="border-t border-gray-200 pt-4 space-y-2">
                <button
                  onClick={() => appState.currentDocument && savePatent(appState.currentDocument.id)}
                  disabled={!appState.currentDocument}
                  className="w-full p-2 text-sm bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors duration-200"
                >
                  💾 保存文档
                </button>
                
                <button className="w-full p-2 text-sm border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 transition-colors duration-200">
                  📄 导出文档
                </button>
              </div>
              )}
            </div>
          )}
        </aside>

        {/* 中间区域 - 文档编辑区 */}
        <main className="flex-1 flex flex-col bg-white min-h-0">
          {/* 文档工具栏 */}
          <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-gray-50 flex-shrink-0">
            <div className="flex items-center space-x-4">
              <h2 className="text-xl font-semibold text-gray-800">
                {appState.currentDocument?.title || "请选择文档"}
              </h2>
            </div>
            
            {/* 未来TinyMCE工具栏预留空间 */}
            <div className="flex items-center space-x-2">
              <div className="text-xs text-gray-500 bg-yellow-100 px-2 py-1 rounded">
                TinyMCE 工具栏预留位置
              </div>
            </div>
          </div>

          {/* 编辑器主区域 - 添加overflow-hidden确保内容不会撑开容器 */}
          <div className="flex-1 p-4 overflow-hidden">
            <div className="h-full bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
              {appState.currentDocument ? (
                <Document
                  onContentChange={handleContentChange}
                  content={currentDocumentContent}
                  onAISuggestions={handleAISuggestions}
                  onProcessingStatus={handleAIProcessingStatus}
                  onManualAnalysis={registerManualAnalysis}
                  onEditorReady={handleEditorReady}
                />
              ) : (
                <div className="h-full flex items-center justify-center text-gray-500">
                  <div className="text-center">
                    <div className="text-6xl mb-4">📄</div>
                    <div className="text-lg font-medium">请选择一个文档开始编辑</div>
                    <div className="text-sm">从左侧面板选择 Patent 1 或 Patent 2</div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* 状态栏 - 添加flex-shrink-0确保始终可见 */}
          <div className="flex items-center justify-between px-4 py-2 bg-gray-50 border-t border-gray-200 text-sm text-gray-600 flex-shrink-0">
            <div className="flex items-center space-x-4">
              <span>字数: {currentDocumentContent.length}</span>
              
              {/* 文档保存状态 */}
              <span className={`flex items-center ${
                appState.isLoading 
                  ? 'text-yellow-600' 
                  : appState.hasUnsavedChanges 
                    ? 'text-orange-600' 
                    : 'text-green-600'
              }`}>
                <div className={`w-2 h-2 rounded-full mr-2 ${
                  appState.isLoading 
                    ? 'bg-yellow-400' 
                    : appState.hasUnsavedChanges 
                      ? 'bg-orange-400' 
                      : 'bg-green-400'
                }`}></div>
                {appState.isLoading 
                  ? '保存中...' 
                  : appState.hasUnsavedChanges 
                    ? '有未保存更改' 
                    : '已保存'
                }
              </span>
              
              {/* AI处理状态 */}
              <span className={`flex items-center ${
                appState.isAIProcessing ? 'text-blue-600' : 'text-gray-500'
              }`}>
                <div className={`w-2 h-2 rounded-full mr-2 ${
                  appState.isAIProcessing ? 'bg-blue-400 animate-pulse' : 'bg-gray-400'
                }`}></div>
                <span className="text-xs">
                  🤖 {appState.aiProcessingStatus}
                </span>
              </span>
            </div>
            <div>
              {appState.currentDocument?.last_modified && 
                `最后修改: ${new Date(appState.currentDocument.last_modified).toLocaleString()}`
              }
            </div>
          </div>
        </main>

        {/* 右侧栏移动端遮罩层 */}
        {isMobile && !appState.rightSidebarCollapsed && (
          <div 
            className="mobile-overlay z-40 lg:hidden"
            onClick={() => setAppState(prev => ({ ...prev, rightSidebarCollapsed: true }))}
          />
        )}
        
        {/* 右侧栏 - AI功能预留区 */}
        <aside className={`
          ${appState.rightSidebarCollapsed ? 'w-12' : 'w-80'} 
          ${isMobile && !appState.rightSidebarCollapsed ? 'fixed right-0 top-16 bottom-0 z-50' : 'relative'}
          bg-white border-l border-gray-200 shadow-sm transition-all duration-300 ease-in-out
          flex flex-col
        `}>
          {/* 右侧栏头部 */}
          <div className="flex items-center justify-between p-4 border-b border-gray-200">
            <button
              onClick={toggleRightSidebar}
              className="p-2 rounded-md hover:bg-gray-100 transition-colors duration-200"
              aria-label="Toggle right sidebar"
            >
              <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                      d={appState.rightSidebarCollapsed ? "M15 19l-7-7 7-7" : "M9 5l7 7-7 7"} />
              </svg>
            </button>
            {!appState.rightSidebarCollapsed && (
              <h2 className="text-lg font-semibold text-gray-800">AI 助手</h2>
            )}
          </div>

          {/* 右侧栏内容 */}
          {!appState.rightSidebarCollapsed && (
            <div className="flex-1 overflow-hidden flex flex-col">
              {/* 标签页导航 */}
              <div className="flex border-b border-gray-200">
                <button
                  onClick={() => setAppState(prev => ({ ...prev, activeRightTab: 'suggestions' }))}
                  className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
                    appState.activeRightTab === 'suggestions'
                      ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50'
                      : 'text-gray-600 hover:text-gray-800 hover:bg-gray-50'
                  }`}
                >
                  🤖 AI建议
                </button>
                <button
                  onClick={() => setAppState(prev => ({ ...prev, activeRightTab: 'chat' }))}
                  className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
                    appState.activeRightTab === 'chat'
                      ? 'text-purple-600 border-b-2 border-purple-600 bg-purple-50'
                      : 'text-gray-600 hover:text-gray-800 hover:bg-gray-50'
                  }`}
                >
                  💬 AI聊天
                </button>
              </div>

              {/* 标签页内容 */}
              {appState.activeRightTab === 'chat' ? (
                <ChatPanel className="flex-1" />
              ) : (
                <div className="flex-1 p-4 overflow-y-auto">
                  {/* AI建议显示区域 */}
                  <div className="space-y-4">
                <div className="flex items-center justify-end">
                  <div className="flex items-center gap-3">
                    {/* AI分析按钮 */}
                    <button
                      onClick={triggerAIAnalysis}
                      disabled={appState.isAIProcessing || appState.aiProcessingStatus.includes('已断开') || appState.aiProcessingStatus.includes('连接失败')}
                      className={`px-3 py-1.5 text-xs font-medium rounded-full transition-all duration-200 ${
                        appState.isAIProcessing || appState.aiProcessingStatus.includes('已断开') || appState.aiProcessingStatus.includes('连接失败')
                          ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                          : 'bg-blue-600 text-white hover:bg-blue-700'
                      }`}
                      aria-label="AI分析文档"
                      title={
                        appState.aiProcessingStatus.includes('已断开') 
                          ? 'WebSocket连接已断开，请刷新页面'
                          : appState.aiProcessingStatus.includes('连接失败')
                          ? 'WebSocket连接失败，请检查网络'
                          : appState.isAIProcessing
                          ? 'AI正在分析中，请稍候'
                          : 'AI分析文档'
                      }
                    >
                      {appState.isAIProcessing 
                        ? '🔄 分析中...' 
                        : appState.aiProcessingStatus.includes('已断开')
                        ? '❌ 已断开'
                        : appState.aiProcessingStatus.includes('连接失败')
                        ? '❌ 连接失败'
                        : appState.aiProcessingStatus.includes('连接中')
                        ? '🔄 尝试连接'
                        : '🤖 AI分析'
                      }
                    </button>
                  </div>
                </div>

                {/* AI建议列表 */}
                {appState.aiSuggestions.length > 0 ? (
                  <div className="space-y-3">
                    {/* 对建议进行排序：先按严重程度(high->medium->low)，再按段落顺序 */}
                    {[...appState.aiSuggestions]
                      .sort((a, b) => {
                        const severityOrder = { high: 3, medium: 2, low: 1 };
                        const severityA = severityOrder[a.severity] || 2;
                        const severityB = severityOrder[b.severity] || 2;
                        
                        // 先按严重程度排序（降序）
                        if (severityA !== severityB) {
                          return severityB - severityA;
                        }
                        
                        // 相同严重程度按段落排序（升序）
                        return a.paragraph - b.paragraph;
                      })
                      .map((suggestion, index) => (
                      <div
                        key={index}
                        className={`p-3 rounded-lg border-l-4 transition-all duration-200 ${
                          activeHighlightIndex === index
                            ? 'ring-2 ring-offset-2 ring-gray-400 shadow-lg' // 激活状态
                            : ''
                        } ${
                          suggestion.severity === 'high'
                            ? 'border-red-500 bg-red-50'
                            : suggestion.severity === 'medium'
                            ? 'border-yellow-500 bg-yellow-50'
                            : 'border-blue-500 bg-blue-50'
                        }`}
                      >
                        {/* 可点击区域 - 用于高亮文本 */}
                        <div 
                          onClick={() => handleSuggestionClick(suggestion, index)}
                          className="cursor-pointer"
                        >
                          {/* 建议头部 */}
                          <div className="flex items-center gap-2 mb-2">
                            {activeHighlightIndex === index && (
                              <span className="text-xs px-2 py-1 bg-green-200 text-green-800 rounded-full font-medium animate-pulse">
                                已高亮
                              </span>
                            )}
                            <span className="text-xs font-medium text-gray-600">
                              段落 {suggestion.paragraph}
                            </span>
                            <span
                              className={`text-xs px-2 py-1 rounded-full font-medium ${
                                suggestion.severity === 'high'
                                  ? 'bg-red-200 text-red-800'
                                  : suggestion.severity === 'medium'
                                  ? 'bg-yellow-200 text-yellow-800'
                                  : 'bg-blue-200 text-blue-800'
                              }`}
                            >
                              {suggestion.severity === 'high' ? '严重' : 
                               suggestion.severity === 'medium' ? '中等' : '轻微'}
                            </span>
                            <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                              {suggestion.type}
                            </span>
                          </div>

                          {/* 问题描述 */}
                          <p className="text-sm text-gray-700 mb-3 leading-relaxed">
                            {suggestion.description}
                          </p>

                          {/* AI建议 */}
                          <div className="bg-white p-2 rounded border mb-3">
                            <div className="flex items-start gap-2">
                              <span className="text-green-600 text-sm font-medium">💡 建议:</span>
                              <p className="text-sm text-green-700 leading-relaxed">
                                {suggestion.suggestion}
                              </p>
                            </div>
                          </div>
                        </div>

                        {/* 操作按钮 */}
                        <div className="flex gap-2 pt-2 border-t">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              acceptSuggestion(suggestion, index);
                            }}
                            className="flex-1 px-3 py-1.5 text-xs font-medium text-white bg-green-600 hover:bg-green-700 rounded-md transition-colors"
                            title="接受建议并应用到文档"
                          >
                            ✅ 接受
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              copySuggestion(suggestion);
                            }}
                            className="flex-1 px-3 py-1.5 text-xs font-medium text-gray-700 bg-gray-200 hover:bg-gray-300 rounded-md transition-colors"
                            title="复制建议内容"
                          >
                            📋 拷贝
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              closeSuggestion(index);
                            }}
                            className="flex-1 px-3 py-1.5 text-xs font-medium text-gray-700 bg-gray-200 hover:bg-gray-300 rounded-md transition-colors"
                            title="忽略此建议"
                          >
                            ❌ 关闭
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                  ) : (
                    /* 无建议时的空状态 */
                    <div className="h-full flex flex-col items-center justify-center text-gray-500 py-8">
                      <div className="text-center space-y-4">
                        <div className="text-4xl">🤖</div>
                        <div className="text-lg font-medium">AI 智能助手</div>
                        <div className="text-sm max-w-64 text-center">
                          {appState.isAIProcessing 
                            ? "AI正在分析您的文档，请稍候..."
                            : appState.currentDocument
                            ? "点击 AI 分析按钮开始分析文档"
                            : "请先选择一个文档开始编辑"
                          }
                        </div>
                      
                      {/* 功能介绍 */}
                      <div className="mt-6 p-3 bg-blue-50 border border-blue-200 rounded-lg text-left">
                        <div className="text-xs font-medium text-blue-800 mb-2">
                          ✨ AI功能介绍
                        </div>
                        <ul className="text-xs text-blue-600 space-y-1">
                          <li>• 专利权利要求格式检查</li>
                          <li>• 语法和结构分析</li>
                          <li>• 实时改进建议</li>
                          <li>• 自动问题检测</li>
                        </ul>
                      </div>
                    </div>
                  </div>
                  )}

                {/* 建议统计 */}
                {appState.aiSuggestions.length > 0 && (
                  <div className="mt-4 p-3 bg-gray-50 rounded-lg">
                    <div className="flex items-center justify-between text-xs text-gray-600">
                      <span>共发现 {appState.aiSuggestions.length} 个建议</span>
                      <div className="flex items-center gap-3">
                        <span className="flex items-center gap-1">
                          <div className="w-2 h-2 bg-red-400 rounded-full"></div>
                          严重: {appState.aiSuggestions.filter(s => s.severity === 'high').length}
                        </span>
                        <span className="flex items-center gap-1">
                          <div className="w-2 h-2 bg-yellow-400 rounded-full"></div>
                          中等: {appState.aiSuggestions.filter(s => s.severity === 'medium').length}
                        </span>
                        <span className="flex items-center gap-1">
                          <div className="w-2 h-2 bg-blue-400 rounded-full"></div>
                          轻微: {appState.aiSuggestions.filter(s => s.severity === 'low').length}
                        </span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
              )}
            </div>
          )}
        </aside>

      </div>

      {/* 删除版本确认对话框 */}
      {appState.deleteDialog.isOpen && (
        <div className="fixed inset-0 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4 shadow-2xl border border-gray-200">
            <div className="flex items-center mb-4">
              <div className="flex-shrink-0 w-10 h-10 mx-auto flex items-center justify-center rounded-full bg-red-100">
                <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
            </div>
            <div className="text-center">
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                删除版本确认
              </h3>
              <p className="text-sm text-gray-500 mb-6">
                确定要删除版本 v{appState.deleteDialog.versionNumber}.0 吗？此操作无法撤销。
              </p>
              <div className="flex justify-center space-x-3">
                <button
                  onClick={closeDeleteDialog}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                >
                  取消
                </button>
                <button
                  onClick={confirmDeleteVersion}
                  className="px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                >
                  确认删除
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;