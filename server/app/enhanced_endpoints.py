# Enhanced endpoints for the application

from datetime import datetime
import json
import logging
from typing import List, Dict

from fastapi import WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel

from app.internal.ai_enhanced import get_ai_enhanced
from app.internal.text_utils import html_to_plain_text, validate_text_for_ai

logger = logging.getLogger(__name__)


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    current_document_content: str = ""  # New: current document content


async def websocket_enhanced_endpoint(websocket: WebSocket):
    """
    Enhanced WebSocket endpoint: AI suggestion system with Function Calling support
    
    Features:
    - Use Function Calling for more precise text matching
    - Support originalText and replaceTo fields
    - More accurate suggestion content
    """
    await websocket.accept()
    logger.info("Enhanced WebSocket connection established")
    
    # Try to initialize enhanced AI service
    try:
        ai = get_ai_enhanced()
        logger.info("✅ Enhanced AI service initialized successfully")
        # Send connection success message
        success_msg = {
            "type": "connection_success",
            "message": "Enhanced AI service ready",
            "timestamp": datetime.utcnow().isoformat()
        }
        await websocket.send_text(json.dumps(success_msg))
    except ValueError as e:
        logger.error(f"Enhanced AI service initialization failed: {e}")
        error_msg = {
            "type": "ai_error",
            "message": f"AI service initialization failed: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }
        await websocket.send_text(json.dumps(error_msg))
        await websocket.close()
        return
    
    try:
        while True:
            # Receive HTML content
            html_content = await websocket.receive_text()
            logger.info(f"Received HTML content, length: {len(html_content)}")
            
            # Notify frontend processing started
            processing_msg = {
                "type": "processing_start",
                "message": "Analysing document...",
                "timestamp": datetime.utcnow().isoformat()
            }
            await websocket.send_text(json.dumps(processing_msg))
            
            try:
                # Convert HTML to plain text
                plain_text = html_to_plain_text(html_content)
                logger.info(f"Converted plain text length: {len(plain_text)}")
                
                # Validate text content
                is_valid, error_message = validate_text_for_ai(plain_text)
                if not is_valid:
                    logger.warning(f"Text validation failed: {error_message}")
                    validation_error = {
                        "type": "validation_error",
                        "message": error_message,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await websocket.send_text(json.dumps(validation_error))
                    continue
                
                # Use enhanced AI analysis (supports Function Calling)
                logger.info("Starting enhanced AI document analysis...")
                response_chunks = []
                
                async for chunk in ai.review_document_with_functions(plain_text):
                    if chunk:
                        response_chunks.append(chunk)
                
                # Merge all responses
                full_response = "".join(response_chunks)
                
                try:
                    # Parse JSON response
                    parsed_result = json.loads(full_response)
                    
                    # Send complete suggestion results
                    success_response = {
                        "type": "ai_suggestions",
                        "data": parsed_result,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await websocket.send_text(json.dumps(success_response))
                    logger.info(f"Enhanced AI analysis complete, found {len(parsed_result.get('issues', []))} issues")
                    
                except json.JSONDecodeError as e:
                    logger.error(f"JSON parsing failed: {e}")
                    error_response = {
                        "type": "parsing_error",
                        "message": "AI response parsing failed",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await websocket.send_text(json.dumps(error_response))
                    
            except Exception as e:
                logger.error(f"Error during analysis processing: {e}")
                error_response = {
                    "type": "ai_error",
                    "message": f"AI analysis failed: {str(e)}",
                    "timestamp": datetime.utcnow().isoformat()
                }
                await websocket.send_text(json.dumps(error_response))
                
    except WebSocketDisconnect:
        logger.info("Enhanced WebSocket connection disconnected")
    except Exception as e:
        logger.error(f"Enhanced WebSocket processing error: {e}")
        try:
            error_response = {
                "type": "server_error",
                "message": f"Server internal error: {str(e)}"
            }
            await websocket.send_text(json.dumps(error_response))
        except:
            pass


async def chat_with_ai(request: ChatRequest):
    """
    Enhanced AI chat functionality endpoint
    
    Supports AI conversation with document context, including:
    - Patent Q&A based on current document content
    - Precise diagram insertion in documents
    - Patent claims analysis and suggestions
    """
    try:
        ai = get_ai_enhanced()
        
        # Build message history
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        
        # Use chat functionality with document context
        response_chunks = []
        diagram_insertions = []
        
        async for chunk in ai.chat_with_document_context(messages, request.current_document_content):
            if chunk:
                # Check if it's a diagram insertion instruction
                if chunk.startswith("DIAGRAM_INSERT:"):
                    try:
                        diagram_data = json.loads(chunk[15:])  # Remove prefix
                        diagram_insertions.append(diagram_data)
                        logger.info(f"📊 Collected diagram insertion request: {diagram_data}")
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Diagram insertion data parsing failed: {e}")
                else:
                    response_chunks.append(chunk)
        
        full_response = "".join(response_chunks)
        
        # Build response, including diagram insertion information
        result = {"response": full_response}
        if diagram_insertions:
            result["diagram_insertions"] = diagram_insertions
            logger.info(f"✅ Returning response contains {len(diagram_insertions)} diagram insertions")
        
        return result
        
    except Exception as e:
        logger.error(f"Chat processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))