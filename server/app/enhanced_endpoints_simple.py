# Simple enhanced endpoints for testing the unified chat integration

from datetime import datetime
import json
import logging
import asyncio
from typing import List, Dict, Optional

from fastapi import WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.internal.ai_enhanced import get_ai_enhanced
from app.internal.text_utils import html_to_plain_text, validate_text_for_ai
from app.internal.db import get_db
from app.internal.chat_manager import get_chat_manager

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


# New unified chat WebSocket endpoint for integrated AI assistant
async def unified_chat_websocket_endpoint(websocket: WebSocket):
    """
    Unified WebSocket endpoint for integrated AI assistant.
    
    This endpoint handles chat with persistent history management.
    TODO: Implement full LangGraph multi-agent workflow.
    """
    await websocket.accept()
    logger.info("🔌 Unified chat WebSocket connection established")
    
    # Initialize database session and chat manager
    db_session = next(get_db())
    chat_manager = get_chat_manager(db_session)
    
    try:
        # Send connection success message
        success_msg = {
            "type": "connection_success",
            "message": "AI Assistant connected and ready",
            "timestamp": datetime.utcnow().isoformat()
        }
        await websocket.send_text(json.dumps(success_msg))
        logger.info("✅ Connection success message sent")
        
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_json()
                logger.info(f"📨 Received message: {data.get('message', '')[:100]}...")
                
                # Extract message data
                user_message = data.get("message", "")
                document_content = data.get("document_content", "")
                document_id = data.get("document_id")
                document_version = data.get("document_version", "v1.0")
                
                if not user_message.strip():
                    error_msg = {
                        "type": "validation_error",
                        "message": "Please provide a message",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await websocket.send_text(json.dumps(error_msg))
                    continue
                
                # Save user message to chat history
                if document_id:
                    await chat_manager.save_user_message(
                        document_id, document_version, user_message
                    )
                
                # Send processing start message
                processing_msg = {
                    "type": "processing_start",
                    "message": "Processing your request...",
                    "timestamp": datetime.utcnow().isoformat()
                }
                await websocket.send_text(json.dumps(processing_msg))
                
                # TEMPORARY: Simple response without LangGraph workflow
                # TODO: Replace with full LangGraph implementation
                await asyncio.sleep(1)  # Simulate processing time
                
                # Determine intent based on keywords
                user_lower = user_message.lower()
                if any(keyword in user_lower for keyword in ["analyze", "review", "check", "improve", "suggest"]):
                    # Document analysis request - return mock suggestion cards
                    cards = [{
                        "id": f"demo_{datetime.utcnow().timestamp()}",
                        "type": "Structure & Format",
                        "severity": "medium",
                        "paragraph": 1,
                        "description": "This is a demo suggestion. Full LangGraph integration is not yet implemented.",
                        "original_text": "sample text",
                        "replace_to": "improved sample text",
                        "confidence": 0.85,
                        "agent": "technical",
                        "created_at": datetime.utcnow().isoformat()
                    }]
                    
                    messages = [{
                        "type": "suggestion_cards",
                        "cards": cards
                    }]
                    intent_detected = "document_analysis"
                    agents_used = ["demo"]
                    
                    # Save suggestion cards to chat history
                    if document_id:
                        await chat_manager.save_suggestion_cards(
                            document_id, document_version, cards, agents_used
                        )
                else:
                    # Regular chat response
                    content = f"I received your message: '{user_message}'. This is a demo response. Full LangGraph integration is coming soon!"
                    messages = [{
                        "type": "text",
                        "content": content
                    }]
                    intent_detected = "casual_chat"
                    agents_used = ["demo"]
                    
                    # Save assistant message to chat history
                    if document_id:
                        await chat_manager.save_assistant_message(
                            document_id, document_version, content, agents_used
                        )
                
                # Send response to client
                response = {
                    "type": "assistant_response",
                    "messages": messages,
                    "intent_detected": intent_detected,
                    "agents_used": agents_used,
                    "timestamp": datetime.utcnow().isoformat()
                }
                await websocket.send_text(json.dumps(response))
                logger.info(f"📤 Response sent: {len(messages)} messages")
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ JSON decode error: {e}")
                error_msg = {
                    "type": "json_error",
                    "message": "Invalid message format",
                    "timestamp": datetime.utcnow().isoformat()
                }
                await websocket.send_text(json.dumps(error_msg))
                
            except Exception as e:
                logger.error(f"❌ Message processing error: {e}")
                error_msg = {
                    "type": "processing_error",
                    "message": f"Failed to process message: {str(e)}",
                    "timestamp": datetime.utcnow().isoformat()
                }
                await websocket.send_text(json.dumps(error_msg))
    
    except WebSocketDisconnect:
        logger.info("🔌 Unified chat WebSocket connection disconnected")
    except Exception as e:
        logger.error(f"❌ Unified chat WebSocket error: {e}")
    finally:
        # Clean up database session
        if db_session:
            db_session.close()


# Chat history management implementations
async def load_chat_history_for_version(document_id: int, version_number: str) -> Dict:
    """
    Load chat history for a specific document version.
    """
    logger.info(f"📚 Loading chat history for document {document_id}, version {version_number}")
    
    try:
        # Get database session and chat manager
        db_session = next(get_db())
        chat_manager = get_chat_manager(db_session)
        
        # Load chat history
        chat_messages = await chat_manager.load_chat_history(document_id, version_number)
        
        # Convert to API format
        api_messages = []
        for chat_msg in chat_messages:
            api_message = chat_msg.to_dict()
            api_messages.append(api_message)
        
        db_session.close()
        
        return {
            "success": True,
            "messages": api_messages,
            "document_id": document_id,
            "version_number": version_number,
            "message_count": len(api_messages)
        }
        
    except Exception as e:
        logger.error(f"Error loading chat history: {e}")
        return {
            "success": False,
            "error": str(e),
            "messages": [],
            "document_id": document_id,
            "version_number": version_number,
            "message_count": 0
        }


async def handle_suggestion_card_action(document_id: int, version_number: str,
                                      message_id: int, card_id: str, action: str) -> Dict:
    """
    Handle suggestion card actions (accept/dismiss).
    """
    logger.info(f"🎯 Handling card action: {action} for card {card_id}")
    
    try:
        # Get database session and chat manager
        db_session = next(get_db())
        chat_manager = get_chat_manager(db_session)
        
        # Mark the card action
        success = await chat_manager.mark_suggestion_card_action(message_id, card_id, action)
        
        if success:
            logger.info(f"✅ Card {card_id} marked as {action}")
            
            # Check if we should remove the message (all cards acted upon)
            if action in ['accepted', 'dismissed']:
                removed = await chat_manager.remove_suggestion_card_message(message_id)
                if removed:
                    logger.info(f"🗑️ Removed suggestion cards message {message_id} (all cards acted upon)")
        
        db_session.close()
        
        return {
            "success": success,
            "message": f"Card {action} successfully" if success else f"Failed to {action} card"
        }
        
    except Exception as e:
        logger.error(f"Error handling card action: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to {action} card"
        }