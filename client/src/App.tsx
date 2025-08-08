import { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";
import Document from "./Document";
import LoadingOverlay from "./internal/LoadingOverlay";
import Logo from "./assets/logo.png";
import ChatPanel from "./ChatPanel";
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
  deleteDialog: {                 // Delete confirmation dialog state
    isOpen: boolean;
    versionNumber: number | null;
  };
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
    deleteDialog: {
      isOpen: false,
      versionNumber: null
    },
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


  // TipTap editor instance reference
  const editorRef = useRef<any>(null);

  /**
   * Handle document content changes and mark as unsaved
   */
  const handleContentChange = (newContent: string) => {
    setCurrentDocumentContent(newContent);


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



  return (
    <div className="flex flex-col h-screen w-full bg-gray-50">
      {/* Loading overlay */}
      {appState.isLoading && <LoadingOverlay />}

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
          ${appState.leftSidebarCollapsed ? 'w-12' : 'w-88'} 
          ${isMobile && !appState.leftSidebarCollapsed ? 'fixed left-0 top-0 bottom-0 z-50' : 'relative'}
          bg-white border-r border-gray-200 shadow-sm transition-all duration-300 ease-in-out
          flex flex-col
        `}>
          {/* Left sidebar header */}
          <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 bg-gray-50 flex-shrink-0 h-[52px]">
            {!appState.leftSidebarCollapsed && (
              <div className="flex items-center space-x-2">
                <img src={Logo} alt="Logo" className="h-5 flex-shrink-0" />
                <h3 className="text-xl font-semibold text-gray-400 whitespace-nowrap">Patent Review</h3>
              </div>
            )}
            <button
              onClick={toggleLeftSidebar}
              className="p-1 rounded-md hover:bg-gray-100 transition-colors duration-200"
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
                          <div className={`font-medium text-sm leading-tight truncate ${
                            appState.currentDocument?.id === doc.id ? 'text-blue-700' : 'text-gray-800'
                          }`} 
                          title={doc.title}>
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
                                <div className="flex items-center justify-between">
                                  <div className="flex items-baseline space-x-2">
                                    <span className="font-medium text-sm">v{version.version_number}.0</span>
                                    <span className="text-xs text-gray-500">
                                      Created on {new Date(version.created_at).toLocaleString('en-US', {
                                        month: 'short',
                                        day: 'numeric',
                                        hour: '2-digit',
                                        minute: '2-digit'
                                      })}
                                    </span>
                                  </div>
                                  {version.version_number === appState.currentDocument?.version_number && (
                                    <span className="text-xs bg-blue-200 text-blue-800 px-2 py-0.5 rounded-full flex-shrink-0 ml-2">Current</span>
                                  )}
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
          <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 bg-gray-50 flex-shrink-0 h-[52px]">
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
          ${appState.rightSidebarCollapsed ? 'w-12' : 'w-88'} 
          ${isMobile && !appState.rightSidebarCollapsed ? 'fixed right-0 top-16 bottom-0 z-50' : 'relative'}
          bg-white border-l border-gray-200 shadow-sm transition-all duration-300 ease-in-out
          flex flex-col
        `}>
          {/* Right sidebar header with tab navigation */}
          <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 bg-gray-50 flex-shrink-0 h-[52px]">
            <button
              onClick={toggleRightSidebar}
              className="p-1 rounded-md hover:bg-gray-100 transition-colors duration-200 mr-2"
              aria-label="Toggle right sidebar"
            >
              <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d={appState.rightSidebarCollapsed ? "M15 19l-7-7 7-7" : "M9 5l7 7-7 7"} />
              </svg>
            </button>
            {!appState.rightSidebarCollapsed && (
              <div className="flex flex-1">
                <h3 className="text-lg font-medium text-gray-800 px-4 py-1.5">
                  🤖 AI Assistant
                </h3>
              </div>
            )}
          </div>

          {/* Right sidebar content */}
          {!appState.rightSidebarCollapsed && (
            <div className="flex-1 overflow-hidden flex flex-col">

              {/* Tab content - limit height to prevent overflow */}
              <div className="flex-1 overflow-hidden flex flex-col">
                <ChatPanel
                  key={appState.currentDocument?.id}
                  className="h-full"
                  getCurrentDocumentContent={() => editorRef.current?.getHTML() || ""}
                  onDiagramInsertions={handleDiagramInsertions}
                  onInsertMermaid={handleInsertMermaid}
                  documentId={appState.currentDocument?.id}
                  documentVersion={`v${appState.currentDocument?.version_number || 1}.0`}
                />
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