"""
Intent Detection Node for LangGraph Workflow

This module implements the intent detection capability for the chat system,
classifying user messages into different categories to route them to appropriate handlers.
"""

import logging
from typing import Dict, Any, Literal
from openai import AsyncOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

IntentType = Literal["casual_chat", "document_analysis", "mermaid_diagram"]

INTENT_DETECTION_PROMPT = """
You are an intent classifier for a patent document review system. Your task is to classify user messages into exactly one of these categories:

**Categories:**

1. **casual_chat** - General questions, greetings, or conversation not directly related to document analysis
   Examples:
   - "How are you today?"
   - "What can you help me with?"
   - "Thanks for your help!"
   - "Hello there!"
   - "Can you explain what a patent is?"

2. **document_analysis** - User requesting document review, suggestions, improvements, or analysis
   Examples:
   - "Please review this patent for any issues"
   - "Can you suggest improvements to my claims?"
   - "Find problems in this document"
   - "Analyze this patent for legal compliance"
   - "Check for technical issues"
   - "Review for novelty problems"
   - "Give me suggestions"
   - "Improve this document"

3. **mermaid_diagram** - User requesting diagrams, flowcharts, or visual representations
   Examples:
   - "Create a flowchart showing the invention process"
   - "Generate a diagram of the system architecture"
   - "Draw a flowchart for this process"
   - "Make a visual representation"
   - "Create a diagram"

**Classification Rules:**
- Be precise in classification
- When in doubt between casual_chat and document_analysis, prefer document_analysis if the message mentions:
  - Documents, patents, claims, analysis, review, improvements, suggestions, issues, problems
  - Technical terms, legal terms, or anything related to patent content
- Only classify as mermaid_diagram if the user explicitly requests visual content (diagrams, charts, flowcharts)
- Casual_chat should only be for general conversation that doesn't involve document work

**Response Format:**
Respond with only one word: casual_chat, document_analysis, or mermaid_diagram

User message: "{user_input}"
Classification:"""


class IntentDetector:
    """
    Detects user intent from chat messages using OpenAI API.
    
    This class analyzes user input to determine the appropriate workflow path:
    - casual_chat: General conversation
    - document_analysis: Patent document review and suggestions  
    - mermaid_diagram: Visual diagram generation
    """
    
    def __init__(self, openai_client: AsyncOpenAI):
        self.client = openai_client
        self.prompt_template = INTENT_DETECTION_PROMPT
    
    async def detect_intent(self, user_input: str) -> IntentType:
        """
        Detect the intent of a user message.
        
        Args:
            user_input: The user's message text
            
        Returns:
            IntentType: One of 'casual_chat', 'document_analysis', or 'mermaid_diagram'
        """
        try:
            # Prepare the prompt with user input
            prompt = self.prompt_template.format(user_input=user_input.strip())
            
            logger.info(f"Detecting intent for message: {user_input[:100]}...")
            
            # Call OpenAI API for classification
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                temperature=0.0,  # Use deterministic output for classification
                max_tokens=10,    # We only need a single word response
                messages=[
                    {"role": "system", "content": prompt}
                ]
            )
            
            # Extract and validate the classification
            classification = response.choices[0].message.content.strip().lower()
            
            # Validate classification result
            if classification in ["casual_chat", "document_analysis", "mermaid_diagram"]:
                logger.info(f"Intent detected: {classification}")
                return classification
            else:
                # Default fallback if classification is unclear
                logger.warning(f"Invalid classification '{classification}', defaulting to casual_chat")
                return "casual_chat"
                
        except Exception as e:
            logger.error(f"Error in intent detection: {e}")
            # Default to casual_chat on error to prevent workflow failure
            return "casual_chat"
    
    def classify_keywords(self, user_input: str) -> IntentType:
        """
        Fallback keyword-based classification when API fails.
        
        Args:
            user_input: The user's message text
            
        Returns:
            IntentType: Best guess based on keywords
        """
        user_lower = user_input.lower()
        
        # Document analysis keywords
        analysis_keywords = [
            "analyze", "review", "check", "improve", "suggest", "suggestion", 
            "patent", "document", "claim", "legal", "technical", "novelty",
            "issue", "problem", "error", "fix", "compliance", "structure"
        ]
        
        # Mermaid diagram keywords  
        diagram_keywords = [
            "diagram", "flowchart", "chart", "visual", "draw", "create diagram",
            "mermaid", "flow", "process diagram", "system diagram"
        ]
        
        # Check for diagram intent first (more specific)
        if any(keyword in user_lower for keyword in diagram_keywords):
            return "mermaid_diagram"
        
        # Check for document analysis intent
        if any(keyword in user_lower for keyword in analysis_keywords):
            return "document_analysis"
        
        # Default to casual chat
        return "casual_chat"


async def detect_intent_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node function for intent detection.
    
    Args:
        state: The current workflow state containing user_input
        
    Returns:
        Updated state with detected intent
    """
    try:
        user_input = state.get("user_input", "")
        
        if not user_input:
            logger.warning("No user input provided for intent detection")
            return {**state, "intent": "casual_chat"}
        
        # Get OpenAI client from state or create new one
        openai_client = state.get("openai_client")
        if not openai_client:
            # This should be injected by the workflow, but provide fallback
            from openai import AsyncOpenAI
            import os
            openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Create detector and classify
        detector = IntentDetector(openai_client)
        intent = await detector.detect_intent(user_input)
        
        logger.info(f"Intent detection complete: {intent}")
        
        return {
            **state,
            "intent": intent,
            "intent_confidence": "high"  # Could be enhanced with confidence scoring
        }
        
    except Exception as e:
        logger.error(f"Error in intent detection node: {e}")
        # Fallback to keyword-based classification
        detector = IntentDetector(None)
        intent = detector.classify_keywords(state.get("user_input", ""))
        
        return {
            **state,
            "intent": intent,
            "intent_confidence": "low"
        }


def should_route_to_casual_chat(state: Dict[str, Any]) -> bool:
    """Route condition for casual chat"""
    return state.get("intent") == "casual_chat"


def should_route_to_document_analysis(state: Dict[str, Any]) -> bool:
    """Route condition for document analysis"""
    return state.get("intent") == "document_analysis"


def should_route_to_mermaid_diagram(state: Dict[str, Any]) -> bool:
    """Route condition for mermaid diagram generation"""
    return state.get("intent") == "mermaid_diagram"


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    import os
    from openai import AsyncOpenAI
    
    async def test_intent_detection():
        """Test function for intent detection"""
        client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        detector = IntentDetector(client)
        
        test_messages = [
            "Hello, how are you?",
            "Please analyze this patent document",
            "Can you review my claims for issues?",
            "Create a flowchart of the process",
            "What's the weather like?",
            "Find technical problems in the document",
            "Generate a system diagram"
        ]
        
        for message in test_messages:
            intent = await detector.detect_intent(message)
            print(f"'{message}' -> {intent}")
    
    # Run test if executed directly
    if os.getenv("OPENAI_API_KEY"):
        asyncio.run(test_intent_detection())
    else:
        print("Set OPENAI_API_KEY to run tests")