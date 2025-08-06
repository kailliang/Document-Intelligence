import Document from "./Document";
import { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";
import LoadingOverlay from "./internal/LoadingOverlay";
import Logo from "./assets/logo.png";
import ChatPanel from "./ChatPanel";
import { findTextInDocument, replaceText } from "./internal/HighlightExtension";
import TurndownService from "turndown";

const BACKEND_URL = "http://localhost:8000";


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

interface DocumentListItem {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

// AI suggestion related interfaces
interface AISuggestion {
  type: string;
  severity: 'high' | 'medium' | 'low';
  paragraph: number;
  description: string;
  text?: string;  // Added: precise original text
  suggestion: string;
  originalText?: string;  // Added: original text (for precise matching)
  replaceTo?: string;     // Added: suggested replacement text
  confidence?: number;     // Added: confidence score (0-1)
  confidence_factors?: {   // Added: factors affecting confidence (for debugging)
    text_length: number;
    issue_type: string;
    has_detailed_replacement: boolean;
  };
}

interface DiagramInsertion {
  insert_after_text: string;
  mermaid_syntax: string;
  diagram_type: string;
  title?: string;
}

interface AppState {
  currentDocument: DocumentWithCurrentVersion | null;
  availableDocuments: DocumentListItem[];    // Added: available documents list
  documentVersions: DocumentVersion[];
  isLoading: boolean;
  leftSidebarCollapsed: boolean;
  rightSidebarCollapsed: boolean;
  hasUnsavedChanges: boolean;  // Track whether there are unsaved changes
  aiSuggestions: AISuggestion[];  // AI suggestions
  aiProcessingStatus: string;     // AI processing status message
  isAIProcessing: boolean;        // Whether AI is processing
  deleteDialog: {                 // Delete confirmation dialog state
    isOpen: boolean;
    versionNumber: number | null;
  };
  activeRightTab: 'suggestions' | 'chat';  // Active right sidebar tab
}

function App() {
  // Integrated state management
  const [appState, setAppState] = useState<AppState>({
    currentDocument: null,
    availableDocuments: [],
    documentVersions: [],
    isLoading: false,
    leftSidebarCollapsed: false,
    rightSidebarCollapsed: false,
    hasUnsavedChanges: false,
    aiSuggestions: [],
    aiProcessingStatus: "AI assistant is off",
    isAIProcessing: false,
    deleteDialog: {
      isOpen: false,
      versionNumber: null
    },
    activeRightTab: 'suggestions'
  });

  // Responsive layout detection
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);

  useEffect(() => {
    const handleResize = () => {
      const mobile = window.innerWidth < 768;
      setIsMobile(mobile);

      // Auto-collapse sidebars on mobile
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

  // Highlight clear timer reference
  const highlightTimerRef = useRef<number | null>(null);

  // TipTap editor instance reference
  const editorRef = useRef<any>(null);

  /**
   * Handle document content changes and mark as unsaved
   */
  const handleContentChange = (newContent: string) => {
    setCurrentDocumentContent(newContent);

    // Clear paragraph highlights and timers when content changes
    if (editorRef.current) {
      editorRef.current.commands.clearTemporaryHighlights();
    }
    setActiveHighlightIndex(null);
    if (highlightTimerRef.current) {
      clearTimeout(highlightTimerRef.current);
      highlightTimerRef.current = null;
    }

    // If content differs from current document content, mark as having unsaved changes
    if (appState.currentDocument && newContent !== appState.currentDocument.content) {
      setAppState(prev => ({ ...prev, hasUnsavedChanges: true }));
    } else {
      setAppState(prev => ({ ...prev, hasUnsavedChanges: false }));
    }
  };

  /**
   * Load all available documents list
   */
  const loadDocumentsList = useCallback(async () => {
    try {
      console.log('📂 Starting to fetch document list...');
      setAppState(prev => ({ ...prev, isLoading: true }));
      
      const response = await axios.get(`${BACKEND_URL}/api/documents`);
      setAppState(prev => ({ 
        ...prev, 
        availableDocuments: response.data,
        isLoading: false
      }));
      console.log('✅ Document list fetched successfully:', response.data);
    } catch (error) {
      console.error('❌ Document list fetch failed:', error);
      setAppState(prev => ({ ...prev, isLoading: false }));
      // Consider adding error notification for user
    }
  }, []);

  // Load document list when component mounts
  useEffect(() => {
    loadDocumentsList();
  }, [loadDocumentsList]);

  /**
   * Load a patent document with version control support
   */
  const loadPatent = async (documentNumber: number) => {
    setAppState(prev => ({ ...prev, isLoading: true }));
    console.log("Loading patent with versions:", documentNumber);

    try {
      // Get document current version content (backward compatible)
      const documentResponse = await axios.get(`${BACKEND_URL}/document/${documentNumber}`);
      const documentData: DocumentWithCurrentVersion = documentResponse.data;

      // Get all version history
      const versionsResponse = await axios.get(`${BACKEND_URL}/api/documents/${documentNumber}/versions`);
      const versions: DocumentVersion[] = versionsResponse.data;

      setAppState(prev => ({
        ...prev,
        currentDocument: documentData,
        documentVersions: versions,
        isLoading: false,
        hasUnsavedChanges: false,  // Reset unsaved state
        aiSuggestions: [],         // Clear AI suggestions
        aiProcessingStatus: "AI assistant is off"  // Update status message
      }));
      setCurrentDocumentContent(documentData.content);

    } catch (error) {
      console.error("Error loading document:", error);
      setAppState(prev => ({ ...prev, isLoading: false }));
    }
  };

  /**
   * Save the current patent document to the backend (updates current version)
   */
  const savePatent = async (documentNumber: number) => {
    if (!appState.currentDocument) return;

    setAppState(prev => ({ ...prev, isLoading: true }));
    try {
      await axios.post(`${BACKEND_URL}/save/${documentNumber}`, {
        content: currentDocumentContent,
      });

      // Update document's last modified time and reset unsaved state
      setAppState(prev => ({
        ...prev,
        currentDocument: prev.currentDocument ? {
          ...prev.currentDocument,
          last_modified: new Date().toISOString(),
        } : null,
        isLoading: false,
        hasUnsavedChanges: false  // Reset unsaved state after saving
      }));

      // Trigger document save event for Mermaid chart re-rendering
      window.dispatchEvent(new CustomEvent('document-saved'));

    } catch (error) {
      console.error("Error saving document:", error);
      setAppState(prev => ({ ...prev, isLoading: false }));
    }
  };

  /**
   * Create a new version of the document
   */
  const createNewVersion = async () => {
    if (!appState.currentDocument) return;

    setAppState(prev => ({ ...prev, isLoading: true }));
    try {
      // Create new version (empty document)
      await axios.post(`${BACKEND_URL}/api/documents/${appState.currentDocument.id}/versions`, {});

      // Reload document and version history
      await loadPatent(appState.currentDocument.id);

    } catch (error) {
      console.error("Error creating new version:", error);
      setAppState(prev => ({ ...prev, isLoading: false }));
    }
  };

  /**
   * Switch to a specific version
   */
  const switchToVersion = async (versionNumber: number) => {
    if (!appState.currentDocument) return;

    setAppState(prev => ({ ...prev, isLoading: true }));
    try {
      // Switch version
      const response = await axios.post(`${BACKEND_URL}/api/documents/${appState.currentDocument.id}/switch-version`, {
        version_number: versionNumber,
      });

      const updatedDocument: DocumentWithCurrentVersion = response.data;

      setAppState(prev => ({
        ...prev,
        currentDocument: updatedDocument,
        isLoading: false,
        hasUnsavedChanges: false,  // Reset unsaved state after version switch
        aiSuggestions: [],         // Clear AI suggestions
        aiProcessingStatus: "AI assistant is off"  // Update status message
      }));
      setCurrentDocumentContent(updatedDocument.content);

      // Reload version list to update active status
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
   * Delete a specific version
   * Delete a specific version
   */
  // Open delete confirmation dialog
  const openDeleteDialog = (versionNumber: number) => {
    setAppState(prev => ({
      ...prev,
      deleteDialog: {
        isOpen: true,
        versionNumber
      }
    }));
  };

  // Close delete confirmation dialog
  const closeDeleteDialog = () => {
    setAppState(prev => ({
      ...prev,
      deleteDialog: {
        isOpen: false,
        versionNumber: null
      }
    }));
  };

  // Confirm version deletion
  const confirmDeleteVersion = async () => {
    if (!appState.currentDocument || !appState.deleteDialog.versionNumber) return;

    const versionNumber = appState.deleteDialog.versionNumber;
    closeDeleteDialog();

    setAppState(prev => ({ ...prev, isLoading: true }));
    try {
      // Delete version
      await axios.delete(`${BACKEND_URL}/api/documents/${appState.currentDocument.id}/versions/${versionNumber}`);

      // Reload document and version history
      await loadPatent(appState.currentDocument.id);

    } catch (error: any) {
      console.error("Error deleting version:", error);
      // Display error message
      const errorMessage = error.response?.data?.detail || "Version deletion failed";
      alert(errorMessage);
      setAppState(prev => ({ ...prev, isLoading: false }));
    }
  };

  /**
   * Handle AI suggestions from WebSocket
   */
  const handleAISuggestions = useCallback((suggestions: AISuggestion[]) => {
    console.log("🎯 Updating AI suggestions:", suggestions.length, "suggestions");
    setAppState(prev => {
      // Prevent duplicate setting of same suggestions
      if (JSON.stringify(prev.aiSuggestions) === JSON.stringify(suggestions)) {
        console.log("🔄 Suggestions unchanged, skipping update");
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
   * Handle AI processing status updates
   */
  const handleAIProcessingStatus = useCallback((isProcessing: boolean, message?: string) => {
    console.log("📊 AI status update:", { isProcessing, message });
    setAppState(prev => ({
      ...prev,
      isAIProcessing: isProcessing,
      aiProcessingStatus: message || (isProcessing ? "AI analysing..." : "AI standby")
    }));
  }, []);

  /**
   * Highlight paragraph in editor by matching text content
   */
  const highlightParagraphByText = useCallback((suggestion: AISuggestion) => {
    console.log(`🎯 Starting text-based paragraph highlighting, severity: ${suggestion.severity}`);

    if (!editorRef.current) {
      console.warn('❌ Editor instance not found');
      return;
    }

    const editor = editorRef.current;

    // Use ProseMirror API for text matching and highlighting
    if (suggestion.originalText || suggestion.text) {
      const searchText = suggestion.originalText || suggestion.text || '';
      const position = findTextInDocument(editor.state.doc, searchText);

      if (position) {
        // Clear previous highlights
        editor.commands.clearTemporaryHighlights();
        // Add temporary highlight
        editor.commands.addTemporaryHighlight(position.from, position.to, suggestion.severity);

        // Wait for highlight decoration to render then scroll to center position
        setTimeout(() => {
          if (editorRef.current) {
            // Find highlight element through CSS selector
            const highlightElement = editorRef.current.view.dom.querySelector(
              `.temporary-highlight-${suggestion.severity}`
            );

            if (highlightElement) {
              // Find the actual scroll container and check element visibility
              const scrollContainer = findScrollContainer(highlightElement);
              const containerRect = scrollContainer.getBoundingClientRect();
              const elementRect = highlightElement.getBoundingClientRect();

              // Calculate visibility relative to scroll container
              const isVisible =
                elementRect.top >= containerRect.top &&
                elementRect.bottom <= containerRect.bottom;

              // Add debug information
              console.log('📊 Visibility debug info:', {
                scrollContainer: scrollContainer.className || scrollContainer.tagName,
                containerRect: { top: containerRect.top, bottom: containerRect.bottom, height: containerRect.height },
                elementRect: { top: elementRect.top, bottom: elementRect.bottom, height: elementRect.height },
                isVisible
              });

              // Directly judge visibility using viewport coordinates - simple and clear
              const isInViewport =
                elementRect.bottom > 0 &&
                elementRect.top < window.innerHeight;

              // Check if there's enough visible content (at least 20px)
              const visibleHeight = Math.min(elementRect.bottom, window.innerHeight) - Math.max(elementRect.top, 0);
              const hasEnoughVisible = visibleHeight >= 20;

              console.log('📊 Simplified visibility check:', {
                elementRect,
                isInViewport,
                visibleHeight,
                hasEnoughVisible,
                windowHeight: window.innerHeight
              });

              if (isInViewport && hasEnoughVisible) {
                console.log('✅ Element is in viewport with sufficient visible content, no scrolling needed');
              } else {
                // Element not in viewport or insufficient visible content - need to scroll to reasonable position
                console.log('📊 Element needs to be scrolled to visible position');

                highlightElement.scrollIntoView({
                  behavior: 'smooth',
                  block: 'center',
                  inline: 'nearest'
                });
                console.log('✅ Scrolled to center position');
              }
            } else {
              console.warn('❌ Highlight element not found, using fallback scroll method');
              // Fallback: set cursor position to trigger scrolling
              editorRef.current.commands.setTextSelection(position.from);
            }
          }
        }, 100); // Increase delay to ensure highlight decoration is rendered

        console.log(`✅ Successfully highlighted text: "${searchText.substring(0, 50)}..."`);
      } else {
        console.warn(`❌ Text not found: "${searchText.substring(0, 50)}..."`);
      }
    }
  }, []);

  /**
   * Handle suggestion card click
   */
  const handleSuggestionClick = useCallback((suggestion: AISuggestion, index: number) => {
    console.log('🖱️ Clicked suggestion card:', suggestion);

    // Clear previous timer
    if (highlightTimerRef.current) {
      clearTimeout(highlightTimerRef.current);
      highlightTimerRef.current = null;
    }

    // Set currently active suggestion
    setActiveHighlightIndex(index);

    // Use text highlighting
    highlightParagraphByText(suggestion);

    // Auto-clear highlights and active state after 3 seconds
    highlightTimerRef.current = setTimeout(() => {
      console.log('⏰ Auto-clear highlights after 3 seconds');
      if (editorRef.current) {
        editorRef.current.commands.clearTemporaryHighlights();
      }
      setActiveHighlightIndex(null);
      highlightTimerRef.current = null;
    }, 3000);
  }, [highlightParagraphByText]);

  // Clean up timers when component unmounts
  useEffect(() => {
    return () => {
      if (highlightTimerRef.current) {
        clearTimeout(highlightTimerRef.current);
      }
    };
  }, []);

  /**
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
        console.log('🔍 Found scroll container:', parent.className || parent.tagName);
        return parent;
      }
      parent = parent.parentElement;
    }
    console.log('🔍 No scroll container found, using document.documentElement');
    return document.documentElement;
  };

  /**
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
   * Manually trigger AI analysis
   */
  const [manualAnalysisFunction, setManualAnalysisFunction] = useState<(() => void) | null>(null);

  const triggerAIAnalysis = () => {
    if (!appState.currentDocument) {
      console.error('Please select a document first');
      return;
    }

    if (!manualAnalysisFunction) {
      console.warn('AI analysis function not ready, please ensure document is loaded');
      return;
    }

    console.log('🚀 Triggering AI analysis');
    manualAnalysisFunction();
  };

  const registerManualAnalysis = useCallback((analysisFunction: () => void) => {
    console.log('📌 App: Received manual analysis function');
    setManualAnalysisFunction(() => analysisFunction);
  }, []);

  /**
   * Handle editor instance ready
   */
  const handleEditorReady = useCallback((editor: any) => {
    editorRef.current = editor;
    console.log('📝 Editor instance ready', editor);
  }, []);

  /**
   * Handle diagram insertion requests
   */
  const handleDiagramInsertions = useCallback((insertions: DiagramInsertion[]) => {
    console.log('📊 Received diagram insertion requests (auto-insertion disabled):', insertions);
    console.log('📋 Use the Insert button in chat to manually insert diagrams');
    
    // Disabled automatic insertion - diagrams will only be inserted manually via chat Insert button
    // This prevents unwanted automatic line break insertion when AI responds
    
    // if (!editorRef.current) {
    //   console.error('❌ Editor instance not ready');
    //   return;
    // }

    // insertions.forEach((insertion, index) => {
    //   console.log(`📊 Inserting diagram ${index + 1}:`, insertion);

    //   const success = insertDiagramAfterText(
    //     editorRef.current,
    //     insertion.insert_after_text,
    //     insertion.mermaid_syntax,
    //     insertion.title
    //   );

    //   if (success) {
    //     console.log(`✅ Diagram ${index + 1} inserted successfully`);
    //     // Mark document as having unsaved changes
    //     setAppState(prev => ({
    //       ...prev,
    //       hasUnsavedChanges: true
    //     }));
    //   } else {
    //     console.error(`❌ Diagram ${index + 1} insertion failed: cannot find text "${insertion.insert_after_text}"`);
    //   }
    // });
  }, []);

  /**
   * Handle mermaid diagram insertion at cursor position
   */
  const handleInsertMermaid = useCallback((mermaidSyntax: string, title?: string) => {
    console.log('📊 Inserting mermaid diagram at cursor position:', { mermaidSyntax, title });

    if (!editorRef.current) {
      console.error('❌ Editor instance not ready');
      return;
    }

    if (!mermaidSyntax || !mermaidSyntax.trim()) {
      console.error('❌ Empty mermaid syntax provided');
      return;
    }

    try {
      // Use the MermaidExtension's insertMermaidDiagram command
      editorRef.current
        .chain()
        .focus()
        .insertMermaidDiagram({ syntax: mermaidSyntax, title })
        .run();

      console.log('✅ Mermaid diagram inserted successfully');

      // Mark document as having unsaved changes
      setAppState(prev => ({
        ...prev,
        hasUnsavedChanges: true
      }));
    } catch (error) {
      console.error('❌ Mermaid diagram insertion failed:', error);
    }
  }, []);

  /**
   * Export document to PDF using backend API
   */
  const exportToPDF = useCallback(async () => {
    if (!appState.currentDocument) {
      console.error('❌ No document selected');
      alert('Please select a document first');
      return;
    }

    try {
      console.log('📄 Starting backend PDF export...');
      
      // Set export status
      setAppState(prev => ({ ...prev, isLoading: true }));

      // Call backend API to export PDF
      const response = await axios.post(
        `${BACKEND_URL}/api/documents/${appState.currentDocument.id}/export/pdf`,
        {},
        { 
          headers: { 'Content-Type': 'application/json' },
          timeout: 30000 // 30 second timeout
        }
      );

      if (response.data.status === 'success') {
        console.log('✅ PDF export successful:', response.data.filename);
        
        // Create download link and auto-click download
        const downloadUrl = `${BACKEND_URL}${response.data.download_url}`;
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.download = response.data.filename;
        link.target = '_blank';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        // Display success message
        alert(`PDF export successful!\nDocument: ${response.data.document_title}\nVersion: v${response.data.version}`);
      } else {
        throw new Error('PDF export API returned failure status');
      }

    } catch (error: any) {
      console.error('❌ PDF export failed:', error);
      
      let errorMessage = 'PDF export failed, please try again later';
      
      if (error.code === 'ECONNABORTED') {
        errorMessage = 'PDF export timeout, please check network connection or try again later';
      } else if (error.response?.status === 404) {
        errorMessage = 'Document does not exist or has no active version';
      } else if (error.response?.status === 500) {
        errorMessage = 'PDF generation failed, please check document content or contact administrator';
      } else if (error.response?.data?.detail) {
        errorMessage = `PDF export failed: ${error.response.data.detail}`;
      }
      
      alert(errorMessage);
      
    } finally {
      // Clear loading state
      setAppState(prev => ({ ...prev, isLoading: false }));
    }
  }, [appState.currentDocument]);


  /**
   * Export document to markdown
   */
  const exportToMarkdown = useCallback(async () => {
    if (!appState.currentDocument) {
      alert('Please select a document first');
      return;
    }

    if (!editorRef.current) {
      alert('Editor instance not ready');
      return;
    }

    const turndownService = new TurndownService();
    
    // Add custom rule for Mermaid diagrams
    turndownService.addRule('mermaidDiagram', {
      filter: function (node) {
        return (
          node.nodeName === 'DIV' && 
          ((node as Element).getAttribute('data-type') === 'mermaid-diagram' || 
           (node as Element).classList.contains('mermaid-node'))
        );
      },
      replacement: function (_content, node) {
        const element = node as Element;
        const syntax = element.getAttribute('data-syntax');
        const title = element.getAttribute('data-title');
        
        if (syntax) {
          let mermaidBlock = '```mermaid\n' + syntax + '\n```';
          if (title) {
            mermaidBlock = `### ${title}\n\n${mermaidBlock}`;
          }
          return '\n\n' + mermaidBlock + '\n\n';
        }
        return '';
      }
    });
    
    const markdownContent = turndownService.turndown(editorRef.current.getHTML());

    const blob = new Blob([markdownContent], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${appState.currentDocument.title}_v${appState.currentDocument.version_number}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    console.log('✅ Markdown export successful');
  }, [appState.currentDocument]);


  /**
   * Accept AI suggestion and apply to document
   */
  const acceptSuggestion = useCallback((suggestion: AISuggestion, _index: number) => {
    console.log('✅ Accepting suggestion:', suggestion);

    // Use new replacement function - allows replaceTo to be empty string (delete text)
    if (suggestion.originalText && suggestion.replaceTo !== undefined && editorRef.current) {
      const success = replaceText(editorRef.current, suggestion.originalText, suggestion.replaceTo);

      if (success) {
        console.log('✅ Text replacement successful');
      } else {
        console.warn('❌ Text to replace not found:', suggestion.originalText);
        // If this error still occurs, backend deduplication hasn't fully resolved the issue
      }
    } else if (suggestion.text && suggestion.suggestion && editorRef.current) {
      // Compatibility with old format: use text and suggestion fields
      const success = replaceText(editorRef.current, suggestion.text, suggestion.suggestion);

      if (!success) {
        console.warn('❌ Text to replace not found:', suggestion.text);
      }
    }

    // Remove from suggestions list - based on content matching not index, avoiding wrong deletion due to sorting
    setAppState(prev => {
      const newSuggestions = prev.aiSuggestions.filter(s =>
        !(s.originalText === suggestion.originalText &&
          s.paragraph === suggestion.paragraph &&
          s.type === suggestion.type)
      );
      
      // Update status if no suggestions remain
      const newStatus = newSuggestions.length === 0 
        ? 'AI standby' 
        : `AI analysis complete, found ${newSuggestions.length} suggestions`;
      
      return {
        ...prev,
        aiSuggestions: newSuggestions,
        aiProcessingStatus: newStatus
      };
    });
  }, []);

  /**
   * Copy suggestion content to clipboard
   */
  const copySuggestion = useCallback((suggestion: AISuggestion) => {
    const textToCopy = suggestion.replaceTo || suggestion.suggestion;
    navigator.clipboard.writeText(textToCopy).then(() => {
      console.log('📋 Copied to clipboard:', textToCopy);
      // TODO: show success notification
    }).catch(err => {
      console.error('Copy failed:', err);
    });
  }, []);

  /**
   * Close/ignore suggestion
   */
  const closeSuggestion = useCallback((suggestion: AISuggestion) => {
    console.log('❌ Dismissing suggestion:', suggestion.type, 'paragraph', suggestion.paragraph);
    setAppState(prev => {
      const newSuggestions = prev.aiSuggestions.filter(s =>
        !(s.originalText === suggestion.originalText &&
          s.paragraph === suggestion.paragraph &&
          s.type === suggestion.type)
      );
      
      // Update status if no suggestions remain
      const newStatus = newSuggestions.length === 0 
        ? 'AI standby' 
        : `AI analysis complete, found ${newSuggestions.length} suggestions`;
      
      return {
        ...prev,
        aiSuggestions: newSuggestions,
        aiProcessingStatus: newStatus
      };
    });
  }, []);

  return (
    <div className="flex flex-col h-screen w-full bg-gray-50">
      {/* Loading overlay */}
      {appState.isLoading && <LoadingOverlay />}

      {/* Header - maintain original design but optimize styles */}
      <header className="flex items-center justify-center w-full bg-gradient-to-r from-gray-900 to-gray-800 text-white shadow-lg z-50 h-16">
        <img src={Logo} alt="Logo" className="h-10" />
        <h1 className="ml-4 text-xl font-semibold">Patent Review System</h1>
      </header>

      {/* Main content area - three-column layout */}
      <div className="flex flex-1 overflow-hidden">

        {/* Mobile overlay */}
        {isMobile && !appState.leftSidebarCollapsed && (
          <div
            className="mobile-overlay z-40 lg:hidden"
            onClick={() => setAppState(prev => ({ ...prev, leftSidebarCollapsed: true }))}
          />
        )}

        {/* Left sidebar - project and version management area */}
        <aside className={`
          ${appState.leftSidebarCollapsed ? 'w-12' : 'w-80'} 
          ${isMobile && !appState.leftSidebarCollapsed ? 'fixed left-0 top-16 bottom-0 z-50' : 'relative'}
          bg-white border-r border-gray-200 shadow-sm transition-all duration-300 ease-in-out
          flex flex-col
        `}>
          {/* Left sidebar header */}
          <div className="flex items-center justify-between p-4 border-b border-gray-200">
            {!appState.leftSidebarCollapsed && (
              <h2 className="text-lg font-semibold text-gray-800">Projects</h2>
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

          {/* Left sidebar content */}
          {!appState.leftSidebarCollapsed && (
            <div className="flex-1 flex flex-col p-4 overflow-hidden">
              {/* Project selection area */}
              <div className="flex flex-col flex-1 min-h-0">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Project List</h3>
                  <span className="text-xs text-gray-400 flex-shrink-0">{appState.availableDocuments.length} items</span>
                </div>
                <div className="space-y-2 overflow-y-auto flex-1">
                  {appState.availableDocuments.map((doc, index) => (
                    <button
                      key={doc.id}
                      onClick={() => loadPatent(doc.id)}
                      className={`w-full p-3 text-left rounded-lg transition-all duration-200 ${
                        appState.currentDocument?.id === doc.id
                          ? 'bg-blue-50 border-blue-300 border-2'
                          : 'bg-white hover:bg-gray-50 border border-gray-200'
                      }`}
                    >
                      <div className="flex items-center gap-3 w-full">
                        <div className={`w-8 h-8 rounded flex items-center justify-center flex-shrink-0 ${
                          appState.currentDocument?.id === doc.id
                            ? 'bg-blue-100'
                            : 'bg-gray-100'
                        }`}>
                          <svg className={`w-4 h-4 ${
                            appState.currentDocument?.id === doc.id ? 'text-blue-600' : 'text-gray-500'
                          }`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                          </svg>
                        </div>
                        <div className="flex-1 min-w-0" style={{ maxWidth: 'calc(100% - 44px)' }}>
                          <div className={`font-medium text-sm leading-tight ${
                            appState.currentDocument?.id === doc.id ? 'text-blue-700' : 'text-gray-800'
                          }`} 
                          title={doc.title}
                          style={{
                            display: '-webkit-box',
                            WebkitLineClamp: 2,
                            WebkitBoxOrient: 'vertical',
                            overflow: 'hidden',
                            wordBreak: 'break-word',
                            lineHeight: '1.2'
                          }}>
                            {doc.title}
                          </div>
                          <div className={`text-xs mt-1 ${
                            appState.currentDocument?.id === doc.id ? 'text-blue-600' : 'text-gray-500'
                          }`}>
                            Project {index + 1}
                          </div>
                        </div>
                      </div>
                    </button>
                  ))}
                  {appState.isLoading ? (
                    <div className="flex flex-col items-center justify-center py-8">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mb-3"></div>
                      <p className="text-sm text-gray-500">Loading projects...</p>
                    </div>
                  ) : appState.availableDocuments.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-8 px-4">
                      <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
                        <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                            d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                        </svg>
                      </div>
                      <p className="text-sm font-medium text-gray-700 mb-1">No projects yet</p>
                      <p className="text-xs text-gray-500 text-center mb-3">Create your first project to get started</p>
                      <button 
                        onClick={loadDocumentsList}
                        className="text-xs px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                      >
                        Reload Projects
                      </button>
                    </div>
                  ) : null}
                </div>
              </div>

              {/* Version management area - only show when project is selected */}
              {appState.currentDocument && (
                <div className="border-t border-gray-200 pt-4 mt-4">
                  <div className="space-y-3">
                    {/* Current version info */}
                    <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-green-800">Current Version</span>
                        <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full">
                          v{appState.currentDocument.version_number}.0
                        </span>
                      </div>
                      <div className="text-xs text-green-600 mt-1">
                        Modified on {new Date(appState.currentDocument.last_modified).toLocaleString()}
                      </div>
                    </div>

                    {/* Create new version button */}
                    <button
                      onClick={createNewVersion}
                      disabled={appState.isLoading}
                      className="w-full p-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors duration-200"
                    >
                      {appState.isLoading ? 'Creating...' : '+ Create New Version'}
                    </button>

                    {/* Version history list */}
                    {appState.documentVersions.length > 1 && (
                      <div className="space-y-2">
                        <h4 className="text-xs font-medium text-gray-700 uppercase tracking-wide">Version History</h4>
                        <div className="max-h-32 overflow-y-auto space-y-1">
                          {appState.documentVersions.map((version) => (
                            <div
                              key={version.id}
                              className={`relative group rounded-md text-xs transition-all duration-200 border ${version.version_number === appState.currentDocument?.version_number
                                ? 'bg-blue-100 text-blue-800 border-blue-200'
                                : 'bg-gray-50 text-gray-700 border-gray-200'
                                } ${appState.isLoading ? 'opacity-50' : ''}`}
                            >
                              {/* Version info area - clickable to switch */}
                              <button
                                onClick={() => switchToVersion(version.version_number)}
                                disabled={appState.isLoading || version.version_number === appState.currentDocument?.version_number}
                                className={`w-full p-3 text-left rounded-md transition-all duration-200 ${version.version_number === appState.currentDocument?.version_number
                                  ? ''
                                  : 'hover:bg-gray-100'
                                  } ${appState.isLoading ? 'cursor-not-allowed' : 'cursor-pointer'}`}
                              >
                                <div className="flex items-center justify-between mb-1">
                                  <span className="font-medium text-sm">v{version.version_number}.0</span>
                                  {version.version_number === appState.currentDocument?.version_number && (
                                    <span className="text-xs bg-blue-200 text-blue-800 px-2 py-0.5 rounded-full">Current</span>
                                  )}
                                </div>
                                <div className="text-xs text-gray-500">
                                  Created on {new Date(version.created_at).toLocaleString('en-US', {
                                    month: 'short',
                                    day: 'numeric',
                                    hour: '2-digit',
                                    minute: '2-digit'
                                  })}
                                </div>
                              </button>

                              {/* Delete button - only show when more than 1 version exists */}
                              {appState.documentVersions.length > 1 && (
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    openDeleteDialog(version.version_number);
                                  }}
                                  disabled={appState.isLoading}
                                  className="absolute top-2 right-2 w-6 h-6 flex items-center justify-center rounded-full bg-red-100 text-red-600 hover:bg-red-200 transition-colors duration-200 opacity-0 group-hover:opacity-100"
                                  title="Delete Version"
                                  aria-label="Delete Version"
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

              {/* Action button group - only show when project is selected */}
              {appState.currentDocument && (
                <div className="border-t border-gray-200 pt-4 space-y-2">
                  <button
                    onClick={() => appState.currentDocument && savePatent(appState.currentDocument.id)}
                    disabled={!appState.currentDocument}
                    className="w-full p-2 text-sm bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors duration-200"
                  >
                    💾 Save Document
                  </button>

                  <button
                    onClick={exportToPDF}
                    disabled={!appState.currentDocument}
                    className="w-full p-2 text-sm bg-orange-600 text-white rounded-md hover:bg-orange-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors duration-200"
                  >
                    📄 Export PDF
                  </button>
                  <button
                    onClick={exportToMarkdown}
                    disabled={!appState.currentDocument}
                    className="w-full p-2 text-sm bg-yellow-600 text-white rounded-md hover:bg-yellow-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors duration-200"
                  >
                    📝 Export Markdown
                  </button>
                </div>
              )}
            </div>
          )}
        </aside>

        {/* Center area - document editing area */}
        <main className="flex-1 flex flex-col bg-white min-h-0">
          {/* Document toolbar */}
          <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-gray-50 flex-shrink-0">
            <div className="flex items-center space-x-4">
              <h3 className="text-xl font-semibold text-gray-400">
                {appState.currentDocument?.title || "Select a Document"}
              </h3>
            </div>

          </div>

          {/* Editor main area - add overflow-hidden to ensure content doesn't expand container */}
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
                  onDiagramInsertions={handleDiagramInsertions}
                />
              ) : (
                <div className="h-full flex items-center justify-center text-gray-400">
                  <div className="text-center">
                    <div className="text-6xl mb-4">📄</div>
                    <div className="text-lg font-medium">Please select a document to start editing</div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Status bar - add flex-shrink-0 to ensure always visible */}
          <div className="flex items-center justify-between px-4 py-2 bg-gray-50 border-t border-gray-200 text-sm text-gray-600 flex-shrink-0">
            <div className="flex items-center space-x-4">
              <span>Word Count: {currentDocumentContent.length}</span>

              {/* Document save status */}
              <span className={`flex items-center ${appState.isLoading
                ? 'text-yellow-600'
                : appState.hasUnsavedChanges
                  ? 'text-orange-600'
                  : 'text-green-600'
                }`}>
                <div className={`w-2 h-2 rounded-full mr-2 ${appState.isLoading
                  ? 'bg-yellow-400'
                  : appState.hasUnsavedChanges
                    ? 'bg-orange-400'
                    : 'bg-green-400'
                  }`}></div>
                {appState.isLoading
                  ? 'Saving...'
                  : appState.hasUnsavedChanges
                    ? 'Unsaved Changes'
                    : 'Saved'
                }
              </span>

              {/* AI processing status */}
              <span className={`flex items-center ${
                appState.isAIProcessing 
                  ? 'text-green-600'  // Running - green
                  : appState.aiProcessingStatus.includes('connected') || appState.aiProcessingStatus.includes('standby') || appState.aiProcessingStatus.includes('ready')
                    ? 'text-yellow-600'  // Standby - yellow
                    : 'text-gray-500'    // Off - gray
                }`}>
                <div className={`w-2 h-2 rounded-full mr-2 ${
                  appState.isAIProcessing 
                    ? 'bg-green-400 animate-pulse'  // Running - green blinking
                    : appState.aiProcessingStatus.includes('connected') || appState.aiProcessingStatus.includes('standby') || appState.aiProcessingStatus.includes('ready')
                      ? 'bg-yellow-400'             // Standby - yellow
                      : 'bg-gray-400'               // Off - gray
                  }`}></div>
                <span className="text-xs">
                  🤖 {appState.aiProcessingStatus}
                </span>
              </span>
            </div>
            <div>
              {appState.currentDocument?.last_modified &&
                `Last Modified: ${new Date(appState.currentDocument.last_modified).toLocaleString()}`
              }
            </div>
          </div>
        </main>

        {/* Right sidebar mobile overlay */}
        {isMobile && !appState.rightSidebarCollapsed && (
          <div
            className="mobile-overlay z-40 lg:hidden"
            onClick={() => setAppState(prev => ({ ...prev, rightSidebarCollapsed: true }))}
          />
        )}

        {/* Right sidebar - AI function reserved area */}
        <aside className={`
          ${appState.rightSidebarCollapsed ? 'w-12' : 'w-80'} 
          ${isMobile && !appState.rightSidebarCollapsed ? 'fixed right-0 top-16 bottom-0 z-50' : 'relative'}
          bg-white border-l border-gray-200 shadow-sm transition-all duration-300 ease-in-out
          flex flex-col
        `}>
          {/* Right sidebar header */}
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
              <h2 className="text-lg font-semibold text-gray-800">AI Assistant</h2>
            )}
          </div>

          {/* Right sidebar content */}
          {!appState.rightSidebarCollapsed && (
            <div className="flex-1 overflow-hidden flex flex-col">
              {/* Tab navigation - fixed at top */}
              <div className="flex border-b border-gray-200 flex-shrink-0 bg-white z-10">
                <button
                  onClick={() => setAppState(prev => ({ ...prev, activeRightTab: 'chat' }))}
                  className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${appState.activeRightTab === 'chat'
                    ? 'text-purple-600 border-b-2 border-purple-600 bg-purple-50'
                    : 'text-gray-600 hover:text-gray-800 hover:bg-gray-50'
                    }`}
                >
                  💬 AI Chat
                </button>
                <button
                  onClick={() => setAppState(prev => ({ ...prev, activeRightTab: 'suggestions' }))}
                  className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${appState.activeRightTab === 'suggestions'
                    ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50'
                    : 'text-gray-600 hover:text-gray-800 hover:bg-gray-50'
                    }`}
                >
                  🤖 AI Suggestions
                </button>
              </div>

              {/* Tab content - limit height to prevent overflow */}
              <div className="flex-1 overflow-hidden flex flex-col">
                {appState.activeRightTab === 'chat' ? (
                  <ChatPanel
                    key={appState.currentDocument?.id}
                    className="h-full"
                    getCurrentDocumentContent={() => editorRef.current?.getHTML() || ""}
                    onDiagramInsertions={handleDiagramInsertions}
                    onInsertMermaid={handleInsertMermaid}
                  />
                ) : (
                  <div className="flex-1 p-4 overflow-y-auto min-h-0">
                  {/* AI suggestions display area */}
                  <div className="space-y-4">
                    <div className="flex items-center justify-center mb-2">
                      {/* AI analysis button */}
                      <button
                        onClick={triggerAIAnalysis}
                        disabled={appState.isAIProcessing || appState.aiProcessingStatus.includes('disconnected') || appState.aiProcessingStatus.includes('connection failed')}
                        className={`w-full px-6 py-2 text-sm font-medium rounded-lg transition-all duration-200 ${appState.isAIProcessing || appState.aiProcessingStatus.includes('disconnected') || appState.aiProcessingStatus.includes('connection failed')
                          ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                          : 'bg-blue-600 text-white hover:bg-blue-700'
                          }`}
                          aria-label="AI Document Analysis"
                          title={
                            appState.aiProcessingStatus.includes('disconnected')
                              ? 'WebSocket connection disconnected, please refresh page'
                              : appState.aiProcessingStatus.includes('connection failed')
                                ? 'WebSocket connection failed, please check network'
                                : appState.isAIProcessing
                                  ? 'AI is analysing, please wait'
                                  : 'AI Document Analysis'
                          }
                        >
                          {appState.isAIProcessing
                            ? '🔄 Analysing...'
                            : appState.aiProcessingStatus.includes('disconnected')
                              ? '❌ Disconnected'
                              : appState.aiProcessingStatus.includes('connection failed')
                                ? '❌ Connection Failed'
                                : appState.aiProcessingStatus.includes('connecting')
                                  ? '🔄 Connecting'
                                  : '🤖 AI Analysis'
                          }
                        </button>
                    </div>

                    {/* AI suggestions list */}
                    {appState.aiSuggestions.length > 0 ? (
                      <div className="space-y-3">
                        {/* Sort suggestions: first by severity (high->medium->low), then by paragraph order */}
                        {[...appState.aiSuggestions]
                          .sort((a, b) => {
                            const severityOrder = { high: 3, medium: 2, low: 1 };
                            const severityA = severityOrder[a.severity] || 2;
                            const severityB = severityOrder[b.severity] || 2;

                            // Sort by severity first (descending)
                            if (severityA !== severityB) {
                              return severityB - severityA;
                            }

                            // For same severity, sort by paragraph (ascending)
                            return a.paragraph - b.paragraph;
                          })
                          .map((suggestion, index) => (
                            <div
                              key={index}
                              className={`p-3 rounded-lg border-l-4 transition-all duration-200 ${activeHighlightIndex === index
                                ? 'ring-2 ring-offset-2 ring-gray-400 shadow-lg' // Active state
                                : ''
                                } ${
                                // Apply opacity for low confidence suggestions
                                suggestion.confidence !== undefined && suggestion.confidence < 0.5
                                  ? 'opacity-75'
                                  : ''
                                } ${suggestion.severity === 'high'
                                  ? 'border-red-500 bg-red-50'
                                  : suggestion.severity === 'medium'
                                    ? 'border-yellow-500 bg-yellow-50'
                                    : 'border-blue-500 bg-blue-50'
                                }`}
                            >
                              {/* Clickable area - for highlighting text */}
                              <div
                                onClick={() => handleSuggestionClick(suggestion, index)}
                                className="cursor-pointer"
                              >
                                {/* Suggestion header */}
                                <div className="flex items-center gap-2 mb-2">
                                  <span className="text-xs font-medium text-gray-600">
                                    Paragraph {suggestion.paragraph}
                                  </span>
                                  <span
                                    className={`text-xs px-2 py-1 rounded-full font-medium ${suggestion.severity === 'high'
                                      ? 'bg-red-200 text-red-800'
                                      : suggestion.severity === 'medium'
                                        ? 'bg-yellow-200 text-yellow-800'
                                        : 'bg-blue-200 text-blue-800'
                                      }`}
                                  >
                                    {suggestion.severity === 'high' ? 'Critical' :
                                      suggestion.severity === 'medium' ? 'Medium' : 'Minor'}
                                  </span>
                                  <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                                    {suggestion.type}
                                  </span>
                                </div>

                                {/* Problem description */}
                                <p className="text-sm text-gray-700 mb-3 leading-relaxed">
                                  {suggestion.description}
                                </p>

                                {/* AI suggestion with confidence */}
                                {(suggestion.replaceTo !== undefined || suggestion.suggestion) && (
                                  <>
                                    <div className="flex items-center justify-between mb-2">
                                      <p className="text-sm font-medium text-green-600">💡 Suggestion:</p>
                                      {/* Confidence display */}
                                      {suggestion.confidence !== undefined && (
                                        <div className="flex items-center gap-2">
                                          <span className="text-xs text-gray-600">Confidence:</span>
                                          <div className="flex items-center gap-1">
                                            <div className="w-16 h-2 bg-gray-200 rounded-full overflow-hidden">
                                              <div 
                                                className={`h-full transition-all duration-300 ${
                                                  suggestion.confidence >= 0.8 ? 'bg-green-500' :
                                                  suggestion.confidence >= 0.6 ? 'bg-yellow-500' : 'bg-orange-500'
                                                }`}
                                                style={{ width: `${suggestion.confidence * 100}%` }}
                                              />
                                            </div>
                                            <span className={`text-xs font-medium ${
                                              suggestion.confidence >= 0.8 ? 'text-green-600' :
                                              suggestion.confidence >= 0.6 ? 'text-yellow-600' : 'text-orange-600'
                                            }`}>
                                              {(suggestion.confidence * 100).toFixed(0)}%
                                            </span>
                                          </div>
                                        </div>
                                      )}
                                    </div>
                                    <div className="bg-white p-3 rounded border mb-3">
                                      <p className="text-sm text-gray-700 leading-relaxed font-mono">
                                        {suggestion.replaceTo || suggestion.suggestion}
                                      </p>
                                    </div>
                                  </>
                                )}
                              </div>

                              {/* Action buttons */}
                              <div className="flex gap-2 pt-2 border-t">
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    acceptSuggestion(suggestion, index);
                                  }}
                                  className="flex-1 px-3 py-1.5 text-xs font-medium text-white bg-green-600 hover:bg-green-700 rounded-md transition-colors"
                                  title="Accept suggestion and apply to document"
                                >
                                  ✅ Accept
                                </button>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    copySuggestion(suggestion);
                                  }}
                                  className="flex-1 px-3 py-1.5 text-xs font-medium text-gray-700 bg-gray-200 hover:bg-gray-300 rounded-md transition-colors"
                                  title="Copy suggestion content"
                                >
                                  📋 Copy
                                </button>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    closeSuggestion(suggestion);
                                  }}
                                  className="flex-1 px-3 py-1.5 text-xs font-medium text-gray-700 bg-gray-200 hover:bg-gray-300 rounded-md transition-colors"
                                  title="Ignore this suggestion"
                                >
                                  ❌ Close
                                </button>
                              </div>
                            </div>
                          ))}
                      </div>
                    ) : (
                      /* Empty state when no suggestions */
                      <div className="h-full flex flex-col items-center justify-center text-gray-500 py-8">
                        <div className="text-center space-y-4">
                          <div className="text-4xl">🤖</div>
                          <div className="text-lg font-medium">AI Assistant</div>
                          <div className="text-sm max-w-64 text-center">
                            {appState.isAIProcessing
                              ? "AI is analysing your document, please wait..."
                              : appState.currentDocument
                                ? "Click the AI Analysis button to start analysing the document"
                                : "Please select a document to start editing"
                            }
                          </div>

                          {/* Feature introduction */}
                          <div className="mt-6 p-3 bg-blue-50 border border-blue-200 rounded-lg text-left">
                            <div className="text-xs font-medium text-blue-800 mb-2">
                              ✨ AI Features
                            </div>
                            <ul className="text-xs text-blue-600 space-y-1">
                              <li>• Patent claims format checking</li>
                              <li>• Grammar and structure analysis</li>
                              <li>• Real-time improvement suggestions</li>
                              <li>• Automatic issue detection</li>
                            </ul>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Suggestion statistics */}
                    {appState.aiSuggestions.length > 0 && (
                      <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                        <div className="space-y-3">
                          <div className="text-sm font-medium text-gray-700">
                            Found {appState.aiSuggestions.length} suggestion{appState.aiSuggestions.length > 1 ? 's' : ''}
                          </div>
                          <div className="grid grid-cols-3 gap-2">
                            <div className="flex items-center gap-2 bg-white p-2 rounded">
                              <div className="w-3 h-3 bg-red-400 rounded-full flex-shrink-0"></div>
                              <div className="text-xs">
                                <span className="font-medium">Critical:</span>
                                <span className="ml-1">{appState.aiSuggestions.filter(s => s.severity === 'high').length}</span>
                              </div>
                            </div>
                            <div className="flex items-center gap-2 bg-white p-2 rounded">
                              <div className="w-3 h-3 bg-yellow-400 rounded-full flex-shrink-0"></div>
                              <div className="text-xs">
                                <span className="font-medium">Medium:</span>
                                <span className="ml-1">{appState.aiSuggestions.filter(s => s.severity === 'medium').length}</span>
                              </div>
                            </div>
                            <div className="flex items-center gap-2 bg-white p-2 rounded">
                              <div className="w-3 h-3 bg-blue-400 rounded-full flex-shrink-0"></div>
                              <div className="text-xs">
                                <span className="font-medium">Minor:</span>
                                <span className="ml-1">{appState.aiSuggestions.filter(s => s.severity === 'low').length}</span>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </aside>

      </div>

      {/* Delete version confirmation dialog */}
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
                Delete Version Confirmation
              </h3>
              <p className="text-sm text-gray-500 mb-6">
                Are you sure you want to delete version v{appState.deleteDialog.versionNumber}.0? This action cannot be undone.
              </p>
              <div className="flex justify-center space-x-3">
                <button
                  onClick={closeDeleteDialog}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                >
                  Cancel
                </button>
                <button
                  onClick={confirmDeleteVersion}
                  className="px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                >
                  Confirm Delete
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