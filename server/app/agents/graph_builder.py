"""
LangGraph Workflow Builder for Patent Document Analysis

This module builds and configures the LangGraph workflow that coordinates
all agents and handles the complete chat and analysis pipeline.
"""

import logging
import operator
from typing import Dict, Any, Optional, Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, SystemMessage
from openai import AsyncOpenAI
import os

from .intent_detector import detect_intent_node, should_route_to_casual_chat, should_route_to_document_analysis, should_route_to_mermaid_diagram
from .technical_agent import technical_analysis_node
from .legal_agent import legal_analysis_node
from .novelty_agent import novelty_analysis_node
from .lead_agent import lead_evaluation_node
from .mapping_agent import mapping_analysis_node
from ..internal.mermaid_render import generate_mermaid_node
from ..internal.text_utils import html_to_plain_text, create_chunks_from_text, convert_chunks_to_full_text
from ..internal.suggestion_generator import generate_suggestions_from_chunk_mapping

logger = logging.getLogger(__name__)


class ChatWorkflowState(TypedDict):
    """
    State object for the LangGraph workflow with proper reducers for parallel execution.
    
    This maintains all state information as the workflow progresses through different nodes.
    Fields with Annotated[list, operator.add] can be safely updated by parallel nodes.
    """
    # Core workflow fields
    user_input: str
    document_content: str
    document_id: Optional[int]
    version_number: Optional[str]
    openai_client: Any
    intent: Optional[str]
    progress_callback: Optional[Any]  # Callback for progress updates
    
    # Fields that may be updated by parallel nodes (need reducers)
    technical_suggestions: Annotated[list, operator.add]
    legal_suggestions: Annotated[list, operator.add]
    novelty_suggestions: Annotated[list, operator.add]
    all_suggestions: Annotated[list, operator.add]
    messages: Annotated[list, operator.add]
    agents_used: Annotated[list, operator.add]
    errors: Annotated[list, operator.add]
    chat_history: Annotated[list, operator.add]
    
    # New chunking fields
    original_chunks: Optional[list]
    improved_documents: Annotated[list, operator.add]
    final_improved_document: Optional[str]
    chunk_mapping: Optional[Dict[str, Any]]
    suggested_chunks: Optional[list]  # Store chunks to maintain ID consistency
    
    # Optional workflow fields
    intent_confidence: Optional[str]
    document_processed: Optional[bool]
    content_length: Optional[int]
    estimated_paragraphs: Optional[int]
    agents_recruited: Optional[list]
    recruitment_complete: Optional[bool]
    final_analysis: Optional[Dict[str, Any]]
    error: Optional[str]


def create_chat_workflow() -> StateGraph:
    """
    Create and configure the complete LangGraph workflow.
    
    Returns:
        Compiled StateGraph ready for execution
    """
    logger.info("Building LangGraph chat workflow")
    
    # Create the state graph with properly defined state and reducers
    workflow = StateGraph(ChatWorkflowState)
    
    # Add all nodes to the workflow
    workflow.add_node("intent_detector", detect_intent_node)
    workflow.add_node("document_loader", load_document_context_node)
    workflow.add_node("casual_responder", handle_casual_chat_node)
    workflow.add_node("mermaid_generator", generate_mermaid_node)
    workflow.add_node("agent_recruiter", recruit_agents_node)
    workflow.add_node("technical_agent", technical_analysis_node)
    workflow.add_node("legal_agent", legal_analysis_node)
    workflow.add_node("novelty_agent", novelty_analysis_node)
    workflow.add_node("suggestions_aggregator", aggregate_suggestions_node)
    workflow.add_node("lead_agent", lead_evaluation_node)
    workflow.add_node("mapping_agent", mapping_analysis_node)
    workflow.add_node("response_formatter", format_final_response_node)
    
    # Set entry point
    workflow.set_entry_point("intent_detector")
    
    # Add conditional routing from intent detector
    workflow.add_conditional_edges(
        "intent_detector",
        route_by_intent,
        {
            "casual_chat": "casual_responder",
            "document_analysis": "document_loader",
            "mermaid_diagram": "mermaid_generator"
        }
    )
    
    # Document analysis workflow
    workflow.add_edge("document_loader", "agent_recruiter")
    
    # Parallel agent processing
    workflow.add_edge("agent_recruiter", "technical_agent")
    workflow.add_edge("agent_recruiter", "legal_agent")
    workflow.add_edge("agent_recruiter", "novelty_agent")
    
    # All agents feed into suggestions aggregator (fixes concurrent update issue)
    workflow.add_edge("technical_agent", "suggestions_aggregator")
    workflow.add_edge("legal_agent", "suggestions_aggregator")
    workflow.add_edge("novelty_agent", "suggestions_aggregator")
    
    # Aggregator feeds into lead agent
    workflow.add_edge("suggestions_aggregator", "lead_agent")
    
    # Lead agent feeds into mapping agent
    workflow.add_edge("lead_agent", "mapping_agent")
    
    # Mapping agent feeds into response formatter  
    workflow.add_edge("mapping_agent", "response_formatter")
    
    # Terminal nodes
    workflow.add_edge("casual_responder", END)
    workflow.add_edge("mermaid_generator", END)
    workflow.add_edge("response_formatter", END)
    
    logger.info("LangGraph workflow structure complete")
    
    # Compile and return the workflow
    return workflow.compile()


