import Document from "./Document";
import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import LoadingOverlay from "./internal/LoadingOverlay";
import Logo from "./assets/logo.png";
import { useMutation, useQuery } from "@tanstack/react-query";

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

interface DocumentData {
  id: number;
  title: string;
  current_version_id?: number;
  created_at: string;
  updated_at: string;
  versions?: DocumentVersion[];
  current_version?: DocumentVersion;
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
  suggestion: string;
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
    aiProcessingStatus: "AI助手待机中",
    isAIProcessing: false,
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

  /**
   * 处理文档内容变化
   * Handle document content changes and mark as unsaved
   */
  const handleContentChange = (newContent: string) => {
    setCurrentDocumentContent(newContent);
    
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
        hasUnsavedChanges: false  // 重置未保存状态
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
      // 创建新版本
      await axios.post(`${BACKEND_URL}/api/documents/${appState.currentDocument.id}/versions`, {
        content: currentDocumentContent,
      });
      
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
        hasUnsavedChanges: false  // 切换版本后重置未保存状态
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
                            <button
                              key={version.id}
                              onClick={() => switchToVersion(version.version_number)}
                              disabled={appState.isLoading || version.version_number === appState.currentDocument?.version_number}
                              className={`w-full p-3 text-left rounded-md text-xs transition-all duration-200 ${
                                version.version_number === appState.currentDocument?.version_number
                                  ? 'bg-blue-100 text-blue-800 border border-blue-200'
                                  : 'bg-gray-50 text-gray-700 hover:bg-gray-100 border border-gray-200'
                              } ${appState.isLoading ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'}`}
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
            <div className="flex-1 p-4 overflow-y-auto">
              {/* AI建议显示区域 */}
              <div className="space-y-4">
                {/* 标题和状态 */}
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold text-gray-800">AI 建议</h3>
                  {appState.isAIProcessing && (
                    <div className="flex items-center text-blue-600">
                      <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse mr-2"></div>
                      <span className="text-xs">分析中...</span>
                    </div>
                  )}
                </div>

                {/* AI建议列表 */}
                {appState.aiSuggestions.length > 0 ? (
                  <div className="space-y-3">
                    {appState.aiSuggestions.map((suggestion, index) => (
                      <div
                        key={index}
                        className={`p-3 rounded-lg border-l-4 ${
                          suggestion.severity === 'high'
                            ? 'border-red-500 bg-red-50'
                            : suggestion.severity === 'medium'
                            ? 'border-yellow-500 bg-yellow-50'
                            : 'border-blue-500 bg-blue-50'
                        }`}
                      >
                        {/* 建议头部 */}
                        <div className="flex items-center gap-2 mb-2">
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
                        <div className="bg-white p-2 rounded border">
                          <div className="flex items-start gap-2">
                            <span className="text-green-600 text-sm font-medium">💡 建议:</span>
                            <p className="text-sm text-green-700 leading-relaxed">
                              {suggestion.suggestion}
                            </p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  /* 空状态显示 */
                  <div className="h-full flex flex-col items-center justify-center text-gray-500 py-8">
                    <div className="text-center space-y-4">
                      <div className="text-4xl">🤖</div>
                      <div className="text-lg font-medium">AI 智能助手</div>
                      <div className="text-sm max-w-64 text-center">
                        {appState.isAIProcessing 
                          ? "AI正在分析您的文档，请稍候..."
                          : appState.currentDocument
                          ? "开始编辑文档，AI将为您提供实时建议"
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
        </aside>

      </div>
    </div>
  );
}

export default App;
