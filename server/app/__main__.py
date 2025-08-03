from contextlib import asynccontextmanager
from datetime import datetime
import json
import logging
import asyncio
from pathlib import Path

from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import insert, select, update, func
from sqlalchemy.orm import Session

from app.internal.ai import AI, get_ai
from app.internal.data import DOCUMENT_1, DOCUMENT_2
from bs4 import BeautifulSoup
from app.internal.db import Base, SessionLocal, engine, get_db
from app.internal.text_utils import html_to_plain_text, validate_text_for_ai, StreamingJSONParser

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_title_from_html(html_content: str) -> str:
    """
    Extract title from HTML content
    Priority order: <title> tag > <h1> tag > default title
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Prefer <title> tag
        title_tag = soup.find('title')
        if title_tag and title_tag.string:
            return title_tag.string.strip()
        
        # If no <title>, use first <h1> tag
        h1_tag = soup.find('h1')
        if h1_tag and h1_tag.string:
            return h1_tag.string.strip()
        
        # If none found, return default title
        return "Untitled Document"
        
    except Exception as e:
        logger.warning(f"Failed to extract title: {e}")
        return "Untitled Document"

import app.models as models
import app.schemas as schemas


@asynccontextmanager
async def lifespan(_: FastAPI):
    """
    Application lifecycle management - initialise database and seed data on startup
    
    Why modify seed data initialisation?
    - Now need to create data for both Document and DocumentVersion tables
    - Need to properly set up relationships between documents and versions
    """
    # Create the database tables
    Base.metadata.create_all(bind=engine)
    
    # Insert seed data with versioning support
    with SessionLocal() as db:
        # Check if data has already been initialised (avoid duplicate initialisation)
        existing_doc = db.scalar(select(models.Document).where(models.Document.id == 1))
        if not existing_doc:
            # Create first document (automatically extract title from HTML)
            doc1_title = extract_title_from_html(DOCUMENT_1)
            doc1 = models.Document(
                id=1,
                title=doc1_title,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(doc1)
            db.flush()  # Ensure doc1 has ID
            
            # Create initial version for first document
            version1 = models.DocumentVersion(
                document_id=doc1.id,
                version_number=1,
                content=DOCUMENT_1,
                is_active=True,
                created_at=datetime.utcnow()
            )
            db.add(version1)
            db.flush()  # Ensure version1 has ID
            
            # Set document's current version
            doc1.current_version_id = version1.id
            
            # Create second document (automatically extract title from HTML)
            doc2_title = extract_title_from_html(DOCUMENT_2)
            doc2 = models.Document(
                id=2,
                title=doc2_title,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(doc2)
            db.flush()
            
            # Create initial version for second document
            version2 = models.DocumentVersion(
                document_id=doc2.id,
                version_number=1,
                content=DOCUMENT_2,
                is_active=True,
                created_at=datetime.utcnow()
            )
            db.add(version2)
            db.flush()
            
            # Set document's current version
            doc2.current_version_id = version2.id
            
            db.commit()
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===================================================================
# Maintain backward compatible legacy API endpoints
# ===================================================================

@app.get("/document/{document_id}")
def get_document(
    document_id: int, db: Session = Depends(get_db)
) -> schemas.DocumentWithCurrentVersion:
    """
    Get document and its current version content (backward compatible)
    
    Why keep this endpoint?
    - Frontend currently uses this endpoint to get documents
    - Maintain backward compatibility, avoid breaking existing functionality
    - Now returns current version content rather than direct content field
    """
    # Query document and its current version
    document = db.scalar(
        select(models.Document)
        .where(models.Document.id == document_id)
    )
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get current version
    current_version = None
    if document.current_version_id:
        current_version = db.scalar(
            select(models.DocumentVersion)
            .where(models.DocumentVersion.id == document.current_version_id)
        )
    
    # If no current version, get latest version
    if not current_version:
        current_version = db.scalar(
            select(models.DocumentVersion)
            .where(models.DocumentVersion.document_id == document_id)
            .order_by(models.DocumentVersion.version_number.desc())
        )
    
    if not current_version:
        raise HTTPException(status_code=404, detail="No version found for document")
    
    return schemas.DocumentWithCurrentVersion(
        id=document.id,
        title=document.title,
        content=current_version.content,
        version_number=current_version.version_number,
        last_modified=current_version.created_at
    )


@app.post("/save/{document_id}")
def save(
    document_id: int, request: schemas.CreateVersionRequest, db: Session = Depends(get_db)
):
    """
    Save document content (backward compatible)
    
    Why modify this endpoint?
    - Now need to update version table rather than directly updating document table
    - Save by updating current active version content
    - Don't create new version, only update existing version
    
    Fix variable name conflict:
    - Parameter name changed from document to request, avoid conflict with database object
    """
    # Find the document
    document = db.scalar(
        select(models.Document)
        .where(models.Document.id == document_id)
    )
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Find current active version
    current_version = None
    if document.current_version_id:
        current_version = db.scalar(
            select(models.DocumentVersion)
            .where(models.DocumentVersion.id == document.current_version_id)
        )
    
    # If no current version, get latest version
    if not current_version:
        current_version = db.scalar(
            select(models.DocumentVersion)
            .where(models.DocumentVersion.document_id == document_id)
            .order_by(models.DocumentVersion.version_number.desc())
        )
    
    if not current_version:
        raise HTTPException(status_code=404, detail="No version found for document")
    
    # Update version content
    db.execute(
        update(models.DocumentVersion)
        .where(models.DocumentVersion.id == current_version.id)
        .values(content=request.content)
    )
    
    # Update document's updated_at timestamp
    db.execute(
        update(models.Document)
        .where(models.Document.id == document_id)
        .values(updated_at=datetime.utcnow())
    )
    
    db.commit()
    return {"document_id": document_id, "version_number": current_version.version_number, "content": request.content}


# ===================================================================
# New version management API endpoints
# ===================================================================

@app.get("/api/documents")
def get_all_documents(db: Session = Depends(get_db)):
    """
    Get basic information list of all documents
    """
    documents = db.scalars(
        select(models.Document)
        .order_by(models.Document.id)
    ).all()
    
    return [
        {
            "id": doc.id,
            "title": doc.title,
            "created_at": doc.created_at.isoformat(),
            "updated_at": doc.updated_at.isoformat()
        }
        for doc in documents
    ]

@app.get("/api/documents/{document_id}")
def get_document_with_versions(
    document_id: int, db: Session = Depends(get_db)
) -> schemas.DocumentRead:
    """
    Get document and all its version history
    
    This endpoint is specifically for version management functionality:
    - Returns complete document information
    - Contains list of all versions
    - Indicates currently active version
    """
    document = db.scalar(
        select(models.Document)
        .where(models.Document.id == document_id)
    )
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get all versions (sorted by version number)
    versions = db.scalars(
        select(models.DocumentVersion)
        .where(models.DocumentVersion.document_id == document_id)
        .order_by(models.DocumentVersion.version_number.desc())
    ).all()
    
    # Get current version
    current_version = None
    if document.current_version_id:
        current_version = db.scalar(
            select(models.DocumentVersion)
            .where(models.DocumentVersion.id == document.current_version_id)
        )
    
    return schemas.DocumentRead(
        id=document.id,
        title=document.title,
        current_version_id=document.current_version_id,
        created_at=document.created_at,
        updated_at=document.updated_at,
        versions=[schemas.DocumentVersionRead.model_validate(v) for v in versions],
        current_version=schemas.DocumentVersionRead.model_validate(current_version) if current_version else None
    )


@app.post("/api/documents/{document_id}/versions")
def create_version(
    document_id: int, 
    request: schemas.CreateVersionRequest, 
    db: Session = Depends(get_db)
) -> schemas.DocumentVersionRead:
    """
    Create new version for document
    
    Logic for creating new version:
    1. Find document
    2. Calculate new version number (max version number + 1)
    3. Set all existing versions to inactive
    4. Create new version and set as active
    5. Update document's current version pointer
    """
    # Find the document
    document = db.scalar(
        select(models.Document)
        .where(models.Document.id == document_id)
    )
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get maximum version number
    max_version = db.scalar(
        select(models.DocumentVersion.version_number)
        .where(models.DocumentVersion.document_id == document_id)
        .order_by(models.DocumentVersion.version_number.desc())
    ) or 0
    
    new_version_number = max_version + 1
    
    # Set all existing versions to inactive
    db.execute(
        update(models.DocumentVersion)
        .where(models.DocumentVersion.document_id == document_id)
        .values(is_active=False)
    )
    
    # Create new version (empty document)
    new_version = models.DocumentVersion(
        document_id=document_id,
        version_number=new_version_number,
        content="",  # New version starts from empty document
        is_active=True,
        created_at=datetime.utcnow()
    )
    
    db.add(new_version)
    db.flush()  # Get new version's ID
    
    # Update document's current version pointer
    db.execute(
        update(models.Document)
        .where(models.Document.id == document_id)
        .values(
            current_version_id=new_version.id,
            updated_at=datetime.utcnow()
        )
    )
    
    db.commit()
    db.refresh(new_version)
    
    return schemas.DocumentVersionRead.model_validate(new_version)


@app.post("/api/documents/{document_id}/switch-version")
def switch_version(
    document_id: int,
    request: schemas.SwitchVersionRequest,
    db: Session = Depends(get_db)
) -> schemas.DocumentWithCurrentVersion:
    """
    Switch to specified version
    
    Logic for switching version:
    1. Verify document and version exist
    2. Set all versions to inactive
    3. Activate specified version
    4. Update document's current version pointer
    5. Return document information after switch
    """
    # Find the document
    document = db.scalar(
        select(models.Document)
        .where(models.Document.id == document_id)
    )
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Find specified version
    target_version = db.scalar(
        select(models.DocumentVersion)
        .where(
            models.DocumentVersion.document_id == document_id,
            models.DocumentVersion.version_number == request.version_number
        )
    )
    
    if not target_version:
        raise HTTPException(status_code=404, detail=f"Version {request.version_number} not found")
    
    # Set all versions to inactive
    db.execute(
        update(models.DocumentVersion)
        .where(models.DocumentVersion.document_id == document_id)
        .values(is_active=False)
    )
    
    # Activate target version
    db.execute(
        update(models.DocumentVersion)
        .where(models.DocumentVersion.id == target_version.id)
        .values(is_active=True)
    )
    
    # Update document's current version pointer
    db.execute(
        update(models.Document)
        .where(models.Document.id == document_id)
        .values(
            current_version_id=target_version.id,
            updated_at=datetime.utcnow()
        )
    )
    
    db.commit()
    
    return schemas.DocumentWithCurrentVersion(
        id=document.id,
        title=document.title,
        content=target_version.content,
        version_number=target_version.version_number,
        last_modified=target_version.created_at
    )


@app.get("/api/documents/{document_id}/versions")
def get_versions(
    document_id: int, db: Session = Depends(get_db)
) -> list[schemas.DocumentVersionRead]:
    """
    Get a list of all versions for a document.

    This endpoint is specifically for displaying version history:
    - Only returns version information, does not include document information.
    - Sorted by version number in descending order (newest version first).
    """
    # Verify the document exists
    document = db.scalar(
        select(models.Document)
        .where(models.Document.id == document_id)
    )
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get all versions
    versions = db.scalars(
        select(models.DocumentVersion)
        .where(models.DocumentVersion.document_id == document_id)
        .order_by(models.DocumentVersion.version_number.desc())
    ).all()
    
    return [schemas.DocumentVersionRead.model_validate(v) for v in versions]


@app.delete("/api/documents/{document_id}/versions/{version_number}")
def delete_version(
    document_id: int,
    version_number: int,
    db: Session = Depends(get_db)
) -> dict:
    """
    Delete specified version
    
    Deletion logic:
    1. Verify document exists
    2. Check if there are at least 2 versions (can't delete last version)
    3. Verify the version to delete exists
    4. Check if the version to delete is the current active version
    5. If it's the active version, switch to latest other version first
    6. Delete specified version
    """
    # Find the document
    document = db.scalar(
        select(models.Document)
        .where(models.Document.id == document_id)
    )
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Check total version count
    version_count = db.scalar(
        select(func.count(models.DocumentVersion.id))
        .where(models.DocumentVersion.document_id == document_id)
    )
    
    if version_count <= 1:
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete the last remaining version"
        )
    
    # Find version to delete
    target_version = db.scalar(
        select(models.DocumentVersion)
        .where(
            models.DocumentVersion.document_id == document_id,
            models.DocumentVersion.version_number == version_number
        )
    )
    
    if not target_version:
        raise HTTPException(
            status_code=404, 
            detail=f"Version {version_number} not found"
        )
    
    # If deleting current active version, need to switch to other version first
    if target_version.is_active:
        # Find latest other version
        alternative_version = db.scalar(
            select(models.DocumentVersion)
            .where(
                models.DocumentVersion.document_id == document_id,
                models.DocumentVersion.id != target_version.id
            )
            .order_by(models.DocumentVersion.version_number.desc())
        )
        
        if alternative_version:
            # Activate alternative version
            alternative_version.is_active = True
            # Update document's current version pointer
            document.current_version_id = alternative_version.id
            document.updated_at = datetime.utcnow()
    
    # Delete target version
    db.delete(target_version)
    db.commit()
    
    return {"message": f"Version {version_number} deleted successfully"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint: Real-time AI suggestion system
    
    Workflow:
    1. Receive HTML content from frontend
    2. Convert to plain text format
    3. Call AI service for streaming analysis
    4. Parse AI response JSON data
    5. Send complete suggestions to frontend
    
    Message format:
    - Receive: HTML string (from TipTap editor)
    - Send: JSON object {"type": "ai_suggestions", "data": {...}}
    """
    await websocket.accept()
    logger.info("WebSocket connection established")
    
    # Try to initialize AI service
    try:
        ai = get_ai()
        logger.info("✅ AI service initialized successfully")
        # Send connection success message
        success_msg = {
            "type": "connection_success",
            "message": "AI service ready",
            "timestamp": datetime.utcnow().isoformat()
        }
        await websocket.send_text(json.dumps(success_msg))
    except ValueError as e:
        logger.error(f"❌ AI service initialization failed: {str(e)}")
        error_response = {
            "type": "server_error",
            "message": "AI service not configured: Please ensure OPENAI_API_KEY is set in server/.env file",
            "details": str(e)
        }
        await websocket.send_text(json.dumps(error_response))
        await websocket.close()
        return
    except Exception as e:
        logger.error(f"❌ Unexpected AI initialization error: {str(e)}")
        error_response = {
            "type": "server_error",
            "message": "AI service initialization failed",
            "details": str(e)
        }
        await websocket.send_text(json.dumps(error_response))
        await websocket.close()
        return
    
    # Create JSON parser for each connection
    json_parser = StreamingJSONParser()
    
    while True:
        try:
            # Receive HTML content
            html_content = await websocket.receive_text()
            logger.info(f"Received HTML content, length: {len(html_content)}")
            
            # Step 1: Convert HTML to plain text
            plain_text = html_to_plain_text(html_content)
            
            # Step 2: Validate if text is suitable for AI processing
            is_valid, error_message = validate_text_for_ai(plain_text)
            
            if not is_valid:
                # Send validation error to client
                error_response = {
                    "type": "validation_error",
                    "message": error_message,
                    "details": f"HTML length: {len(html_content)}, text length: {len(plain_text)}"
                }
                await websocket.send_text(json.dumps(error_response))
                logger.warning(f"Text validation failed: {error_message}")
                continue
            
            # Step 3: Send processing start notification
            start_response = {
                "type": "processing_start",
                "message": "AI is analyzing document...",
                "text_length": len(plain_text)
            }
            await websocket.send_text(json.dumps(start_response))
            logger.info("Starting AI analysis...")
            
            # Step 4: Reset JSON parser for new analysis
            json_parser.reset()
            
            # Step 5: Call AI for streaming analysis
            try:
                async for chunk in ai.review_document(plain_text):
                    if chunk:
                        # Try to parse JSON chunk
                        parsed_result = json_parser.add_chunk(chunk)
                        
                        if parsed_result:
                            # Successfully parsed complete JSON, send to client
                            success_response = {
                                "type": "ai_suggestions",
                                "data": parsed_result,
                                "timestamp": datetime.utcnow().isoformat()
                            }
                            await websocket.send_text(json.dumps(success_response))
                            logger.info(f"AI analysis complete, found {len(parsed_result.get('issues', []))} issues")
                            break  # Complete one analysis
                            
                # If stream ends but no complete JSON, try final parse
                if json_parser.buffer:
                    logger.warning("AI stream ended but JSON incomplete, trying final parse...")
                    final_result = json_parser.add_chunk("")  # Trigger final parse attempt
                    if final_result:
                        success_response = {
                            "type": "ai_suggestions",
                            "data": final_result,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        await websocket.send_text(json.dumps(success_response))
                        logger.info("Final parse successful")
                    else:
                        # Parse failed, send error
                        error_response = {
                            "type": "parsing_error",
                            "message": "AI response parse failed",
                            "buffer_info": json_parser.get_buffer_info()
                        }
                        await websocket.send_text(json.dumps(error_response))
                        logger.error("AI response final parse failed")
                        
            except Exception as ai_error:
                # AI call error
                logger.error(f"AI service error: {ai_error}")
                error_response = {
                    "type": "ai_error", 
                    "message": f"AI service error: {str(ai_error)}",
                    "details": "Please check API key configuration and network connection"
                }
                await websocket.send_text(json.dumps(error_response))
                
        except WebSocketDisconnect:
            logger.info("Client disconnected WebSocket connection")
            break
            
        except json.JSONEncodeError as json_error:
            logger.error(f"JSON encoding error: {json_error}")
            error_response = {
                "type": "json_error",
                "message": "Server response encoding error"
            }
            # Try to send simple error message
            try:
                await websocket.send_text('{"type":"error","message":"JSON encoding error"}')
            except:
                pass
                
        except Exception as e:
            logger.error(f"WebSocket processing error: {e}")
            try:
                error_response = {
                    "type": "server_error",
                    "message": f"Server internal error: {str(e)}"
                }
                await websocket.send_text(json.dumps(error_response))
            except:
                # If connection already closed, ignore send error
                break


# Try to import enhanced endpoints (if available)
try:
    from app.enhanced_endpoints import websocket_enhanced_endpoint, chat_with_ai, ChatRequest
    
    # Register enhanced WebSocket endpoint
    @app.websocket("/ws/enhanced")
    async def enhanced_websocket_route(websocket: WebSocket):
        await websocket_enhanced_endpoint(websocket)
    
    # Register chat API endpoint
    @app.post("/api/chat")
    async def chat_endpoint(request: ChatRequest):
        return await chat_with_ai(request)
    
    logger.info("✅ Enhanced endpoints registered")
except ImportError as e:
    logger.warning(f"⚠️ Enhanced endpoints not available: {e}")


# ============================================================================
# PDF export related endpoints
# ============================================================================

@app.post("/api/documents/{document_id}/export/pdf")
async def export_document_to_pdf(
    document_id: int, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Export document current version to PDF
    
    Args:
        document_id: Document ID
        background_tasks: Background task manager for file cleanup
        db: Database session
        
    Returns:
        Response containing download URL
    """
    try:
        logger.info(f"Starting PDF export for document {document_id}...")
        
        # 1. Get document
        document = db.scalar(select(models.Document).where(models.Document.id == document_id))
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # 2. Get current active version
        current_version = db.scalar(
            select(models.DocumentVersion)
            .where(
                models.DocumentVersion.document_id == document_id,
                models.DocumentVersion.is_active == True
            )
        )
        
        if not current_version:
            raise HTTPException(status_code=404, detail="No active version found")
        
        # 3. Import PDF exporter
        try:
            from app.internal.pdf_export_simple import SimplePDFExporter as PDFExporter
        except ImportError as e:
            logger.error(f"PDF export functionality not available: {e}")
            raise HTTPException(
                status_code=500, 
                detail="PDF export functionality is not available. Please check server configuration."
            )
        
        # 4. Generate PDF
        exporter = PDFExporter()
        filename = await exporter.export_document(document, current_version)
        
        # 5. Schedule file cleanup (after 24 hours)
        background_tasks.add_task(cleanup_pdf_file, filename, delay_hours=24)
        
        logger.info(f"PDF export successful: {filename}")
        
        return {
            "status": "success",
            "filename": filename,
            "download_url": f"/api/downloads/{filename}",
            "document_title": document.title,
            "version": current_version.version_number
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF export failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"PDF export failed: {str(e)}")


@app.get("/api/downloads/{filename}")
async def download_pdf_file(filename: str):
    """
    Download PDF file
    
    Args:
        filename: PDF filename
        
    Returns:
        PDF file stream
    """
    try:
        # Validate filename security (prevent path traversal attacks)
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        # Ensure it's a PDF file
        if not filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
        # Build file path
        file_path = Path("app/static/exports") / filename
        
        # Check if file exists
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="File not found")
        
        logger.info(f"Downloading PDF file: {filename}")
        
        # Return file
        import urllib.parse
        encoded_filename = urllib.parse.quote(filename)
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type='application/pdf',
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File download failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File download failed: {str(e)}")


async def cleanup_pdf_file(filename: str, delay_hours: int = 24):
    """
    Scheduled PDF file cleanup
    
    Args:
        filename: Filename to clean up
        delay_hours: Cleanup delay time (hours)
    """
    try:
        # Wait for specified time
        await asyncio.sleep(delay_hours * 3600)
        
        file_path = Path("app/static/exports") / filename
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Scheduled cleanup of PDF file: {filename}")
        
    except Exception as e:
        logger.error(f"PDF file cleanup failed {filename}: {str(e)}")


# Clean up old PDF files on application startup
@app.on_event("startup")
async def cleanup_old_pdfs():
    """Clean up old PDF files on application startup"""
    try:
        from app.internal.pdf_export import PDFExporter
        exporter = PDFExporter()
        cleaned_count = await exporter.cleanup_old_files(max_age_hours=24)
        logger.info(f"Cleaned up {cleaned_count} old PDF files on startup")
    except Exception as e:
        logger.warning(f"PDF file cleanup on startup failed: {str(e)}")