def route_by_intent(state: ChatWorkflowState) -> str:
    """
    Route workflow based on detected intent.
    
    Args:
        state: Current workflow state
        
    Returns:
        Next node name based on intent
    """
    intent = state.get("intent", "casual_chat")
    
    logger.info(f"Routing based on intent: {intent}")
    
    if intent == "casual_chat":
        return "casual_chat"
    elif intent == "document_analysis":
        return "document_analysis"
    elif intent == "mermaid_diagram":
        return "mermaid_diagram"
    else:
        # Default to casual chat for unknown intents
        logger.warning(f"Unknown intent '{intent}', defaulting to casual_chat")
        return "casual_chat"


async def load_document_context_node(state: ChatWorkflowState) -> ChatWorkflowState:
    """
    Load document context and prepare for analysis.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with document context
    """
    try:
        # Send progress update
        if state.get("progress_callback"):
            await state["progress_callback"]("document_parsing", "system", state.get("intent", "document_analysis"))
            
        logger.info("Loading document context")
        
        # Get document content from state
        document_content = state.get("document_content", "")
        
        if not document_content:
            logger.warning("No document content provided")
            return {
                **state,
                "document_processed": False,
                "error": "No document content available for analysis"
            }
        
        # Convert HTML to plain text for analysis
        try:
            plain_text = html_to_plain_text(document_content)
            if not plain_text or len(plain_text.strip()) < 50:
                return {
                    **state,
                    "document_processed": False,
                    "error": "Document content is too short or empty for meaningful analysis"
                }
        except Exception as e:
            logger.error(f"Failed to process document content: {e}")
            return {
                **state,
                "document_processed": False,
                "error": f"Failed to process document content: {str(e)}"
            }
        
        # Create chunks from plain text
        try:
            original_chunks = create_chunks_from_text(plain_text)
            if not original_chunks:
                return {
                    **state,
                    "document_processed": False,
                    "error": "Failed to create chunks from document"
                }
            
            # Convert chunks to agent-friendly format (single newlines)
            agent_text = convert_chunks_to_full_text(original_chunks)
            
            logger.info(f"Created {len(original_chunks)} chunks for agent processing")
            
        except Exception as e:
            logger.error(f"Failed to chunk document: {e}")
            return {
                **state,
                "document_processed": False,
                "error": f"Failed to chunk document: {str(e)}"
            }
        
        # Update state with processed document and chunks
        updated_state = {
            **state,
            "document_content": agent_text,  # Use agent-friendly format for analysis
            "original_chunks": [chunk.to_dict() for chunk in original_chunks],  # Store original chunks
            "document_processed": True,
            "content_length": len(agent_text),
            "estimated_paragraphs": len(original_chunks)
        }
        
        logger.info(f"Document context loaded: {len(plain_text)} characters, "
                   f"{updated_state['estimated_paragraphs']} paragraphs")
        
        return updated_state
        
    except Exception as e:
        logger.error(f"Document context loading failed: {e}")
        return {
            **state,
            "document_processed": False,
            "error": str(e)
        }


