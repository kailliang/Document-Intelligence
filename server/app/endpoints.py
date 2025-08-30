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
from app.internal.db import get_db, SessionLocal
from app.internal.chat_manager import get_chat_manager
from app.agents.graph_builder import execute_chat_workflow

logger = logging.getLogger(__name__)

# Intent-specific processing stage configurations
INTENT_STAGE_MAPPINGS = {
    "casual_chat": [
        {"id": "intent_detection", "name": "Understanding Request", "message": "Processing your message...", "progress": 25, "agent": "system"},
        {"id": "agent_selection", "name": "Preparing Response", "message": "Setting up AI assistant...", "progress": 50, "agent": "system"},
        {"id": "finalizing_results", "name": "Generating Response", "message": "Creating response...", "progress": 90, "agent": "system"}
    ],
    "document_analysis": [
        {"id": "intent_detection", "name": "Intent Detection", "message": "Analyzing your request...", "progress": 10, "agent": "system"},
        {"id": "agent_selection", "name": "Agent Selection", "message": "Selecting appropriate AI agents...", "progress": 20, "agent": "lead"},
        {"id": "technical_analysis", "name": "Technical Analysis", "message": "Technical agent reviewing structure...", "progress": 40, "agent": "technical"},
        {"id": "legal_analysis", "name": "Legal Analysis", "message": "Legal agent investigating compliance...", "progress": 40, "agent": "legal"},
        {"id": "novelty_analysis", "name": "Novelty Analysis", "message": "Novelty agent checking innovation...", "progress": 40, "agent": "novelty"},
        {"id": "lead_synthesis", "name": "Lead Synthesis", "message": "Lead agent synthesizing findings...", "progress": 60, "agent": "lead"},
        {"id": "suggestion_mapping", "name": "Suggestion Mapping", "message": "Mapping suggestions to document...", "progress": 80, "agent": "mapping"},
        {"id": "finalizing_results", "name": "Finalizing Results", "message": "Finalizing analysis results...", "progress": 100, "agent": "system"}
    ],
    "mermaid_diagram": [
        {"id": "intent_detection", "name": "Request Analysis", "message": "Understanding diagram requirements...", "progress": 25, "agent": "system"},
        {"id": "agent_selection", "name": "Diagram Setup", "message": "Preparing diagram generator...", "progress": 75, "agent": "system"},
        {"id": "diagram_generation", "name": "Creating Diagram", "message": "Generating Mermaid diagram...", "progress": 90, "agent": "system"}
    ]
}

# Legacy processing stages (for backward compatibility)
PROCESSING_STAGES = INTENT_STAGE_MAPPINGS["document_analysis"]

async def send_processing_stage(websocket: WebSocket, stage_id: str, agent: str = "system", 
                               delay: float = 0.8, intent_type: str = "document_analysis"):
    """Send a processing stage message to the client with optional delay"""
    # Get stages for the specific intent type
    stages = INTENT_STAGE_MAPPINGS.get(intent_type, INTENT_STAGE_MAPPINGS["document_analysis"])
    stage = next((s for s in stages if s["id"] == stage_id), None)
    if not stage:
        logger.warning(f"Stage {stage_id} not found for intent {intent_type}")
        return
    
    # Add delay for realistic processing timing
    if delay > 0:
        await asyncio.sleep(delay)
    
    stage_msg = {
        "type": "processing_stage",
        "stage": stage["id"],
        "name": stage["name"],
        "message": stage["message"],
        "progress": stage["progress"],
        "agent": stage.get("agent", agent),  # Use stage's agent or fallback
        "intent_type": intent_type,  # Include intent for frontend
        "timestamp": datetime.utcnow().isoformat()
    }
    
    try:
        # Check if WebSocket is still connected before sending
        if hasattr(websocket, 'client_state') and websocket.client_state.name != 'CONNECTED':
            logger.warning(f"WebSocket not connected, skipping stage: {stage['name']}")
            return
        await websocket.send_text(json.dumps(stage_msg))
        logger.info(f"📊 Sent {intent_type} stage: {stage['name']} ({stage['progress']}%)")
    except Exception as e:
        logger.error(f"Failed to send processing stage {stage_id}: {e}")


