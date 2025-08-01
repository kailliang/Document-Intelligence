# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Patent Review System** - a full-stack web application that enables users to review, edit, and analyze patent documents with AI assistance. The system includes document versioning, real-time AI suggestions, and a chat interface for enhanced user interaction.

## Architecture

**Frontend (React + TypeScript)**
- **TipTap** rich text editor for document editing with custom highlight extensions
- **WebSocket** connection for real-time AI suggestions and chat functionality
- **Tab-based UI** with integrated suggestions and chat panels
- **Tailwind CSS** with Emotion for styling
- **Mermaid** for diagram generation in chat
- **ProseMirror API** for precise text matching and highlighting

**Backend (FastAPI + Python)**
- **SQLAlchemy** ORM with SQLite database
- **Dual WebSocket** endpoints: `/ws` (basic) and `/ws/enhanced` (Function Calling)
- **OpenAI GPT-4** integration with Function Calling for precise suggestions
- **Streaming JSON parser** for handling intermittent AI API responses
- **Document versioning system** with complete CRUD operations
- **Enhanced AI endpoints** for chat and diagram generation

**Key Components:**
- `client/src/App.tsx`: Main application state management and tab-based UI orchestration
- `client/src/Document.tsx`: Document editor with WebSocket AI integration and real-time content sync
- `client/src/ChatPanel.tsx`: AI chat interface with streaming responses and Mermaid diagram support
- `client/src/internal/HighlightExtension.tsx`: Custom TipTap extension for text highlighting and replacement
- `server/app/__main__.py`: Core FastAPI routes and WebSocket handlers
- `server/app/enhanced_endpoints.py`: Enhanced WebSocket and chat endpoints
- `server/app/internal/ai_enhanced.py`: Enhanced AI with Function Calling for multiple suggestions
- `server/app/internal/prompt_enhanced.py`: Specialized prompts for patent analysis with rule-based validation
- `server/app/models.py`: Database models for Document and DocumentVersion tables

## Development Commands

**Frontend (from `/client`):**
```bash
npm run dev          # Start development server (Vite)
npm run build        # Build for production (TypeScript + Vite)
npm run lint         # ESLint with TypeScript support
npm run preview      # Preview production build
```

**Backend (from `/server`):**
```bash
python -m app        # Start FastAPI server with uvicorn
uvicorn app.__main__:app --reload  # Alternative with hot reload
```

**Environment Setup:**
```bash
./activate-backend.sh    # Activate conda environment (patent-backend)
./activate-frontend.sh   # Setup frontend environment
```

**Docker (from project root):**
```bash
docker-compose up --build    # Build and run both services
```

**Development Scripts:**
- `activate-backend.sh`: Backend setup script (conda environment: patent-backend)
- `activate-frontend.sh`: Frontend setup script

## Database Architecture

The system uses a **versioning model** with two main entities:

**Document Table:**
- Stores document metadata (title, current_version_id, timestamps)
- Points to the currently active version

**DocumentVersion Table:**
- Stores actual content for each version
- Tracks version numbers (v1.0, v2.0, etc.)
- Maintains version history with `is_active` flag

**Key Features:**
- Create new versions (empty documents)
- Switch between existing versions  
- Edit and save any version without creating new ones
- Delete versions (with safety checks to prevent deleting the last version)

## API Endpoints Structure

**Legacy Compatibility Endpoints:**
- `GET /document/{id}` - Get document with current version content
- `POST /save/{id}` - Save content to current active version

**Version Management API:**
- `GET /api/documents/{id}/versions` - List all versions
- `POST /api/documents/{id}/versions` - Create new version
- `POST /api/documents/{id}/switch-version` - Switch active version
- `DELETE /api/documents/{id}/versions/{version_number}` - Delete version

**Real-time Features:**
- `WebSocket /ws` - Basic AI document analysis (legacy)
- `WebSocket /ws/enhanced` - Enhanced AI with Function Calling capabilities (preferred)
- `POST /api/chat` - AI chat interface with Mermaid diagram support

## AI Integration Details

**Enhanced AI Architecture:**
The system uses two AI processing modes:

1. **Basic Mode** (`/ws`): Legacy WebSocket using streaming JSON responses
2. **Enhanced Mode** (`/ws/enhanced`): Function Calling with precise text matching

**Enhanced AI Workflow:**
1. HTML content from TipTap editor is converted to plain text
2. Text validation ensures content is suitable for AI processing  
3. OpenAI GPT-4 with Function Calling generates structured suggestions
4. Multiple parallel `create_suggestion` function calls for comprehensive analysis
5. Frontend receives suggestions with precise `originalText` and `replaceTo` fields
6. Real-time text highlighting using ProseMirror API for exact matches

