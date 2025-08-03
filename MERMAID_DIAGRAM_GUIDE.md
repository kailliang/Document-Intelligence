# Mermaid Diagram Integration Guide

This guide explains how Mermaid diagrams are generated, inserted into documents, and processed for PDF export in the Patent Review System.

## Overview

The system supports Mermaid diagrams in two main contexts:
1. **Chat Interface**: Users can request diagram generation through AI chat
2. **Document Editor**: Diagrams can be inserted directly into patent documents

## Architecture Flow

```
User Request → AI Chat → Diagram Generation → Document Insertion → PDF Export
```

## 1. Frontend: Diagram Generation in Chat

### Chat Panel Component (`client/src/ChatPanel.tsx`)

The chat interface handles Mermaid diagrams through:

1. **AI Response Processing**: When the AI includes Mermaid syntax in markdown code blocks:
   ```markdown
   ```mermaid
   graph TD
       A[Start] --> B[Process]
       B --> C[End]
   ```
   ```

2. **Mermaid Component**: A dedicated React component renders diagrams:
   - Initializes Mermaid with theme settings
   - Renders diagrams asynchronously
   - Provides an "Insert" button to add diagrams to documents
   - Handles rendering errors gracefully

3. **Diagram Insertion Callbacks**:
   - `onInsertMermaid`: Inserts diagram at cursor position
   - `onDiagramInsertions`: Processes AI-suggested insertion points

### Key Features:
- Real-time diagram rendering
- Error handling with user feedback
- Unique ID generation for each diagram
- Theme consistency across diagrams

## 2. Frontend: Document Integration

### Mermaid Extension (`client/src/internal/MermaidExtension.tsx`)

A custom TipTap extension that:

1. **Node Definition**:
   - Creates a `mermaidDiagram` node type
   - Stores diagram syntax and optional title
   - Renders as an atomic block element

2. **Node View Component**:
   - Renders Mermaid syntax as SVG
   - Provides edit/delete functionality (UI only)
   - Maintains diagram styling consistency

3. **Insertion Methods**:
   - `insertMermaidDiagram`: Command to insert at current position
   - `insertDiagramAfterText`: Finds text and inserts diagram after it
   - Fallback to cursor position if text not found

### App.tsx Integration

The main app component coordinates diagram insertion:

1. **Manual Insertion** (`handleInsertMermaid`):
   - Receives Mermaid syntax from chat
   - Converts to base64 data URL
   - Inserts at current cursor position

2. **AI-Guided Insertion** (`handleDiagramInsertions`):
   - Processes insertion requests from AI
   - Finds specified text locations
   - Inserts diagrams with titles

## 3. Backend: AI Integration

### Chat Endpoint (`server/app/enhanced_endpoints.py`)

The chat API supports diagram generation:

1. **Request Processing**:
   - Receives chat messages and current document content
   - AI analyzes context and generates appropriate diagrams

2. **Diagram Instructions**:
   - AI can return `DIAGRAM_INSERT:` prefixed JSON
   - Contains insertion location and Mermaid syntax
   - Multiple diagrams supported per response

### Response Format:
```json
{
  "response": "Here's a flowchart for your patent process...",
  "diagram_insertions": [{
    "insert_after_text": "patent application process",
    "mermaid_syntax": "graph TD\n    A[Start] --> B[End]",
    "diagram_type": "flowchart",
    "title": "Patent Application Flow"
  }]
}
```

## 4. Backend: PDF Export

### Mermaid Renderer (`server/app/internal/mermaid_render.py`)

Converts Mermaid nodes to SVG for PDF:

1. **HTML Processing**:
   - Finds all Mermaid nodes in document HTML
   - Extracts syntax and title from attributes/content
   - Renders each diagram using Playwright

2. **SVG Generation**:
   - Creates temporary HTML page with Mermaid.js
   - Renders diagram in headless Chrome
   - Extracts generated SVG content

3. **Container Creation**:
   - Wraps SVG with proper styling
   - Adds title if provided
   - Ensures page-break-inside: avoid

### PDF Exporter (`server/app/internal/pdf_export.py`)

Generates high-quality PDFs:

1. **Processing Pipeline**:
   - Processes Mermaid diagrams to SVG
   - Cleans HTML (removes TipTap attributes)
   - Applies PDF-specific styling
   - Generates PDF with WeasyPrint

2. **Styling Features**:
   - Custom CSS for print layout
   - Page numbering
   - Diagram containers prevent page breaks
   - Chinese font support

## 5. Data Flow Examples

### Example 1: Chat-based Diagram Insertion
```
1. User: "Create a flowchart for the patent process"
2. AI generates Mermaid syntax
3. Chat panel renders diagram
4. User clicks "Insert"
5. Diagram added to document at cursor
```

### Example 2: AI-Suggested Insertion
```
1. User: "Add diagrams to illustrate key concepts"
2. AI analyzes document content
3. Returns insertion points with diagrams
4. App finds text locations
5. Inserts diagrams automatically
```

### Example 3: PDF Export
```
1. User exports document to PDF
2. Backend processes HTML content
3. Mermaid nodes converted to SVG
4. PDF generated with embedded diagrams
```

## 6. Technical Considerations

### Frontend:
- Mermaid initialized with consistent theme
- Unique IDs prevent rendering conflicts
- Error boundaries for failed diagrams
- Real-time synchronization with editor

### Backend:
- Async rendering for performance
- Timeout protection (2 seconds)
- Fallback for rendering failures
- SVG optimization for PDF quality

### Security:
- Mermaid security level set to 'loose'
- Input sanitization in BeautifulSoup
- Safe file path generation

## 7. Troubleshooting

### Common Issues:

1. **Diagram Not Rendering**:
   - Check Mermaid syntax validity
   - Verify initialization settings
   - Check browser console for errors

2. **Insertion Failures**:
   - Ensure editor instance is ready
   - Verify text search accuracy
   - Check callback registration

3. **PDF Export Issues**:
   - Verify Playwright installation
   - Check SVG generation logs
   - Ensure proper HTML structure

### Debug Points:
- Chat console logs: `📊` prefix
- Mermaid render errors in console
- Backend logs for PDF generation
- Network tab for API responses
