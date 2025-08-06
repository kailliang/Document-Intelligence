
## Objective

You have received a mock-up of a patent reviewing application from a junior colleague. Unfortunately, it is incomplete and needs additional work. Your job is to take your colleague's work, improve and extend it, and add a feature of your own creation!

After completing the tasks below, add a couple of sentences to the end of this file briefly outlining what improvements you made.

## Docker

Make sure you create a .env file (see .env.example) with the OpenAI API key we have provided.

To build and run the application using Docker, execute the following command:

```
docker-compose up --build
```

## Task 1: Implement Document Versioning

Currently, the user can save a document, but there is no concept of **versioning**. Paying customers have expressed an interest in this and have requested the following:

1. The ability to create new versions
2. The ability to switch between existing versions
3. The ability to make changes to any of the existing versions and save those changes (without creating a new version)

You will need to modify the database model (`app/models.py`), add some API routes (`app/__main__.py`), and update the client-side code accordingly.

## Task 2: Real-Time AI Suggestions

Your colleague started some work on integrating real-time improvement suggestions for your users. However, they only had time to set up a WebSocket connection. It is your job to finish it.

You will find a WebSocket endpoint that needs to be completed in the `app/__main__.py` file in the `server`. This endpoint should receive the editor contents from the client and stream out AI suggestions to the UI. There are a few complications here:

- You are using a third party AI library, which exposes a fairly poor API. The code for this library is in `server/app/internal/ai.py`.
  - The API expects a **plain** text document, with no HTML mark-up or formatting
  - There are intermittent errors in the formatting of the JSON output

You will need to find some way of notifying the user of the suggestions generated. As we don't want the user's experience to be impacted, this should be a background process. You can find the existing frontend WebSocket code in `client/src/Document.tsx`.

## Task 3: Showcase your AI Skills

Implement an additional AI-based feature or product improvement that would benefit our customers as they draft their patent applications.

This last part is open-ended, and you can take it in any direction you like. We’re interested in seeing how you come up with and implement AI-based approaches without us directing you.

Some ideas:

- Generate technical drawings (e.g. flowcharts, system diagrams, device diagrams, etc.) based on the claims.
- Have the user ask the AI to make an update to the application, and have the AI stream this update directly into the editor.
- Extend task 2 by having the AI incorporate its suggestions directly into the editor.

Or anything else you like.

Enjoy!

---



# Complete Functionality Report

## Task Requirements Fulfillment

### ✅ Task 1: Document Versioning - FULLY IMPLEMENTED

**Requirements:**
1. ✅ **Create new versions** 
2. ✅ **Switch between existing versions**
3. ✅ **Make changes to any existing version without creating new version**

**Implementation:**
- **Database Model**: Enhanced with `Document` and `DocumentVersion` tables with proper relationships
- **API Routes**: Complete REST API for version management
  - `GET /api/documents/{id}/versions` - List all versions
  - `POST /api/documents/{id}/versions` - Create new version
  - `POST /api/documents/{id}/switch-version` - Switch active version
  - `DELETE /api/documents/{id}/versions/{version_number}` - Delete version
- **Frontend**: Professional version management UI with:
  - Version dropdown selector
  - Create new version button
  - Delete a version button
  - Real-time version switching
  - Save to current version functionality
  - Safety checks preventing deletion of last version

**Key Features:**
- Seamless version switching without data loss
- Version metadata (timestamps, version numbers)
- Active version tracking
- Backward compatible with existing save functionality

---

### ✅ Task 2: Real-Time AI Suggestions - FULLY IMPLEMENTED & ENHANCED

**Requirements:**
1. ✅ **Complete WebSocket endpoint**
2. ✅ **Handle HTML-to-plain-text conversion**
3. ✅ **Handle intermittent JSON formatting errors**
4. ✅ **Background processing without impacting user experience**

