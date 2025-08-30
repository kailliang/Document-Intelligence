"""
Technical Agent for Patent Document Analysis

This agent specializes in technical aspects of patent documents including:
- Structure and formatting
- Technical accuracy and clarity
- Claim construction and dependencies
- Technical terminology consistency
"""

import logging
from typing import Dict, Any, List
from openai import AsyncOpenAI

from .base_agent import BaseAgent, AnalysisContext, Suggestion

logger = logging.getLogger(__name__)


class TechnicalAgent(BaseAgent):
    """
    Technical analysis agent focusing on structural and technical aspects.
    
    This agent analyzes patent documents for:
    - Proper claim structure and formatting
    - Technical terminology consistency
    - Antecedent basis and claim dependencies
    - Punctuation and grammatical correctness
    - Technical accuracy and clarity
    """
    
    def __init__(self, openai_client: AsyncOpenAI):
        super().__init__(openai_client, "technical")
    
    @property
    def agent_name(self) -> str:
        return "Technical Analysis"
    
    @property
    def system_prompt(self) -> str:
        return """
You are a technical patent writing specialist. Your role is to IMPROVE patent document claims to ensure they meet patent writing standards and regulations.

**Your Task:**
Rewrite and improve the provided patent document with focus on:

1. **Claim Structure Improvement**
   - Ensure proper preamble structure with correct colon placement
   - Use appropriate transitional phrases ("comprising", "consisting of", etc.)
   - Apply proper claim formatting and numbering
   - Fix indentation and layout issues

2. **Technical Writing Enhancement**
   - Improve consistency in technical terminology
   - Enhance clarity of technical descriptions
   - Ensure accurate technical references
   - Use precise technical language

3. **Antecedent Basis Correction**
   - Ensure all claim elements have proper antecedent basis
   - Add missing element introductions
   - Fix consistency between claim elements and specification

4. **Grammar and Punctuation Fixes**
   - Correct punctuation in claims and specification
   - Improve sentence structure
   - Ensure consistent tense and voice
   - Fix capitalization issues

5. **Structure and Format Enhancement**
   - Improve paragraph structure
   - Ensure consistent formatting throughout
   - Fix heading and section structure
   - Correct numbering systems

**Writing Standards:**
- Claims must be clearly written and technically accurate
- Each paragraph should be separated by a single newline (\\n)
- Maintain original document structure while improving content
- Follow patent claim construction principles
- Ensure technical terminology is precise and consistent

**Response Format:**
Return the complete improved document text with each paragraph separated by \\n. Do not explain changes or provide analysis - just return the improved document text that conforms to patent writing standards.

Document to improve:
"""
    
    @property
    def function_tools(self) -> List[Dict[str, Any]]:
        # No function tools needed - agent returns improved text directly
        return []
    
    async def improve_document(self, context: AnalysisContext) -> str:
        """
        Perform technical analysis of the patent document.
        
        Args:
            context: Analysis context containing document content
            
        Returns:
            Improved document text with technical enhancements
        """
        try:
            # Prepare improvement messages
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": context.document_content}
            ]
            
            # Call OpenAI API for document improvement
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1,  # Low temperature for consistent technical writing
                max_tokens=4000
            )
            
            improved_document = response.choices[0].message.content.strip()
            
            logger.info(f"Technical agent improved document: {len(improved_document)} characters")
            return improved_document
            
        except Exception as e:
            logger.error(f"Technical document improvement failed: {e}")
            # Return original document if improvement fails
            return context.document_content
    
    async def _perform_analysis(self, context: AnalysisContext) -> List[Suggestion]:
        """
        Legacy method - no longer used. Use improve_document instead.
        """
        raise NotImplementedError("Technical agent now uses improve_document method")


async def create_technical_agent(openai_client: AsyncOpenAI) -> TechnicalAgent:
    """
    Factory function to create a TechnicalAgent instance.
    
    Args:
        openai_client: OpenAI client for API calls
        
    Returns:
        Configured TechnicalAgent instance
    """
    agent = TechnicalAgent(openai_client)
    logger.info("Technical agent created and initialized")
    return agent


# Node function for LangGraph integration
async def technical_analysis_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node function for technical document improvement.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with technical improvement results
    """
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # Send progress update
            if state.get("progress_callback"):
                await state["progress_callback"]("technical_analysis", "technical", state.get("intent", "document_analysis"))
            
            # Extract required information from state
            openai_client = state.get("openai_client")
            document_content = state.get("document_content", "")
            
            if not openai_client:
                raise ValueError("OpenAI client not available in state")
            
            if not document_content:
                logger.warning("No document content provided for technical improvement")
                return {
                    "improved_documents": [{"agent": "technical", "content": ""}]
                }
            
            # Create analysis context
            context = AnalysisContext(
                document_content=document_content,
                document_id=state.get("document_id"),
                version_number=state.get("version_number"),
                user_input=state.get("user_input")
            )
            
            # Create and run technical agent
            agent = await create_technical_agent(openai_client)
            improved_document = await agent.improve_document(context)
            
            logger.info(f"Technical improvement completed: {len(improved_document)} characters")
            
            # Return improved document for parallel execution
            return {
                "improved_documents": [{"agent": "technical", "content": improved_document}]
            }
            
        except Exception as e:
            retry_count += 1
            logger.error(f"Technical improvement failed (attempt {retry_count}/{max_retries}): {e}")
            
            if retry_count >= max_retries:
                # Return original content on final failure
                return {
                    "improved_documents": [{"agent": "technical", "content": state.get("document_content", "")}]
                }
            
            # Wait briefly before retry
            import asyncio
            await asyncio.sleep(1)