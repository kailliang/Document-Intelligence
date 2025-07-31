# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a patent review application challenge with a React/TypeScript frontend and Python FastAPI backend. The application allows users to load, edit, and save patent documents, with real-time AI suggestions via WebSocket connections.

## Development Commands

### Frontend (client/)
- `npm install` - Install dependencies
- `npm run dev` - Start development server (runs on port 5173)
- `npm run build` - Build for production (runs TypeScript compiler then Vite build)
- `npm run lint` - Run ESLint with TypeScript extensions
- `npm run preview` - Preview production build

### Backend (server/)
- `pip install -r requirements.txt` - Install Python dependencies
- `uvicorn app.__main__:app --reload` - Start development server with auto-reload (runs on port 8000)
- Create `.env` file with `OPENAI_API_KEY` before running

### Docker
- `docker-compose up --build` - Build and run both services in containers

## Architecture

### Backend Structure (FastAPI + SQLAlchemy)
- `server/app/__main__.py` - Main FastAPI application with routes and WebSocket endpoint
- `server/app/models.py` - Database models (currently Document model with id/content)
- `server/app/schemas.py` - Pydantic schemas for API serialization
- `server/app/internal/` - Internal modules (treat as third-party libraries):
  - `ai.py` - OpenAI integration with streaming document review
  - `db.py` - Database configuration and session management
  - `data.py` - Seed data for documents
  - `prompt.py` - AI prompt templates

### Frontend Structure (React + TypeScript + Vite)
- `client/src/App.tsx` - Main application shell with document loading/saving
- `client/src/Document.tsx` - Document component with WebSocket integration
- `client/src/internal/` - Internal components (treat as third-party libraries):
  - `Editor.tsx` - TipTap rich text editor component
  - `LoadingOverlay.tsx` - Loading UI component

### Key Technologies
- Frontend: React 18, TypeScript, TipTap editor, TanStack Query, Tailwind CSS, Vite
- Backend: FastAPI, SQLAlchemy, OpenAI SDK, WebSockets, Pydantic
- Database: In-memory SQLite (resets on server restart)

## Development Notes

### Current State
The application has basic CRUD operations for documents but is incomplete:
- WebSocket endpoint receives content but doesn't process or respond with AI suggestions
- No document versioning system
- AI integration exists but isn't fully implemented in the WebSocket flow

### Challenge Tasks
1. **Document Versioning**: Add version control to documents (create, switch, save versions)
2. **Real-time AI Suggestions**: Complete WebSocket implementation to stream AI review suggestions
3. **Custom AI Feature**: Implement additional AI-powered functionality

### AI Integration Notes
- `ai.review_document()` expects plain text (no HTML/markdown)
- Returns streaming JSON with issues array containing type, severity, paragraph, description, suggestion
- Has 5% random error probability for testing error handling
- Frontend editor uses TipTap which outputs HTML - needs conversion to plain text before AI processing

### Database
- Uses SQLAlchemy with in-memory SQLite
- Auto-creates tables on startup with seed data (2 documents)
- No migrations - database resets on server restart

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