**Implementation:**
- **WebSocket Endpoints**: Dual implementation for maximum flexibility
  - `/ws` - Legacy endpoint with streaming JSON
  - `/ws/enhanced` - Advanced endpoint with Function Calling
- **HTML Processing**: BeautifulSoup4 for reliable HTML-to-plain-text conversion
- **Error Handling**: Multi-tier JSON parsing with fallback strategies
- **Background Processing**: 
  - Manual trigger system (user-controlled)
  - Non-blocking WebSocket communication
  - Real-time status updates

**Advanced Features:**
- **Function Calling Integration**: OpenAI GPT-4.1 for precise suggestions
- **Patent-Specific Rules**: Structure, punctuation, antecedent basis validation
- **Precise Text Matching**: Using `originalText` and `replaceTo` fields
- **Smart UI Integration**:
  - Severity-based color coding (high=red, medium=yellow, low=blue)
  - Accept/Copy/Dismiss actions
  - Temporary text highlighting
  - Tab-based suggestion panel

---

### ✅ Task 3: AI Skills Showcase - MERMAID DIAGRAM SYSTEM

**Implementation:**

#### 1. **AI-Generated Diagrams in Chat**
- Chat interface where users can request diagrams
- AI generates Mermaid syntax for various diagram types:
  - Flowcharts for process flows
  - Hierarchical diagrams for claim structures
  - Sequence diagrams for method steps
  - State diagrams for system states

#### 2. **Document Diagram Insertion**
- **Custom TipTap MermaidExtension**: 
  ```typescript
  insertMermaidDiagram({ syntax: string, title?: string })
  ```
- **AI-Powered Insertion**: AI can insert diagrams at specific locations
  ```typescript
  insertDiagramAfterText(editor, searchText, mermaidSyntax, title)
  ```
- **Real-time Preview**: Diagrams render immediately in editor

#### 3. **PDF Export with Diagrams**
- **Server-Side Rendering**: Playwright renders Mermaid to SVG
- **PDF Integration**: 
  - Removed foreignObject elements for compatibility
  - Applied explicit SVG styling
  - Fixed text positioning and centering
  - Removed CSS animations
  - Added proper ViewBox for scaling
- **High-Quality Output**: Professional PDFs with embedded diagrams

**Technical Innovation:**
- Function Calling for diagram, flowchart and suggestion card generation 
- Smart text search for insertion points
- Fallback to cursor position if text not found
- Complete edit→preview→export pipeline

---

## Core Features Overview

### 1. **Document Management System**
- **Rich Text Editing**: TipTap-based editor with custom extensions
- **Version Control**: Complete document versioning with create/switch/save/delete capabilities
- **Real-time Saving**: Automatic save status indicators and error handling
- **Document Persistence**: SQLAlchemy ORM with SQLite database

### 2. **AI-Powered Patent Analysis**
- **OpenAI GPT-4.1 Integration**: Advanced patent analysis using Function Calling
- **Real-time Suggestions**: WebSocket-based streaming analysis
- **Patent-Specific Rules**: Structure, punctuation, antecedent basis validation
- **Severity Categorization**: High/medium/low priority issues
- **Precise Text Matching**: Exact text location and replacement suggestions

### 3. **Interactive AI Chat**
- **Conversational Interface**: Dedicated chat panel for patent queries
- **Context-Aware Responses**: AI understands current document content
- **Diagram Generation**: AI can create Mermaid diagrams on demand
- **Streaming Responses**: Real-time message delivery

### 4. **Mermaid Diagram Integration**
- **Custom TipTap Extension**: Native diagram support in editor
- **AI-Generated Diagrams**: Automatic diagram creation from text
- **Multiple Diagram Types**: Flowcharts, hierarchical, sequence diagrams
- **Smart Insertion**: AI places diagrams at contextually relevant positions
- **PDF Export Support**: Server-side rendering for perfect PDF integration