async def handle_casual_chat_node(state: ChatWorkflowState) -> ChatWorkflowState:
    """
    Handle casual chat conversations.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with casual chat response
    """
    try:
        logger.info("Handling casual chat")
        
        user_input = state.get("user_input", "")
        openai_client = state.get("openai_client")
        
        if not openai_client:
            return {
                **state,
                "messages": [{
                    "type": "text",
                    "content": "I'm here to help with patent document analysis. How can I assist you today?",
                    "timestamp": "2024-01-01T00:00:00Z"
                }],
                "intent": "casual_chat"
            }
        
        # Generate casual chat response
        response = await openai_client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4.1"),
            temperature=0.7,  # Higher temperature for more conversational responses
            max_tokens=300,
            messages=[
                {
                    "role": "system", 
                    "content": """You are a helpful AI assistant specializing in patent document analysis. 
                    Respond to casual conversation in a friendly, professional manner. 
                    Keep responses concise and always offer to help with patent document analysis tasks.
                    If users ask about your capabilities, mention that you can analyze patents for technical, 
                    legal, and novelty issues, and can also generate diagrams."""
                },
                {"role": "user", "content": user_input}
            ]
        )
        
        chat_response = response.choices[0].message.content
        
        return {
            **state,
            "messages": [{
                "type": "text",
                "content": chat_response,
                "timestamp": "2024-01-01T00:00:00Z"
            }],
            "intent": "casual_chat"
        }
        
    except Exception as e:
        logger.error(f"Casual chat handling failed: {e}")
        return {
            **state,
            "messages": [{
                "type": "text",
                "content": "I'm here to help with patent document analysis. What would you like to know?",
                "timestamp": "2024-01-01T00:00:00Z"
            }],
            "intent": "casual_chat",
            "error": str(e)
        }


async def recruit_agents_node(state: ChatWorkflowState) -> ChatWorkflowState:
    """
    Recruit and prepare specialized agents for analysis.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with agent recruitment information
    """
    try:
        # Send progress update
        if state.get("progress_callback"):
            await state["progress_callback"]("agent_selection", "lead", state.get("intent", "document_analysis"))
            
        logger.info("Recruiting specialized agents for analysis")
        
        # Check if document is ready for analysis
        if not state.get("document_processed", False):
            return {
                **state,
                "agents_recruited": [],
                "error": "Document not ready for analysis"
            }
        
        # Determine which agents to recruit based on user input and document
        user_input = state.get("user_input", "").lower()
        recruited_agents = []
        
        # Always recruit all three agents for comprehensive analysis
        # But could be made selective based on user input in the future
        recruited_agents = ["technical", "legal", "novelty"]
        
        # Log recruitment decision
        logger.info(f"Recruited agents: {recruited_agents}")
        
        return {
            **state,
            "agents_recruited": recruited_agents,
            "recruitment_complete": True
        }
        
    except Exception as e:
        logger.error(f"Agent recruitment failed: {e}")
        return {
            **state,
            "agents_recruited": [],
            "error": str(e)
        }


