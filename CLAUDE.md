# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Patent Review System** - a full-stack web application that enables users to review, edit, and analyze patent documents with AI assistance. The system includes document versioning, real-time AI suggestions, and a chat interface for enhanced user interaction.

## Architecture

**Frontend (React + TypeScript)**
- **TipTap** rich text editor for document editing with custom highlight extensions
- **WebSocket** connection for real-time AI suggestions and chat functionality
- **React Query** for API state management
- **Tailwind CSS** with Emotion for styling
- **Mermaid** for diagram generation

**Backend (FastAPI + Python)**
- **SQLAlchemy** ORM with SQLite database
- **WebSocket** endpoints for real-time features (`/ws` and `/ws/enhanced`)
- **OpenAI GPT-4** integration for patent analysis and chat functionality
- **Streaming JSON parser** for handling intermittent AI API responses
- Document versioning system with complete CRUD operations

**Key Components:**
- `client/src/App.tsx`: Main application state management and UI orchestration
- `client/src/Document.tsx`: Document editor with WebSocket AI integration
- `client/src/ChatPanel.tsx`: AI chat interface with streaming responses
- `server/app/__main__.py`: Core FastAPI routes and WebSocket handlers
- `server/app/models.py`: Database models for Document and DocumentVersion tables
- `server/app/internal/ai.py`: OpenAI integration with streaming capabilities

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
```

**Docker (from project root):**
```bash
docker-compose up --build    # Build and run both services
```

**Development Scripts:**
- `activate-backend.sh`: Backend setup script
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
- `WebSocket /ws` - Basic AI document analysis
- `WebSocket /ws/enhanced` - Enhanced AI with function calling capabilities
- `POST /api/chat` - AI chat interface

## AI Integration Details

**Core AI Workflow:**
1. HTML content from TipTap editor is converted to plain text
2. Text validation ensures content is suitable for AI processing
3. OpenAI GPT-4 streams back JSON-formatted suggestions
4. Custom StreamingJSONParser handles intermittent JSON formatting issues
5. Frontend receives suggestions and applies highlighting to specific text

**AI Suggestion Format:**
```json
{
  "issues": [{
    "type": "error_type",
    "severity": "high|medium|low", 
    "paragraph": 1,
    "description": "Issue description",
    "text": "original_text",
    "originalText": "exact_match_text",
    "replaceTo": "suggested_replacement"
  }]
}
```

**Enhanced Features:**
- Real-time text highlighting in editor based on AI suggestions
- Accept/copy/dismiss functionality for each suggestion
- Streaming chat interface with context awareness
- Manual trigger for AI analysis (non-automatic)

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
- Uses `react-use-websocket` with automatic reconnection
- Shared WebSocket connections to prevent multiple instances
- Robust error handling for connection failures and AI API issues

**Text Processing Pipeline:**
- HTML→Plain text conversion using BeautifulSoup
- Text validation (length, content checks)
- Streaming JSON parsing to handle API response inconsistencies

**Frontend State Management:**
- Single `AppState` object manages all application state
- Real-time updates via WebSocket callbacks
- Proper cleanup of timers and highlights

**Database Considerations:**
- SQLAlchemy relationships with proper foreign key handling
- Cascade deletion for versions when documents are deleted
- UTC timestamps for all datetime fields

The codebase implements a complete patent review workflow with sophisticated real-time AI features, comprehensive version control, and a responsive user interface.