### 5. **Professional PDF Export**
- **High-Quality Output**: Playwright-based rendering engine
- **Diagram Integration**: Perfect Mermaid diagram rendering with:
  - SVG processing for PDF compatibility
  - Text positioning fixes
  - Background color corrections
  - Wide diagram handling
- **Automatic Cleanup**: 24-hour retention with automatic deletion
- **Security Features**: Path traversal protection, filename validation

---

## Technical Implementation Details

### Frontend Architecture
```
React 18 + TypeScript
├── TipTap Editor (Custom Extensions)
│   ├── HighlightExtension (Text highlighting)
│   └── MermaidExtension (Diagram support)
├── WebSocket Integration (react-use-websocket)
├── State Management (React Query)
├── UI Framework (TailwindCSS + Emotion)
└── Build System (Vite)
```

### Backend Architecture
```
FastAPI + Python
├── Database Layer (SQLAlchemy + SQLite)
├── AI Integration (OpenAI GPT-4)
├── WebSocket Endpoints
│   ├── /ws (Legacy streaming)
│   └── /ws/enhanced (Function Calling)
├── PDF Generation (Playwright)
└── API Endpoints (RESTful design)
```

### Diagram System Architecture
```
AI Chat Request → GPT-4.1 Function Calling → Mermaid Syntax Generation
                                         ↓
                                  Document Insertion
                                         ↓
                              TipTap MermaidExtension
                                         ↓
                                  PDF Export Pipeline
                                         ↓
                              Playwright SVG Rendering
```

---


## Security Features

- **API Key Management**: Environment variable protection
- **Path Traversal Protection**: Secure file operations
- **Input Validation**: Pydantic models for data validation
- **CORS Configuration**: Configurable origin restrictions
- **Error Handling**: Comprehensive error management

---

## Performance Optimizations

- **Debounced Analysis**: 1-second delay for AI triggers
- **Connection Management**: Smart WebSocket handling
- **Caching**: React Query for efficient data management
- **Lazy Loading**: Component-based code splitting
- **Cleanup Systems**: Automatic file management

---

## Development Tools

### Scripts
- `start-dev.sh`: One-click development startup
- `stop-dev.sh`: Clean service shutdown
- `logs-dev.sh`: Service monitoring

---

## Future Enhancements

### Planned Features
- User authentication system
- Multi-user collaboration
- Advanced export formats
- Extended AI capabilities
- Performance monitoring

### Advanced AI Architecture Enhancement
**Multi-Agent Collaboration System**

The current implementation uses a single-agent architecture. With more development time, the system could be enhanced with a multi-agent collaboration architecture:

**Proposed Architecture:**
```
Task Orchestrator Agent
    ├── Patent Structure Analyst Agent
    │   └── Specializes in claim structure, dependencies, and formatting
    ├── Technical Accuracy Agent
    │   └── Validates technical terms, consistency, and prior art references
    ├── Legal Compliance Agent
    │   └── Ensures legal language compliance and regulatory requirements
    ├── Diagram Generation Agent
    │   └── Creates flowcharts, system diagrams, and technical illustrations
    └── Quality Assurance Agent
        └── Reviews outputs from other agents for coherence and accuracy
```

**Benefits of Multi-Agent Architecture:**
- **Higher Quality Suggestions**: Each agent specializes in specific aspects of patent analysis
- **More Robust Diagram Generation**: Dedicated agent for visual content with deeper understanding
- **Parallel Processing**: Multiple agents can work simultaneously on different aspects
- **Scalability**: Easy to add new specialized agents for emerging requirements
- **Improved Accuracy**: Cross-validation between agents reduces errors
- **Context Preservation**: Agents can share context while maintaining specialization

**Implementation Approach:**
1. Define clear interfaces between agents
2. Implement message passing and coordination protocols
3. Create specialized prompts for each agent role
4. Build consensus mechanisms for conflicting suggestions
5. Develop agent performance monitoring and optimization


### Security Improvements
- JWT authentication
- Rate limiting
- Security headers
- Audit logging

---