# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a patent review application challenge with a React/TypeScript frontend and Python FastAPI backend. The application provides document version control, real-time AI suggestions via WebSocket streaming, and a modern three-column UI for patent document editing and review.

## Development Commands

### Frontend (client/)
- `npm install` - Install dependencies
- `npm run dev` - Start development server (runs on port 5173)
- `npm run build` - Build for production (runs TypeScript compiler then Vite build)
- `npm run lint` - Run ESLint with TypeScript extensions
- `npm run preview` - Preview production build

### Backend (server/)
- `pip install -r requirements.txt` - Install Python dependencies (includes BeautifulSoup4 for text processing)
- `uvicorn app.__main__:app --reload` - Start development server with auto-reload (runs on port 8000)
- Create `.env` file with `OPENAI_API_KEY` and `OPENAI_MODEL` before running

### Docker
- `docker-compose up --build` - Build and run both services in containers

## Architecture

### Backend Structure (FastAPI + SQLAlchemy + WebSocket)
- `server/app/__main__.py` - Main FastAPI application with REST routes and WebSocket endpoint for real-time AI
- `server/app/models.py` - Database models with Document and DocumentVersion for version control
- `server/app/schemas.py` - Pydantic schemas for API serialization
- `server/app/internal/` - Internal modules:
  - `ai.py` - OpenAI integration with streaming document review
  - `text_utils.py` - HTML-to-plaintext conversion and streaming JSON parsing
  - `db.py` - Database configuration and session management
  - `data.py` - Seed data for documents
  - `prompt.py` - AI prompt templates

### Frontend Structure (React + TypeScript + WebSocket)
- `client/src/App.tsx` - Main application with three-column layout, state management, and AI suggestions UI
- `client/src/Document.tsx` - Document component with WebSocket integration for real-time AI communication
- `client/src/internal/` - Internal components:
  - `Editor.tsx` - TipTap rich text editor component
  - `LoadingOverlay.tsx` - Loading UI component

### Key Technologies
- Frontend: React 18, TypeScript, TipTap editor, TanStack Query, Tailwind CSS, Vite, WebSocket (react-use-websocket)
- Backend: FastAPI, SQLAlchemy, OpenAI SDK, WebSockets, Pydantic, BeautifulSoup4
- Database: In-memory SQLite (resets on server restart)

## Completed Features

### Task 1: Document Version Control
- Complete version management system with Document and DocumentVersion models
- REST API endpoints for creating, switching, and managing versions
- Frontend UI for version selection and creation in left sidebar
- Version history display with timestamps and current version indicators

### Task 2: Real-time AI Suggestions  
- WebSocket endpoint (`/ws`) for streaming AI analysis
- HTML-to-plaintext conversion using BeautifulSoup4 preserving document structure
- Streaming JSON parser with multi-tier fallback strategies for malformed AI responses
- Real-time AI suggestions display in right sidebar with severity-based color coding
- Debounced content analysis to prevent excessive API calls
- Comprehensive error handling and user feedback

## AI Integration Architecture

### Data Flow
1. **HTML Input**: TipTap editor outputs HTML content
2. **Text Conversion**: `text_utils.html_to_plain_text()` converts HTML to plain text preserving structure
3. **AI Processing**: OpenAI API streams JSON responses with patent review suggestions
4. **JSON Parsing**: `StreamingJSONParser` handles fragmented/malformed JSON from AI stream
5. **UI Display**: Suggestions displayed in real-time with severity indicators

### WebSocket Message Types
- `connection_success` - AI service ready
- `processing_start` - AI analysis beginning
- `ai_suggestions` - Streaming suggestions data
- `validation_error` - Text validation issues
- `ai_error` / `server_error` - Error handling

### Performance Optimizations
- 1-second debounce on content changes
- Content change detection to avoid duplicate analysis
- Cached callback functions with `useCallback` to prevent render loops
- Smart state comparison to skip unnecessary updates

## Database Schema

### Document (Main table)
- Stores document metadata and current version reference
- `current_version_id` points to active DocumentVersion

### DocumentVersion (Version storage)  
- Stores actual content for each version
- `version_number` for user-friendly versioning (v1.0, v2.0)
- `is_active` flag for current version tracking

## WebSocket Implementation Notes

- Frontend uses `react-use-websocket` with automatic reconnection
- Backend streams AI responses in real-time using FastAPI WebSocket
- Error handling includes validation, AI service errors, and connection issues
- Message parsing handles incomplete JSON chunks from streaming responses

## SSH Key for GitHub (iak1257 account)

Copy the following SSH public key and add it to GitHub at: https://github.com/iak1257/settings/keys

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINV6SKJCTKvh/v+f+Dem2qLS33eKr88LRKLrwiA1xI/c iak1257@users.noreply.github.com
```

**Steps to add SSH key:**
1. Go to https://github.com/iak1257/settings/keys
2. Click "New SSH key"
3. Title: `MacBook Pro - iak1257`
4. Key: Paste the above SSH public key
5. Click "Add SSH key"