async def aggregate_suggestions_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Aggregate improved documents from all parallel agents.
    
    This node collects improved documents from technical, legal, and novelty agents
    that run in parallel and prepares them for lead agent synthesis.
    
    Args:
        state: Current workflow state with agent improved documents
        
    Returns:
        Updated state with aggregated improved documents
    """
    try:
        logger.info("Aggregating improved documents from parallel agents")
        
        # The improved_documents field is automatically aggregated by LangGraph
        # because it has the operator.add annotation in ChatWorkflowState
        improved_documents = state.get("improved_documents", [])
        
        # Ensure we have the expected agent contributions
        agent_names = {doc.get("agent", "unknown") for doc in improved_documents}
        expected_agents = {"technical", "legal", "novelty"}
        
        logger.info(f"Received improved documents from agents: {list(agent_names)}")
        logger.info(f"Expected agents: {list(expected_agents)}")
        
        # Check if all expected agents contributed
        if not expected_agents.issubset(agent_names):
            missing_agents = expected_agents - agent_names
            logger.warning(f"Missing improved documents from agents: {list(missing_agents)}")
        
        logger.info(f"Aggregated {len(improved_documents)} improved documents from agents")
        
        # Return empty dict since improved_documents is automatically aggregated
        # Just ensure agents_used is updated
        contributing_agents = list(agent_names) if agent_names else ["technical", "legal", "novelty"]
        
        return {
            "agents_used": contributing_agents
        }
        
    except Exception as e:
        logger.error(f"Error aggregating suggestions: {e}")
        return {
            "agents_used": [],
            "error": str(e)
        }


async def format_final_response_node(state: ChatWorkflowState) -> ChatWorkflowState:
    """
    Format the final response with all analysis results.
    
    Args:
        state: Current workflow state with all analysis results
        
    Returns:
        Final state with formatted response messages
    """
    try:
        # Send progress update for finalizing results
        if state.get("progress_callback"):
            await state["progress_callback"]("finalizing_results", "system", state.get("intent", "document_analysis"))
            
        logger.info("Formatting final response")
        
        # Get chunk mapping and generate suggestions
        chunk_mapping = state.get("chunk_mapping", {})
        original_chunks = state.get("original_chunks", [])
        final_improved_document = state.get("final_improved_document", "")
        agents_used = state.get("agents_used", [])
        
        # Generate suggestions from chunk mapping
        suggestions = []
        suggested_chunks = state.get("suggested_chunks", [])
        
        if chunk_mapping and original_chunks and suggested_chunks:
            try:
                # Send progress update for generating suggestions
                if state.get("progress_callback"):
                    await state["progress_callback"]("generating_suggestions", "lead", state.get("intent", "document_analysis"))
                
                # Use stored suggested chunks to maintain ID consistency
                logger.info(f"Using stored suggested chunks: {len(suggested_chunks)} chunks")
                
                # Generate suggestion cards
                suggestions = generate_suggestions_from_chunk_mapping(
                    chunk_mapping, original_chunks, suggested_chunks
                )
                
                logger.info(f"Generated {len(suggestions)} suggestion cards from chunk mapping")
                
            except Exception as e:
                logger.error(f"Failed to generate suggestions from chunk mapping: {e}")
                suggestions = []
        elif chunk_mapping and original_chunks and final_improved_document:
            try:
                # Fallback: create chunks if not stored (shouldn't happen normally)
                logger.warning("Suggested chunks not found in state, recreating (may cause ID mismatch)")
                suggested_chunks_objects = create_chunks_from_text(final_improved_document)
                suggested_chunks = [chunk.to_dict() for chunk in suggested_chunks_objects]
                
                # Generate suggestion cards
                suggestions = generate_suggestions_from_chunk_mapping(
                    chunk_mapping, original_chunks, suggested_chunks
                )
                
                logger.info(f"Generated {len(suggestions)} suggestion cards from chunk mapping (fallback)")
                
            except Exception as e:
                logger.error(f"Failed to generate suggestions from chunk mapping (fallback): {e}")
                suggestions = []
        else:
            logger.warning("Missing chunk mapping data for suggestion generation")
        
        if not suggestions:
            return {
                "messages": [{
                    "type": "text",
                    "content": "I've analyzed your document and everything looks good! No specific improvements were identified at this time.",
                    "timestamp": "2024-01-01T00:00:00Z"
                }],
                "intent": "document_analysis",
                "agents_used": agents_used
            }
        
        # Create response messages
        messages = []
        
        # Add introductory message
        intro_message = f"I've analyzed your patent document using {len(agents_used)} specialized agents. "
        intro_message += f"Here are {len(suggestions)} suggestions for improvement:"
        
        messages.append({
            "type": "text",
            "content": intro_message,
            "timestamp": "2024-01-01T00:00:00Z"
        })
        
        # Add suggestion cards message
        messages.append({
            "type": "suggestion_cards",
            "cards": suggestions,
            "timestamp": "2024-01-01T00:00:00Z"
        })
        
        logger.info(f"Final response formatted: {len(messages)} messages, {len(suggestions)} suggestion cards")
        
        return {
            "messages": messages,
            "intent": "document_analysis",
            "agents_used": agents_used
        }
        
    except Exception as e:
        logger.error(f"Response formatting failed: {e}")
        return {
            "messages": [{
                "type": "text",
                "content": "I encountered an issue while formatting the analysis results. Please try again.",
                "timestamp": "2024-01-01T00:00:00Z"
            }],
            "intent": "document_analysis",
            "error": str(e)
        }


def create_initial_state(user_input: str, document_content: str = "",
                        document_id: Optional[int] = None,
                        version_number: Optional[str] = None,
                        chat_history: Optional[list] = None,
                        progress_callback: Optional[callable] = None) -> ChatWorkflowState:
    """
    Create initial state for the workflow that matches ChatWorkflowState structure.
    
    Args:
        user_input: User's message
        document_content: Document content (if any)
        document_id: Document ID (if any)
        version_number: Document version (if any)
        chat_history: Previous chat history (if any)
        
    Returns:
        Initial workflow state
    """
    # Get OpenAI client
    openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # Create initial state matching TypedDict structure
    initial_state: ChatWorkflowState = {
        # Required core fields
        "user_input": user_input,
        "document_content": document_content or "",
        "document_id": document_id,
        "version_number": version_number,
        "openai_client": openai_client,
        "intent": None,
        "progress_callback": progress_callback,
        
        # Fields with reducers (start as empty lists)
        "technical_suggestions": [],
        "legal_suggestions": [],
        "novelty_suggestions": [],
        "all_suggestions": [],
        "messages": [],
        "agents_used": [],
        "errors": [],
        "chat_history": chat_history or [],
        
        # Optional fields
        "intent_confidence": None,
        "document_processed": None,
        "content_length": None,
        "estimated_paragraphs": None,
        "agents_recruited": None,
        "recruitment_complete": None,
        "final_analysis": None,
        "error": None
    }
    
    return initial_state


async def execute_chat_workflow(user_input: str, document_content: str = "",
                               document_id: Optional[int] = None,
                               version_number: Optional[str] = None,
                               chat_history: Optional[list] = None,
                               progress_callback: Optional[callable] = None) -> Dict[str, Any]:
    """
    Execute the complete chat workflow.
    
    Args:
        user_input: User's message
        document_content: Document content for analysis
        document_id: Document ID
        version_number: Document version
        chat_history: Previous chat history
        progress_callback: Optional callback for progress updates
        
    Returns:
        Workflow execution result
    """
    try:
        logger.info(f"Executing chat workflow for input: {user_input[:100]}...")
        
        # Create workflow
        workflow = create_chat_workflow()
        
        # Create initial state
        initial_state = create_initial_state(
            user_input=user_input,
            document_content=document_content,
            document_id=document_id,
            version_number=version_number,
            chat_history=chat_history,
            progress_callback=progress_callback
        )
        
        # Add debug logging
        logger.info(f"Initial state keys: {initial_state.keys()}")
        logger.info(f"Initial document_content length: {len(initial_state.get('document_content', ''))}")
        logger.info(f"User input: {initial_state.get('user_input', 'None')[:100]}...")
        
        # Execute workflow
        result = await workflow.ainvoke(initial_state)
        
        # Debug the result
        logger.info(f"Workflow result keys: {result.keys() if result else 'None'}")
        logger.info(f"Workflow messages: {result.get('messages', []) if result else 'None'}")
        logger.info(f"Intent detected: {result.get('intent', 'unknown')}")
        
        logger.info("Chat workflow execution completed successfully")
        
        return {
            "type": "assistant_response",
            "messages": result.get("messages", []),
            "intent_detected": result.get("intent", "unknown"),
            "agents_used": result.get("agents_used", []),
            "timestamp": "2024-01-01T00:00:00Z",
            "success": True
        }
        
    except Exception as e:
        logger.error(f"Chat workflow execution failed: {e}")
        
        return {
            "type": "error",
            "message": f"I encountered an error while processing your request: {str(e)}",
            "timestamp": "2024-01-01T00:00:00Z",
            "success": False
        }


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    async def test_workflow():
        """Test the workflow with sample inputs"""
        
        # Test cases
        test_cases = [
            {
                "input": "Hello, how are you?",
                "content": "",
                "expected_intent": "casual_chat"
            },
            {
                "input": "Please analyze this patent document",
                "content": "A system comprising a processor and memory, wherein the processor executes instructions stored in the memory.",
                "expected_intent": "document_analysis"
            },
            {
                "input": "Create a flowchart of the system",
                "content": "",
                "expected_intent": "mermaid_diagram"
            }
        ]
        
        for i, test in enumerate(test_cases):
            print(f"\n--- Test Case {i+1} ---")
            print(f"Input: {test['input']}")
            
            result = await execute_chat_workflow(
                user_input=test['input'],
                document_content=test['content']
            )
            
            print(f"Intent: {result.get('intent_detected')}")
            print(f"Success: {result.get('success')}")
            print(f"Messages: {len(result.get('messages', []))}")
            
            if result.get('success'):
                for msg in result.get('messages', []):
                    print(f"  - {msg.get('type')}: {msg.get('content', '')[:100]}")
    
    # Run test if API key is available
    if os.getenv("OPENAI_API_KEY"):
        asyncio.run(test_workflow())
    else:
        print("Set OPENAI_API_KEY to run workflow tests")