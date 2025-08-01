import Document from "./Document";
import { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";
import LoadingOverlay from "./internal/LoadingOverlay";
import Logo from "./assets/logo.png";

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
    }
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
  const highlightTimerRef = useRef<NodeJS.Timeout | null>(null);

  /**
   * 处理文档内容变化
   * Handle document content changes and mark as unsaved
   */
  const handleContentChange = (newContent: string) => {
    setCurrentDocumentContent(newContent);
    
    // 内容变化时清除段落高亮和定时器
    clearParagraphHighlights();
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
  const highlightParagraphByText = useCallback((suggestion: AISuggestion, severity: 'high' | 'medium' | 'low') => {
    console.log(`🎯 开始通过文本匹配高亮段落，严重程度: ${severity}`);
    console.log(`🔍 建议描述: "${suggestion.description.substring(0, 100)}..."`);
    
    // 获取编辑器容器
    const editorElement = document.querySelector('.ProseMirror');
    console.log('📝 编辑器元素:', editorElement);
    
    if (!editorElement) {
      console.warn('❌ 编辑器元素未找到');
      return;
    }

    // 清除之前的高亮
    clearParagraphHighlights();

    // 获取所有段落元素
    const allElements = editorElement.querySelectorAll('p, h1, h2, h3, h4, h5, h6');
    const paragraphs = Array.from(allElements).filter(p => {
      const text = p.textContent?.trim();
      return text && text.length > 0; // 只包含有内容的段落
    });
    
    console.log(`📄 找到 ${paragraphs.length} 个非空段落`);
    
    // 尝试从建议描述中提取关键词进行匹配
    const extractKeywords = (description: string): string[] => {
      // 提取引号中的内容和重要词汇
      const quotedMatches = description.match(/'([^']+)'/g) || [];
      const quoted = quotedMatches.map(m => m.replace(/'/g, ''));
      
      // 提取claim相关的数字
      const claimMatches = description.match(/claim\s+(\d+)/gi) || [];
      const claims = claimMatches.map(m => m.toLowerCase());
      
      // 合并所有关键词
      return [...quoted, ...claims].filter(k => k.length > 3);
    };
    
    const keywords = extractKeywords(suggestion.description);
    console.log('🔑 提取的关键词:', keywords);
    
    // 按匹配度排序找到最佳匹配段落
    let bestMatch: { element: Element; score: number } | null = null;
    
    paragraphs.forEach((paragraph, index) => {
      const text = paragraph.textContent?.toLowerCase() || '';
      let score = 0;
      
      // 计算匹配分数
      keywords.forEach(keyword => {
        if (text.includes(keyword.toLowerCase())) {
          score += keyword.length; // 长关键词权重更高
        }
      });
      
      // 特殊处理：如果建议提到claim号，优先匹配对应的claim
      const claimMatch = suggestion.description.match(/claim\s+(\d+)/i);
      if (claimMatch) {
        const claimNumber = claimMatch[1];
        if (text.includes(`${claimNumber}.`) || text.includes(`claim ${claimNumber}`)) {
          score += 50; // 很高的权重
        }
      }
      
      console.log(`段落 ${index + 1}: "${text.substring(0, 40)}..." 匹配分数: ${score}`);
      
      if (score > 0 && (!bestMatch || score > bestMatch.score)) {
        bestMatch = { element: paragraph, score };
      }
    });
    
    const targetParagraph = bestMatch?.element;
    console.log(`🎯 最佳匹配段落:`, targetParagraph, `分数: ${bestMatch?.score || 0}`);

    if (targetParagraph) {
      // 使用更明显的高亮颜色和!important优先级
      const colors = {
        high: { 
          backgroundColor: '#fca5a5 !important', // 更深的红色
          borderLeft: '6px solid #dc2626 !important', // 更粗的边框
          padding: '12px !important',
          borderRadius: '8px !important',
          margin: '8px 0 !important',
          boxShadow: '0 4px 6px rgba(220, 38, 38, 0.3) !important' // 添加阴影
        },
        medium: { 
          backgroundColor: '#fbbf24 !important', // 更深的黄色
          borderLeft: '6px solid #d97706 !important',
          padding: '12px !important',
          borderRadius: '8px !important',
          margin: '8px 0 !important',
          boxShadow: '0 4px 6px rgba(217, 119, 6, 0.3) !important'
        },
        low: { 
          backgroundColor: '#93c5fd !important', // 更深的蓝色
          borderLeft: '6px solid #2563eb !important',
          padding: '12px !important',
          borderRadius: '8px !important',
          margin: '8px 0 !important',
          boxShadow: '0 4px 6px rgba(37, 99, 235, 0.3) !important'
        }
      };

      // 保存原始样式以便恢复
      const originalStyle = targetParagraph.getAttribute('style') || '';
      targetParagraph.setAttribute('data-original-style', originalStyle);
      
      // 清除原有的相关样式
      targetParagraph.style.removeProperty('background-color');
      targetParagraph.style.removeProperty('border-left');
      targetParagraph.style.removeProperty('padding');
      targetParagraph.style.removeProperty('border-radius');
      targetParagraph.style.removeProperty('margin');
      targetParagraph.style.removeProperty('box-shadow');
      
      // 更激进的样式覆盖方法
      let bgColor, borderColor, shadowColor;
      
      if (severity === 'high') {
        bgColor = '#dc2626'; // 更深的红色
        borderColor = '#991b1b';
        shadowColor = 'rgba(220, 38, 38, 0.5)';
      } else if (severity === 'medium') {
        bgColor = '#d97706'; // 更深的橙色
        borderColor = '#92400e';
        shadowColor = 'rgba(217, 119, 6, 0.5)';
      } else {
        bgColor = '#2563eb'; // 更深的蓝色
        borderColor = '#1d4ed8';
        shadowColor = 'rgba(37, 99, 235, 0.5)';
      }
      
      // 创建一个覆盖样式，强制显示
      const styleOverride = `
        background-color: ${bgColor} !important;
        color: white !important;
        border: 3px solid ${borderColor} !important;
        padding: 15px !important;
        border-radius: 10px !important;
        margin: 10px 0 !important;
        box-shadow: 0 6px 12px ${shadowColor} !important;
        font-weight: bold !important;
        transform: scale(1.02) !important;
        z-index: 1000 !important;
        position: relative !important;
      `;
      
      // 强制设置样式
      targetParagraph.setAttribute('style', styleOverride);
      
      // 同时注入CSS到页面头部，确保最高优先级
      const styleId = 'highlight-override-style';
      let existingStyle = document.getElementById(styleId);
      if (existingStyle) {
        existingStyle.remove();
      }
      
      const styleElement = document.createElement('style');
      styleElement.id = styleId;
      styleElement.textContent = `
        [data-highlighted="true"] {
          background-color: ${bgColor} !important;
          color: white !important;
          border: 3px solid ${borderColor} !important;
          padding: 15px !important;
          border-radius: 10px !important;
          margin: 10px 0 !important;
          box-shadow: 0 6px 12px ${shadowColor} !important;
          font-weight: bold !important;
          transform: scale(1.02) !important;
          z-index: 1000 !important;
          position: relative !important;
          display: block !important;
        }
        
        .ProseMirror [data-highlighted="true"] {
          background-color: ${bgColor} !important;
          color: white !important;
          border: 3px solid ${borderColor} !important;
        }
      `;
      document.head.appendChild(styleElement);
      
      console.log('🎨 应用强制样式覆盖:', styleOverride);
      console.log('💉 注入CSS到页面头部');
      
      targetParagraph.setAttribute('data-highlighted', 'true');
      console.log('✅ 段落最终样式:', targetParagraph.style.cssText);

      // 滚动到目标段落 - 使用多种方法确保可见
      console.log('📍 开始滚动到目标段落');
      
      // 方法1: 标准scrollIntoView
      targetParagraph.scrollIntoView({ 
        behavior: 'smooth', 
        block: 'center',
        inline: 'nearest'
      });
      
      // 方法2: 如果编辑器容器有特殊滚动，也滚动编辑器
      const editorContainer = editorElement.parentElement;
      if (editorContainer && 'scrollTop' in editorContainer) {
        const containerElement = editorContainer as HTMLElement;
        const targetElement = targetParagraph as HTMLElement;
        const targetPosition = targetElement.offsetTop - containerElement.offsetTop - 100;
        containerElement.scrollTo({
          top: targetPosition,
          behavior: 'smooth'
        });
        console.log('📍 同时滚动编辑器容器');
      }
      
      // 方法3: 添加强制闪烁效果
      let flashCount = 0;
      const flashInterval = setInterval(() => {
        if (flashCount >= 8) { // 增加闪烁次数
          clearInterval(flashInterval);
          return;
        }
        
        const htmlElement = targetParagraph as HTMLElement;
        if (flashCount % 2 === 0) {
          htmlElement.style.setProperty('transform', 'scale(1.1)', 'important');
          htmlElement.style.setProperty('opacity', '0.7', 'important');
        } else {
          htmlElement.style.setProperty('transform', 'scale(1.02)', 'important');
          htmlElement.style.setProperty('opacity', '1', 'important');
        }
        flashCount++;
      }, 150);

      console.log(`✅ 成功高亮段落，已添加闪烁效果`);
    } else {
      console.warn(`❌ 未找到匹配的段落，总共有 ${paragraphs.length} 个段落`);
    }
  }, []);

  /**
   * 清除所有段落高亮
   * Clear all paragraph highlights
   */
  const clearParagraphHighlights = useCallback(() => {
    // 使用多种选择器查找高亮元素
    const selectors = [
      '[data-highlighted="true"]',
      '.ProseMirror [data-highlighted="true"]',
      '.tiptap [data-highlighted="true"]',
      'div[contenteditable] [data-highlighted="true"]'
    ];
    
    let totalCleared = 0;
    
    selectors.forEach(selector => {
      const elements = document.querySelectorAll(selector);
      console.log(`🔍 使用选择器 "${selector}" 找到 ${elements.length} 个元素`);
      
      elements.forEach(element => {
        // 恢复原始样式
        const originalStyle = element.getAttribute('data-original-style') || '';
        element.setAttribute('style', originalStyle);
        
        // 移除标记属性
        element.removeAttribute('data-highlighted');
        element.removeAttribute('data-original-style');
        
        console.log('🧹 清除高亮:', element);
        totalCleared++;
      });
    });
    
    console.log(`🧹 总共清除 ${totalCleared} 个高亮段落`);
    
    // 移除所有注入的样式
    const injectedStyles = document.querySelectorAll('style[id^="highlight-style-"], #highlight-override-style');
    console.log(`🗑️ 移除 ${injectedStyles.length} 个注入的样式`);
    injectedStyles.forEach(style => {
      style.remove();
      console.log('🗑️ 移除样式:', style.id);
    });
    
    console.log('✅ 高亮清除完成');
  }, []);

  /**
   * 通过精确文本匹配高亮元素
   * Highlight element by exact text matching
   */
  const highlightByExactText = useCallback((editorElement: Element, exactText: string, severity: 'high' | 'medium' | 'low'): boolean => {
    console.log(`🔍 搜索精确文本: "${exactText}"`);
    
    // 获取所有文本节点
    const walker = document.createTreeWalker(
      editorElement,
      NodeFilter.SHOW_TEXT,
      null
    );
    
    const textNodes: Text[] = [];
    let node;
    while (node = walker.nextNode()) {
      textNodes.push(node as Text);
    }
    
    console.log(`📝 找到 ${textNodes.length} 个文本节点`);
    
    // 清理函数：移除多余空白，标准化文本
    const normalizeText = (text: string) => {
      return text.replace(/\s+/g, ' ').trim().toLowerCase();
    };
    
    const normalizedTarget = normalizeText(exactText);
    console.log(`🎯 标准化目标文本: "${normalizedTarget.substring(0, 100)}..."`);
    
    // 方法1: 在每个段落元素中搜索
    const paragraphs = editorElement.querySelectorAll('p, h1, h2, h3, h4, h5, h6');
    for (const paragraph of paragraphs) {
      const paragraphText = paragraph.textContent || '';
      const normalizedParagraph = normalizeText(paragraphText);
      
      // 检查是否包含目标文本
      if (normalizedParagraph.includes(normalizedTarget)) {
        console.log(`✅ 在段落中找到匹配: "${paragraphText.substring(0, 50)}..."`);
        highlightElement(paragraph as HTMLElement, severity);
        return true;
      }
      
      // 检查部分匹配（80%以上相似度）
      const similarity = calculateSimilarity(normalizedTarget, normalizedParagraph);
      if (similarity > 0.8) {
        console.log(`🎯 找到高相似度匹配 (${(similarity * 100).toFixed(1)}%): "${paragraphText.substring(0, 50)}..."`);
        highlightElement(paragraph as HTMLElement, severity);
        return true;
      }
    }
    
    // 方法2: 跨段落文本搜索
    const fullText = editorElement.textContent || '';
    const normalizedFullText = normalizeText(fullText);
    
    if (normalizedFullText.includes(normalizedTarget)) {
      console.log('🎯 在完整文本中找到匹配，尝试定位到具体段落');
      
      // 找到最佳匹配的段落
      let bestMatch: { element: Element; score: number } | null = null;
      
      for (const paragraph of paragraphs) {
        const paragraphText = normalizeText(paragraph.textContent || '');
        const score = calculateSimilarity(normalizedTarget, paragraphText);
        
        if (score > 0.3 && (!bestMatch || score > bestMatch.score)) {
          bestMatch = { element: paragraph, score };
        }
      }
      
      if (bestMatch) {
        console.log(`🎯 找到最佳匹配段落 (相似度: ${(bestMatch.score * 100).toFixed(1)}%)`);
        highlightElement(bestMatch.element as HTMLElement, severity);
        return true;
      }
    }
    
    console.log('❌ 精确文本匹配失败');
    return false;
  }, []);

  /**
   * 计算两个字符串的相似度
   */
  const calculateSimilarity = (str1: string, str2: string): number => {
    if (str1 === str2) return 1;
    if (str1.length === 0 || str2.length === 0) return 0;
    
    // 简单的包含关系检查
    if (str2.includes(str1) || str1.includes(str2)) {
      return Math.min(str1.length, str2.length) / Math.max(str1.length, str2.length);
    }
    
    // Levenshtein距离的简化版本
    const longer = str1.length > str2.length ? str1 : str2;
    const shorter = str1.length > str2.length ? str2 : str1;
    
    if (longer.length === 0) return 1;
    
    const editDistance = levenshteinDistance(longer, shorter);
    return (longer.length - editDistance) / longer.length;
  };

  /**
   * 计算编辑距离
   */
  const levenshteinDistance = (str1: string, str2: string): number => {
    const matrix = [];
    
    for (let i = 0; i <= str2.length; i++) {
      matrix[i] = [i];
    }
    
    for (let j = 0; j <= str1.length; j++) {
      matrix[0][j] = j;
    }
    
    for (let i = 1; i <= str2.length; i++) {
      for (let j = 1; j <= str1.length; j++) {
        if (str2.charAt(i - 1) === str1.charAt(j - 1)) {
          matrix[i][j] = matrix[i - 1][j - 1];
        } else {
          matrix[i][j] = Math.min(
            matrix[i - 1][j - 1] + 1,
            matrix[i][j - 1] + 1,
            matrix[i - 1][j] + 1
          );
        }
      }
    }
    
    return matrix[str2.length][str1.length];
  };

  /**
   * 高亮单个元素
   */
  const highlightElement = useCallback((element: HTMLElement, severity: 'high' | 'medium' | 'low') => {
    console.log(`🎨 高亮元素: "${element.textContent?.substring(0, 30)}..."`);
    
    const colors = {
      high: { bg: '#fca5a5', border: '#dc2626', text: '#7f1d1d' },
      medium: { bg: '#fcd34d', border: '#f59e0b', text: '#78350f' },
      low: { bg: '#93c5fd', border: '#3b82f6', text: '#1e3a8a' }
    };
    
    const color = colors[severity];
    
    // 创建强制CSS样式覆盖
    const styleId = 'exact-text-highlight-override';
    let existingStyle = document.getElementById(styleId);
    if (existingStyle) {
      existingStyle.remove();
    }
    
    const styleElement = document.createElement('style');
    styleElement.id = styleId;
    styleElement.textContent = `
      /* 超强力选择器 - 覆盖所有可能的TipTap样式 */
      .ProseMirror [data-highlighted="true"],
      .tiptap [data-highlighted="true"],
      div[contenteditable="true"] [data-highlighted="true"],
      div[role="textbox"] [data-highlighted="true"],
      [data-highlighted="true"],
      body [data-highlighted="true"],
      html [data-highlighted="true"] {
        background-color: ${color.bg} !important;
        background: ${color.bg} !important;
        color: ${color.text} !important;
        border: 6px solid ${color.border} !important;
        border-left: 10px solid ${color.border} !important;
        padding: 16px 20px !important;
        margin: 12px 0 !important;
        border-radius: 12px !important;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3) !important;
        font-weight: 900 !important;
        transform: translateX(10px) scale(1.03) !important;
        position: relative !important;
        z-index: 9999 !important;
        transition: all 0.3s ease !important;
        outline: 4px solid ${color.border}88 !important;
        outline-offset: 2px !important;
        text-shadow: 1px 1px 2px rgba(255,255,255,0.8) !important;
      }
      
      /* 更强的伪元素选择器 */
      .ProseMirror [data-highlighted="true"]::before,
      [data-highlighted="true"]::before {
        content: '🎯 AI建议' !important;
        position: absolute !important;
        top: -35px !important;
        left: -5px !important;
        background: ${color.border} !important;
        color: white !important;
        padding: 6px 12px !important;
        border-radius: 6px !important;
        font-size: 14px !important;
        font-weight: bold !important;
        z-index: 10000 !important;
        animation: bounce-pointer 1.5s ease-in-out infinite !important;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3) !important;
      }
      
      /* 背景光晕效果 */
      .ProseMirror [data-highlighted="true"]::after,
      [data-highlighted="true"]::after {
        content: '' !important;
        position: absolute !important;
        top: -8px !important;
        left: -8px !important;
        right: -8px !important;
        bottom: -8px !important;
        background: linear-gradient(45deg, ${color.border}44, ${color.border}88, ${color.border}44) !important;
        border-radius: 16px !important;
        z-index: -1 !important;
        animation: pulse-glow 2s ease-in-out infinite !important;
      }
      
      @keyframes bounce-pointer {
        0%, 100% { transform: translateY(0) translateX(0); }
        50% { transform: translateY(-3px) translateX(-2px); }
      }
      
      @keyframes pulse-glow {
        0%, 100% { opacity: 0.6; transform: scale(1); }
        50% { opacity: 1; transform: scale(1.02); }
      }
    `;
    document.head.appendChild(styleElement);
    
    // 保存原始样式
    element.setAttribute('data-original-style', element.getAttribute('style') || '');
    element.setAttribute('data-highlighted', 'true');
    
    // 直接设置内联样式作为最强备用方案
    const forceStyle = `
      background-color: ${color.bg} !important;
      color: ${color.text} !important;
      border: 6px solid ${color.border} !important;
      border-left: 10px solid ${color.border} !important;
      padding: 16px 20px !important;
      margin: 12px 0 !important;
      border-radius: 12px !important;
      box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3) !important;
      font-weight: 900 !important;
      transform: translateX(10px) scale(1.03) !important;
      position: relative !important;
      z-index: 9999 !important;
      outline: 4px solid ${color.border}88 !important;
      outline-offset: 2px !important;
    `;
    element.setAttribute('style', forceStyle);
    
    // 使用setProperty强制设置关键样式
    element.style.setProperty('background-color', color.bg, 'important');
    element.style.setProperty('color', color.text, 'important');
    element.style.setProperty('border', `6px solid ${color.border}`, 'important');
    element.style.setProperty('border-left', `10px solid ${color.border}`, 'important');
    element.style.setProperty('padding', '16px 20px', 'important');
    element.style.setProperty('border-radius', '12px', 'important');
    element.style.setProperty('box-shadow', '0 8px 25px rgba(0, 0, 0, 0.3)', 'important');
    element.style.setProperty('font-weight', '900', 'important');
    element.style.setProperty('transform', 'translateX(10px) scale(1.03)', 'important');
    element.style.setProperty('z-index', '9999', 'important');
    element.style.setProperty('position', 'relative', 'important');
    
    console.log(`🎨 强制应用样式到元素:`, element);
    console.log(`🎨 最终样式:`, element.style.cssText);
    
    // 滚动到目标元素
    element.scrollIntoView({ 
      behavior: 'smooth', 
      block: 'center' 
    });
    
    // 强化闪烁动画 - 确保视觉反馈
    let flashCount = 0;
    const flashAnimation = setInterval(() => {
      if (flashCount >= 6) { // 增加闪烁次数
        clearInterval(flashAnimation);
        // 闪烁结束后确保样式还在
        element.style.setProperty('background-color', color.bg, 'important');
        element.style.setProperty('transform', 'translateX(10px) scale(1.03)', 'important');
        return;
      }
      
      if (flashCount % 2 === 0) {
        // 闪烁时使用更明显的样式
        element.style.setProperty('background-color', color.border, 'important');
        element.style.setProperty('transform', 'translateX(15px) scale(1.08)', 'important');
        element.style.setProperty('box-shadow', `0 12px 35px rgba(0, 0, 0, 0.5)`, 'important');
      } else {
        // 恢复原高亮样式
        element.style.setProperty('background-color', color.bg, 'important');
        element.style.setProperty('transform', 'translateX(10px) scale(1.03)', 'important');
        element.style.setProperty('box-shadow', '0 8px 25px rgba(0, 0, 0, 0.3)', 'important');
      }
      flashCount++;
    }, 250); // 稍微加快闪烁速度
  }, []);

  /**
   * 通过精确文本匹配高亮编辑器中的段落
   * Highlight paragraph in editor by exact text matching
   */
  const highlightParagraphByIndex = useCallback((suggestion: AISuggestion) => {
    const { paragraph: paragraphIndex, severity, text: exactText } = suggestion;
    console.log(`🎯 开始高亮段落 ${paragraphIndex}，严重程度: ${severity}`);
    if (exactText) {
      console.log(`🔍 精确文本: "${exactText.substring(0, 100)}..."`);
    }
    
    // 获取编辑器容器
    const editorElement = document.querySelector('.ProseMirror');
    if (!editorElement) {
      console.warn('❌ 编辑器元素未找到');
      return;
    }

    // 清除之前的高亮
    clearParagraphHighlights();

    // 优先使用精确文本匹配
    if (exactText && exactText.trim().length > 0) {
      console.log('🎯 使用精确文本匹配模式');
      const success = highlightByExactText(editorElement, exactText, severity);
      if (success) {
        console.log('✅ 精确文本匹配成功');
        return;
      } else {
        console.log('⚠️ 精确文本匹配失败，fallback到段落索引模式');
      }
    }

    // Fallback: 特殊处理：检查建议描述是否包含claim号
    let targetClaimNumber: number | null = null;
    const claimMatch = suggestion.description.match(/[Cc]laim\s+(\d+)/);
    if (claimMatch) {
      targetClaimNumber = parseInt(claimMatch[1]);
      console.log(`📋 从建议描述中提取到 Claim ${targetClaimNumber}`);
    }

    // 获取所有段落元素并按claim分组
    const allParagraphs = editorElement.querySelectorAll('p, h1, h2, h3, h4, h5, h6');
    const claims: { claimNumber: number; elements: HTMLElement[] }[] = [];
    let currentClaim: { claimNumber: number; elements: HTMLElement[] } | null = null;
    
    // 过滤掉标题（如 "Claims", "Claim", "#Claims" 等）
    const validParagraphs = Array.from(allParagraphs).filter(p => {
      const text = p.textContent?.trim() || '';
      // 排除单独的标题词
      const isTitle = /^(claims?|#claims?)$/i.test(text);
      return !isTitle && text.length > 0;
    });
    
    console.log(`📝 过滤前: ${allParagraphs.length} 个元素，过滤后: ${validParagraphs.length} 个有效段落`);
    
    validParagraphs.forEach((p) => {
      const text = p.textContent?.trim() || '';
      const claimStartMatch = text.match(/^(\d+)\.\s/);
      
      if (claimStartMatch) {
        // 新的claim开始
        const claimNum = parseInt(claimStartMatch[1]);
        currentClaim = { claimNumber: claimNum, elements: [p as HTMLElement] };
        claims.push(currentClaim);
        console.log(`🔢 找到 Claim ${claimNum}: "${text.substring(0, 50)}..."`);
      } else if (currentClaim && text.length > 0) {
        // 添加到当前claim
        currentClaim.elements.push(p as HTMLElement);
      }
    });
    
    console.log(`📝 找到 ${claims.length} 个claims，共 ${allParagraphs.length} 个段落元素`);

    // 查找目标claim
    let targetElements: HTMLElement[] = [];
    
    if (targetClaimNumber) {
      // 如果从描述中提取到了claim号，使用它
      const targetClaim = claims.find(c => c.claimNumber === targetClaimNumber);
      if (targetClaim) {
        targetElements = targetClaim.elements;
        console.log(`✅ 通过claim号找到目标: Claim ${targetClaimNumber}，包含 ${targetElements.length} 个元素`);
      }
    } else {
      // 否则使用段落索引（作为行号）- 使用过滤后的段落
      const targetParagraph = validParagraphs[paragraphIndex - 1] as HTMLElement;
      if (targetParagraph) {
        targetElements = [targetParagraph];
        console.log(`✅ 通过行号找到目标: 第 ${paragraphIndex} 行 (过滤后)`);
      }
    }

    if (targetElements.length > 0) {
      console.log(`🎨 开始高亮 ${targetElements.length} 个元素`);
      
      // 使用更明显的高亮样式
      const colors = {
        high: { bg: '#fca5a5', border: '#dc2626', text: '#7f1d1d' },
        medium: { bg: '#fcd34d', border: '#f59e0b', text: '#78350f' },
        low: { bg: '#93c5fd', border: '#3b82f6', text: '#1e3a8a' }
      };
      
      const color = colors[severity];
      
      // 创建强制CSS样式覆盖
      const styleId = 'claim-highlight-override';
      let existingStyle = document.getElementById(styleId);
      if (existingStyle) {
        existingStyle.remove();
      }
      
      const styleElement = document.createElement('style');
      styleElement.id = styleId;
      styleElement.textContent = `
        /* 最强力的选择器覆盖 TipTap 样式 */
        .ProseMirror [data-highlighted="true"],
        .tiptap [data-highlighted="true"],
        div[contenteditable] [data-highlighted="true"],
        [data-highlighted="true"] {
          background: ${color.bg} !important;
          color: ${color.text} !important;
          border-left: 10px solid ${color.border} !important;
          border-right: 4px solid ${color.border} !important;
          border-top: 2px solid ${color.border} !important;
          border-bottom: 2px solid ${color.border} !important;
          padding: 15px 20px !important;
          margin: 12px 0 !important;
          border-radius: 12px !important;
          box-shadow: 0 6px 20px rgba(0, 0, 0, 0.25) !important;
          transform: translateX(8px) scale(1.02) !important;
          font-weight: 700 !important;
          font-size: 16px !important;
          line-height: 1.5 !important;
          text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.9) !important;
          position: relative !important;
          z-index: 999 !important;
          transition: all 0.3s ease !important;
          outline: 3px solid ${color.border}66 !important;
          outline-offset: 4px !important;
        }
        
        /* 脉冲动画 */
        [data-highlighted="true"]::before {
          content: '👈 AI建议';
          position: absolute;
          left: -60px;
          top: 50%;
          transform: translateY(-50%);
          background: ${color.border};
          color: white;
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 12px;
          font-weight: bold;
          z-index: 1000;
          animation: bounce-pointer 1.5s ease-in-out infinite;
        }
        
        @keyframes bounce-pointer {
          0%, 100% { transform: translateY(-50%) translateX(0); }
          50% { transform: translateY(-50%) translateX(-5px); }
        }
        
        /* 闪烁边框动画 */
        [data-highlighted="true"]::after {
          content: '';
          position: absolute;
          top: -6px;
          left: -6px;
          right: -6px;
          bottom: -6px;
          border: 3px solid ${color.border};
          border-radius: 16px;
          z-index: -1;
          animation: pulse-border 2s ease-in-out infinite;
        }
        
        @keyframes pulse-border {
          0%, 100% { opacity: 0.5; transform: scale(1); }
          50% { opacity: 1; transform: scale(1.05); }
        }
      `;
      document.head.appendChild(styleElement);
      console.log('💉 注入强制高亮CSS样式');

      // 高亮所有相关元素
      targetElements.forEach((element, index) => {
        // 保存原始样式和类名
        element.setAttribute('data-original-style', element.getAttribute('style') || '');
        element.setAttribute('data-original-class', element.className || '');
        
        // 直接设置内联样式作为备用
        const directStyle = `
          background: ${color.bg} !important;
          color: ${color.text} !important;
          border-left: 8px solid ${color.border} !important;
          padding: 12px 16px !important;
          margin: 8px 0 !important;
          border-radius: 8px !important;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
          font-weight: 600 !important;
          transform: translateX(4px) !important;
          position: relative !important;
          z-index: 10 !important;
        `;
        
        element.setAttribute('style', directStyle);
        element.setAttribute('data-highlighted', 'true');
        
        // 添加闪烁动画吸引注意力
        let flashCount = 0;
        const flashAnimation = setInterval(() => {
          if (flashCount >= 6) {
            clearInterval(flashAnimation);
            return;
          }
          
          if (flashCount % 2 === 0) {
            element.style.setProperty('background', `${color.border}88`, 'important');
            element.style.setProperty('transform', 'translateX(8px) scale(1.03)', 'important');
          } else {
            element.style.setProperty('background', color.bg, 'important');
            element.style.setProperty('transform', 'translateX(4px) scale(1)', 'important');
          }
          flashCount++;
        }, 200);
        
        console.log(`🎨 高亮元素 ${index + 1}/${targetElements.length}: "${element.textContent?.substring(0, 30)}..."`);
        console.log(`🎯 应用的样式:`, directStyle);
      });

      // 滚动到第一个元素
      targetElements[0].scrollIntoView({ 
        behavior: 'smooth', 
        block: 'center' 
      });

      console.log(`✅ 成功高亮 ${targetClaimNumber ? `Claim ${targetClaimNumber}` : `第 ${paragraphIndex} 行`}`);
    } else {
      console.warn(`❌ 未找到目标（查找: ${targetClaimNumber ? `Claim ${targetClaimNumber}` : `第 ${paragraphIndex} 行`}）`);
    }
  }, []);

  /**
   * 处理建议卡片点击事件
   * Handle suggestion card click
   */
  const handleSuggestionClick = useCallback((suggestion: AISuggestion, index: number) => {
    console.log('🖱️ 点击建议卡片:', suggestion);
    console.log('📍 建议信息:', {
      paragraph: suggestion.paragraph,
      severity: suggestion.severity,
      type: suggestion.type,
      description: suggestion.description.substring(0, 100) + '...'
    });
    
    // 清除之前的定时器
    if (highlightTimerRef.current) {
      clearTimeout(highlightTimerRef.current);
      highlightTimerRef.current = null;
    }
    
    // 设置当前激活的建议
    setActiveHighlightIndex(index);
    
    // 直接使用段落索引高亮
    highlightParagraphByIndex(suggestion);
    
    // 3秒后自动清除高亮和激活状态
    highlightTimerRef.current = setTimeout(() => {
      console.log('⏰ 3秒后自动清除高亮');
      clearParagraphHighlights();
      setActiveHighlightIndex(null);
      highlightTimerRef.current = null;
    }, 3000);
  }, [highlightParagraphByIndex, clearParagraphHighlights]);

  // 组件卸载时清理定时器
  useEffect(() => {
    return () => {
      if (highlightTimerRef.current) {
        clearTimeout(highlightTimerRef.current);
      }
    };
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

  /**
   * 手动触发AI分析
   * Manually trigger AI analysis
   */
  const [manualAnalysisFunction, setManualAnalysisFunction] = useState<(() => void) | null>(null);
  
  const triggerAIAnalysis = () => {
    if (manualAnalysisFunction) {
      manualAnalysisFunction();
    } else {
      console.warn('AI分析函数未就绪');
    }
  };

  const registerManualAnalysis = useCallback((analysisFunction: () => void) => {
    setManualAnalysisFunction(() => analysisFunction);
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
                {/* 标题和AI开关 */}
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold text-gray-800">AI 建议</h3>
                  <div className="flex items-center gap-3">
                    {/* AI处理状态指示器 */}
                    {appState.isAIProcessing && (
                      <div className="flex items-center text-blue-600">
                        <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse mr-2"></div>
                        <span className="text-xs">分析中...</span>
                      </div>
                    )}
                    
                    {/* AI分析按钮 */}
                    <button
                      onClick={triggerAIAnalysis}
                      disabled={appState.isAIProcessing}
                      className={`px-3 py-1.5 text-xs font-medium rounded-full transition-all duration-200 ${
                        appState.isAIProcessing
                          ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                          : 'bg-blue-600 text-white hover:bg-blue-700'
                      }`}
                      aria-label="AI分析文档"
                    >
                      {appState.isAIProcessing ? '🔄 分析中...' : '🤖 AI分析'}
                    </button>
                  </div>
                </div>

                {/* AI建议列表 */}
                {appState.aiSuggestions.length > 0 ? (
                  <div className="space-y-3">
                    {appState.aiSuggestions.map((suggestion, index) => (
                      <div
                        key={index}
                        onClick={() => handleSuggestionClick(suggestion, index)}
                        className={`p-3 rounded-lg border-l-4 cursor-pointer hover:shadow-lg transition-all duration-200 ${
                          activeHighlightIndex === index
                            ? 'ring-2 ring-offset-2 ring-gray-400 shadow-lg' // 激活状态
                            : ''
                        } ${
                          suggestion.severity === 'high'
                            ? 'border-red-500 bg-red-50 hover:bg-red-100'
                            : suggestion.severity === 'medium'
                            ? 'border-yellow-500 bg-yellow-50 hover:bg-yellow-100'
                            : 'border-blue-500 bg-blue-50 hover:bg-blue-100'
                        }`}
                        title="点击高亮对应段落"
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
