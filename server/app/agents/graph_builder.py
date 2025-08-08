"""
LangGraph Workflow Builder for Patent Document Analysis

This module builds and configures the LangGraph workflow that coordinates
all agents and handles the complete chat and analysis pipeline.
"""

import logging
from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage
from openai import AsyncOpenAI
import os

from .intent_detector import detect_intent_node, should_route_to_casual_chat, should_route_to_document_analysis, should_route_to_mermaid_diagram
from .technical_agent import technical_analysis_node
from .legal_agent import legal_analysis_node
from .novelty_agent import novelty_analysis_node
from .lead_agent import lead_evaluation_node
from ..internal.mermaid_render import generate_mermaid_node
from ..internal.text_utils import html_to_plain_text

logger = logging.getLogger(__name__)


class ChatWorkflowState(Dict[str, Any]):
    """
    State object for the LangGraph workflow.
    
    This maintains all state information as the workflow progresses
    through different nodes and processing stages.
    """
    pass


def create_chat_workflow() -> StateGraph:
    """
    Create and configure the complete LangGraph workflow.
    
    Returns:
        Compiled StateGraph ready for execution
    """
    logger.info("Building LangGraph chat workflow")
    
    # Create the state graph
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
    workflow.add_node("lead_agent", lead_evaluation_node)
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
    
    # All agents feed into lead agent
    workflow.add_edge("technical_agent", "lead_agent")
    workflow.add_edge("legal_agent", "lead_agent")
    workflow.add_edge("novelty_agent", "lead_agent")
    
    # Lead agent feeds into response formatter
    workflow.add_edge("lead_agent", "response_formatter")
    
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
        
        # Update state with processed document
        updated_state = {
            **state,
            "document_content": plain_text,  # Use plain text for analysis
            "document_processed": True,
            "content_length": len(plain_text),
            "estimated_paragraphs": len([p for p in plain_text.split('\n') if p.strip()])
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
                "intent_detected": "casual_chat"
            }
        
        # Generate casual chat response
        response = await openai_client.chat.completions.create(
            model="gpt-4o",
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
            "intent_detected": "casual_chat"
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
            "intent_detected": "casual_chat",
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


async def format_final_response_node(state: ChatWorkflowState) -> ChatWorkflowState:
    """
    Format the final response with all analysis results.
    
    Args:
        state: Current workflow state with all analysis results
        
    Returns:
        Final state with formatted response messages
    """
    try:
        logger.info("Formatting final response")
        
        # Get analysis results
        final_analysis = state.get("final_analysis", {})
        agents_used = state.get("agents_used", [])
        
        if final_analysis.get("error"):
            return {
                **state,
                "messages": [{
                    "type": "text",
                    "content": f"I encountered an issue while analyzing your document: {final_analysis['error']}. Please try again or check your document content.",
                    "timestamp": "2024-01-01T00:00:00Z"
                }],
                "intent_detected": "document_analysis"
            }
        
        suggestions = final_analysis.get("suggestions", [])
        
        if not suggestions:
            return {
                **state,
                "messages": [{
                    "type": "text",
                    "content": "I've analyzed your document and everything looks good! No specific improvements were identified at this time.",
                    "timestamp": "2024-01-01T00:00:00Z"
                }],
                "intent_detected": "document_analysis",
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
            **state,
            "messages": messages,
            "intent_detected": "document_analysis",
            "agents_used": agents_used
        }
        
    except Exception as e:
        logger.error(f"Response formatting failed: {e}")
        return {
            **state,
            "messages": [{
                "type": "text",
                "content": "I encountered an issue while formatting the analysis results. Please try again.",
                "timestamp": "2024-01-01T00:00:00Z"
            }],
            "intent_detected": "document_analysis",
            "error": str(e)
        }


def create_initial_state(user_input: str, document_content: str = "",
                        document_id: Optional[int] = None,
                        version_number: Optional[str] = None,
                        chat_history: Optional[list] = None) -> ChatWorkflowState:
    """
    Create initial state for the workflow.
    
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
    
    initial_state = ChatWorkflowState({
        "user_input": user_input,
        "document_content": document_content,
        "document_id": document_id,
        "version_number": version_number,
        "chat_history": chat_history or [],
        "openai_client": openai_client,
        "messages": [],
        "agents_used": [],
        "errors": []
    })
    
    return initial_state


async def execute_chat_workflow(user_input: str, document_content: str = "",
                               document_id: Optional[int] = None,
                               version_number: Optional[str] = None,
                               chat_history: Optional[list] = None) -> Dict[str, Any]:
    """
    Execute the complete chat workflow.
    
    Args:
        user_input: User's message
        document_content: Document content for analysis
        document_id: Document ID
        version_number: Document version
        chat_history: Previous chat history
        
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
            chat_history=chat_history
        )
        
        # Execute workflow
        result = await workflow.ainvoke(initial_state)
        
        logger.info("Chat workflow execution completed successfully")
        
        return {
            "type": "assistant_response",
            "messages": result.get("messages", []),
            "intent_detected": result.get("intent_detected", "unknown"),
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