**AI Function Calling Configuration:**
- **Temperature**: 0.1 for analysis (stability), 0.2 for chat (creativity)
- **Tool Choice**: "auto" (allows multiple function calls per analysis)
- **Single Suggestion per Text**: AI calls `create_suggestion` once per text segment, combining all issues into one comprehensive correction
- **Rule-Based Analysis**: Uses predefined patent claim rules (Structure, Punctuation, Antecedent Basis, etc.)

**AI Suggestion Format:**
```json
{
  "issues": [{
    "type": "Structure & Punctuation",           // Combined types if multiple issues
    "severity": "high",                          // Highest severity among all issues
    "paragraph": 1,
    "description": "Issue 1 desc | Issue 2 desc", // Combined descriptions
    "text": "original_text",                     // Legacy field
    "suggestion": "suggested_correction",         // Legacy field  
    "originalText": "exact_match_text",          // Enhanced: precise text matching
    "replaceTo": "comprehensive_replacement",     // Enhanced: fixes ALL issues at once
    "issues": [                                  // Detailed breakdown of all issues
      {"type": "Structure", "severity": "high", "description": "Missing colon"},
      {"type": "Punctuation", "severity": "medium", "description": "Wrong punctuation"}
    ]
  }]
}
```

**Enhanced Features:**
- **Precise Text Matching**: Uses `originalText` field for exact document text matching
- **Real-time Content Sync**: Editor content retrieved via `editorRef.current.getHTML()`
- **One Card per Text**: Each text segment gets ONE suggestion card with a comprehensive correction that fixes ALL issues
- **Manual Analysis Trigger**: User-initiated AI analysis (non-automatic)
- **Tab-based UI Integration**: Suggestions and chat panels integrated in right sidebar
- **Accept/Copy/Dismiss Actions**: Interactive suggestion cards with action buttons
- **Smart Sorting**: Suggestions automatically sorted by severity (high→medium→low) and paragraph order
- **Clean Highlighting**: Pure visual highlighting without text selection - only moves cursor position for scrolling
- **Mermaid Diagram Support**: AI can generate flowcharts and system diagrams in chat

## Configuration Requirements

**Environment Variables (.env files needed):**

`server/.env`:
```
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4o
```

`client/.env`:
```
VITE_USE_ENHANCED_WS=true
```

## Important Technical Notes

**WebSocket Implementation:**
- **Dual WebSocket Support**: Basic (`/ws`) and Enhanced (`/ws/enhanced`) endpoints
- **Connection Management**: Uses `react-use-websocket` with automatic reconnection and shared connections
- **State Handling**: Relaxed connection checks allow requests during CONNECTING state
- **Error Handling**: Comprehensive error messages for connection failures and AI API issues

**Enhanced AI Processing:**
- **Function Calling**: Uses indexed dictionary to handle multiple parallel function calls
- **Streaming Parser**: Custom StreamingJSONParser handles intermittent JSON formatting issues  
- **Real-time Document Sync**: Editor content accessed via `editorRef.current.getHTML()` for current state
- **Multiple Function Calls**: AI processes entire document and calls `create_suggestion` separately for each issue

**Text Processing and Highlighting:**
- **HTML→Plain Text**: BeautifulSoup conversion with text validation
- **ProseMirror Integration**: Direct editor manipulation for precise text highlighting and replacement
- **Custom TipTap Extension**: `HighlightExtension.tsx` provides `findTextInDocument` and `replaceText` utilities
- **Temporary Highlights**: Click-to-highlight functionality with auto-clear timers

**Frontend State Management:**
- **Unified AppState**: Single state object manages all application state including tabs, suggestions, and processing status
- **Tab Navigation**: Right sidebar supports 'suggestions' and 'chat' tabs with `activeRightTab` state
- **Real-time Updates**: WebSocket callbacks update UI state immediately
- **Editor Instance Management**: `editorRef` provides access to current editor content independent of React props

**Database Considerations:**
- **SQLAlchemy Relationships**: Proper foreign key handling between Document and DocumentVersion tables
- **Version Management**: Active version tracking with `is_active` flag and `current_version_id`
- **Cascade Deletion**: Versions deleted when documents are removed, with safety checks
- **UTC Timestamps**: All datetime fields use UTC for consistency

The codebase implements a complete patent review workflow with sophisticated real-time AI features, comprehensive version control, and a responsive user interface.