async def send_intent_stage_list(websocket: WebSocket, intent_type: str):
    """Send the complete stage list for an intent to the frontend"""
    stages = INTENT_STAGE_MAPPINGS.get(intent_type, INTENT_STAGE_MAPPINGS["document_analysis"])
    
    stage_list_msg = {
        "type": "stage_list",
        "intent_type": intent_type,
        "stages": stages,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    try:
        await websocket.send_text(json.dumps(stage_list_msg))
        logger.info(f"📋 Sent stage list for intent: {intent_type} ({len(stages)} stages)")
    except Exception as e:
        logger.error(f"Failed to send stage list for {intent_type}: {e}")


async def simulate_progress_for_intent(websocket: WebSocket, intent_type: str):
    """Simulate realistic progress updates for a specific intent"""
    stages = INTENT_STAGE_MAPPINGS.get(intent_type, INTENT_STAGE_MAPPINGS["document_analysis"])
    
    # Different delays based on intent complexity
    delays = {
        "casual_chat": [0.3, 0.5, 0.2],  # Fast for simple chat
        "document_analysis": [0.5, 0.3, 0.8, 1.2, 1.0, 0.8, 1.0, 0.5],  # Varied for complex analysis
        "mermaid_diagram": [0.4, 0.6, 1.2, 0.8, 0.3]  # Creative process timing
    }
    
    stage_delays = delays.get(intent_type, [0.8] * len(stages))
    
    for i, stage in enumerate(stages):
        delay = stage_delays[i] if i < len(stage_delays) else 0.8
        await send_processing_stage(
            websocket, 
            stage["id"], 
            stage.get("agent", "system"), 
            delay, 
            intent_type
        )


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
    
    db_session = None
    
    try:
        # Send connection success message
        success_msg = {
            "type": "connection_success",
            "message": "AI Assistant connected and ready",
            "timestamp": datetime.utcnow().isoformat()
        }
        try:
            await websocket.send_text(json.dumps(success_msg))
            logger.info("✅ Connection success message sent")
        except Exception as e:
            logger.error(f"Failed to send connection success message: {e}")
            return
        
        while True:
            try:
                # Receive message from client
                try:
                    data = await websocket.receive_json()
                    logger.info(f"📨 Received message: {data.get('message', '')[:100]}...")
                except WebSocketDisconnect:
                    logger.info("🔌 Client disconnected during message receive")
                    break
                except Exception as e:
                    if "1001" in str(e):
                        logger.info("🔌 Client disconnected (going away)")
                        break
                    else:
                        raise e
                
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
                    try:
                        await websocket.send_text(json.dumps(error_msg))
                    except Exception as e:
                        logger.error(f"Failed to send validation error: {e}")
                        break
                    continue
                
                # Save user message to chat history
                if document_id:
                    with SessionLocal() as temp_db:
                        temp_chat_manager = get_chat_manager(temp_db)
                        await temp_chat_manager.save_user_message(
                            document_id, document_version, user_message
                        )
                
                # Stage 1: Intent Detection (quick check)
                await send_processing_stage(websocket, "intent_detection", "system", 0.3)
                
                # Use LangGraph workflow for proper intent detection and routing
                try:
                    logger.info("🤖 Using LangGraph workflow for message processing")
                    
                    # Track if we've sent stage list for this intent
                    sent_stage_lists = set()
                    
                    # Create progress callback for real-time updates
                    async def progress_callback(stage_id: str, agent: str = "system", intent_type: str = "document_analysis"):
                        """Send real-time progress updates during workflow execution"""
                        try:
                            # Send stage list once per intent when we first know the intent
                            if intent_type and intent_type not in sent_stage_lists:
                                logger.info(f"🎯 Early stage list send for intent: {intent_type}")
                                await send_intent_stage_list(websocket, intent_type)
                                sent_stage_lists.add(intent_type)
                            
                            await send_processing_stage(websocket, stage_id, agent, 0.1, intent_type)
                        except Exception as e:
                            logger.error(f"Failed to send progress update for {stage_id}: {e}")
                    
                    # Execute the full LangGraph workflow with progress callback
                    result = await execute_chat_workflow(
                        user_input=user_message,
                        document_content=document_content,
                        document_id=document_id,
                        version_number=document_version,
                        chat_history=[],  # You can add actual chat history if needed
                        progress_callback=progress_callback
                    )
                    
                    # Extract results from workflow
                    messages = result.get("messages", [])
                    intent_detected = result.get("intent_detected", "unknown")
                    agents_used = result.get("agents_used", [])
                    
                    logger.info(f"✅ Workflow completed - Intent: {intent_detected}")
                    
                    # Handle empty response
                    if not messages:
                        messages = [{
                            "type": "text",
                            "content": "I'm here to help! You can ask me questions about your document or request an analysis."
                        }]
                        intent_detected = "casual_chat"  # Changed from "chat" to match intent types
                        agents_used = ["system"]
                    
                    # Map intent names for consistency
                    intent_mapping = {
                        "chat": "casual_chat",
                        "casual": "casual_chat",
                        "analysis": "document_analysis",
                        "document": "document_analysis",
                        "diagram": "mermaid_diagram",
                        "mermaid": "mermaid_diagram"
                    }
                    intent_detected = intent_mapping.get(intent_detected, intent_detected)
                    
                    # Stage list already sent during workflow execution via progress_callback
                    logger.info(f"📋 Stage list already sent for intent: {intent_detected}")
                    
                    # Save messages to chat history (if needed)
                    if document_id:
                        with SessionLocal() as temp_db:
                            temp_chat_manager = get_chat_manager(temp_db)
                            for i, message in enumerate(messages):
                                if message.get("type") == "text":
                                    saved_message = await temp_chat_manager.save_assistant_message(
                                        document_id, document_version, message["content"], agents_used
                                    )
                                    messages[i]["message_id"] = saved_message.id
                                # Add other message type handling as needed
                    
                except Exception as e:
                    logger.error(f"❌ AI processing error: {e}")
                    content = "I apologize, but I'm experiencing technical difficulties. Please try again in a moment."
                    messages = [{
                        "type": "text",
                        "content": content
                    }]
                    intent_detected = "error"
                    agents_used = ["system"]
                
                # Send response to client
                response = {
                    "type": "assistant_response",
                    "messages": messages,
                    "intent_detected": intent_detected,
                    "agents_used": agents_used,
                    "timestamp": datetime.utcnow().isoformat()
                }
                try:
                    await websocket.send_text(json.dumps(response))
                    logger.info(f"📤 Response sent: {len(messages)} messages")
                except Exception as e:
                    logger.error(f"Failed to send response: {e}")
                    break
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ JSON decode error: {e}")
                error_msg = {
                    "type": "json_error",
                    "message": "Invalid message format",
                    "timestamp": datetime.utcnow().isoformat()
                }
                try:
                    await websocket.send_text(json.dumps(error_msg))
                except Exception as send_e:
                    logger.error(f"Failed to send JSON error message: {send_e}")
                    break
                
            except Exception as e:
                # Check if it's a client disconnect before logging as error
                if "1001" in str(e) or isinstance(e, WebSocketDisconnect):
                    logger.info("🔌 Client disconnected during message processing")
                    break
                else:
                    logger.error(f"❌ Message processing error: {e}")
                    error_msg = {
                        "type": "processing_error",
                        "message": f"Failed to process message: {str(e)}",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    try:
                        await websocket.send_text(json.dumps(error_msg))
                    except Exception as send_e:
                        logger.info(f"Client disconnected while sending error message")
                        break
    
    except WebSocketDisconnect:
        logger.info("🔌 Unified chat WebSocket connection disconnected")
    except Exception as e:
        # Don't log as error if it's a normal client disconnect (1001 = going away)
        if "1001" in str(e):
            logger.info("🔌 Client disconnected (going away)")
        else:
            logger.error(f"❌ Unified chat WebSocket error: {e}")
    finally:
        # WebSocket cleanup - database sessions are handled per operation
        pass


# Chat history management implementations
async def load_chat_history_for_version(document_id: int, version_number: str) -> Dict:
    """
    Load chat history for a specific document version.
    """
    logger.info(f"📚 Loading chat history for document {document_id}, version {version_number}")
    
    try:
        # Use session context manager for proper cleanup
        with SessionLocal() as db_session:
            chat_manager = get_chat_manager(db_session)
            
            # Load chat history
            chat_messages = await chat_manager.load_chat_history(document_id, version_number)
            
            # Convert to API format
            api_messages = []
            for chat_msg in chat_messages:
                api_message = chat_msg.to_dict()
                api_messages.append(api_message)
        
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


async def handle_suggestion_card_action(message_id: int, card_id: str, action: str) -> Dict:
    """
    Handle suggestion card actions (accept/dismiss).
    """
    logger.info(f"🎯 Handling card action: {action} for card {card_id}")
    
    try:
        # Use session context manager for proper cleanup
        with SessionLocal() as db_session:
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


async def clear_chat_history_for_version(document_id: int, version_number: str) -> Dict:
    """
    Clear all chat history for a specific document version.
    """
    logger.info(f"🗑️ Clearing chat history for document {document_id}, version {version_number}")
    
    try:
        # Use session context manager for proper cleanup
        with SessionLocal() as db_session:
            chat_manager = get_chat_manager(db_session)
            
            # Clear chat history
            success = await chat_manager.clear_chat_history(document_id, version_number)
            
            if success:
                logger.info(f"✅ Chat history cleared successfully for doc {document_id} v{version_number}")
                return {
                    "success": True,
                    "message": f"Chat history cleared for document {document_id} version {version_number}",
                    "document_id": document_id,
                    "version_number": version_number
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to clear chat history",
                    "document_id": document_id,
                    "version_number": version_number
                }
        
    except Exception as e:
        logger.error(f"Error clearing chat history: {e}")
        return {
            "success": False,
            "error": str(e),
            "document_id": document_id,
            "version_number": version_number
        }