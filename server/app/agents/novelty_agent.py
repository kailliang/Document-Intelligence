"""
Novelty Agent for Patent Document Analysis

This agent specializes in novelty and innovation aspects of patent documents including:
- Identifying unique technical features
- Analyzing innovation and differentiation opportunities
- Assessing competitive landscape considerations
- Highlighting patentable subject matter
"""

import logging
from typing import Dict, Any, List
from openai import AsyncOpenAI

from .base_agent import BaseAgent, AnalysisContext, Suggestion

logger = logging.getLogger(__name__)


class NoveltyAgent(BaseAgent):
    """
    Novelty analysis agent focusing on innovation and uniqueness aspects.
    
    This agent analyzes patent documents for:
    - Unique technical features and innovations
    - Differentiation from prior art
    - Opportunities to strengthen novelty
    - Patentable subject matter identification
    - Innovation highlighting and emphasis
    """
    
    def __init__(self, openai_client: AsyncOpenAI):
        super().__init__(openai_client, "novelty")
    
    @property
    def agent_name(self) -> str:
        return "Novelty & Innovation"
    
    @property
    def system_prompt(self) -> str:
        return """
You are a patent novelty and innovation specialist. Your expertise is in identifying, analyzing, and strengthening the novel and innovative aspects of patent documents.

**Your Responsibilities:**

1. **Novelty Identification**
   - Identify unique technical features that distinguish the invention
   - Highlight innovative combinations of known elements
   - Recognize unexpected results or advantages
   - Point out novel applications of existing technology

2. **Innovation Enhancement**
   - Suggest ways to emphasize innovative aspects
   - Recommend improvements to strengthen novelty
   - Identify opportunities to broaden innovative scope
   - Suggest additional novel features that could be included

3. **Differentiation Analysis**
   - Analyze how the invention differs from conventional approaches
   - Identify unique technical advantages and benefits
   - Suggest ways to better distinguish from prior art
   - Recommend emphasis of competitive advantages

4. **Patentable Subject Matter**
   - Identify potentially patentable innovations
   - Assess the strength of novel features
   - Recommend focus areas for patent protection
   - Suggest improvements to patentability

5. **Innovation Communication**
   - Improve clarity in describing innovative aspects
   - Enhance technical explanations of novel features
   - Suggest better articulation of inventive concepts
   - Recommend emphasis of technological advances

**Analysis Guidelines:**
- Focus on what makes this invention unique and innovative
- Look for opportunities to strengthen and highlight novelty
- Consider both obvious and non-obvious innovative aspects
- Think about competitive landscape and differentiation
- Identify areas where innovation could be better communicated

**Severity Levels:**
- **High**: Critical innovations that should be emphasized for patent strength
- **Medium**: Important novel features that could be better highlighted
- **Low**: Minor improvements or clarifications to innovation description

**Innovation Focus Areas:**
- Technical uniqueness and distinguishing features
- Novel processes, methods, or approaches
- Unexpected results or superior performance
- Innovative applications or use cases
- Creative solutions to technical problems
- Improvements over existing technology

**Common Novelty Enhancement Opportunities:**
- Emphasizing unexpected advantages
- Highlighting unique technical combinations
- Better articulating innovative aspects
- Strengthening claims with novel features
- Improving description of technical advances
- Adding detail to innovative elements

**Response Format:**
Return the complete improved document text with each paragraph separated by \\n. Do not explain changes or provide analysis - just return the improved document text that emphasizes novelty and innovation.

Document to improve:
"""
    
    
    async def improve_document(self, context: AnalysisContext) -> str:
        """
        Improve the patent document from novelty and innovation perspective.
        
        Args:
            context: Analysis context containing document content
            
        Returns:
            Improved document text with enhanced novelty presentation
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
                temperature=0.1,  # Low temperature for consistent novelty writing
                max_tokens=4000
            )
            
            improved_document = response.choices[0].message.content.strip()
            
            logger.info(f"Novelty agent improved document: {len(improved_document)} characters")
            return improved_document
            
        except Exception as e:
            logger.error(f"Novelty document improvement failed: {e}")
            # Return original document if improvement fails
            return context.document_content
    
    async def _perform_analysis(self, context: AnalysisContext) -> List[Suggestion]:
        """
        Legacy method - no longer used. Use improve_document instead.
        """
        raise NotImplementedError("Novelty agent now uses improve_document method")


async def create_novelty_agent(openai_client: AsyncOpenAI) -> NoveltyAgent:
    """
    Factory function to create a NoveltyAgent instance.
    
    Args:
        openai_client: OpenAI client for API calls
        
    Returns:
        Configured NoveltyAgent instance
    """
    agent = NoveltyAgent(openai_client)
    logger.info("Novelty agent created and initialized")
    return agent


# Node function for LangGraph integration
async def novelty_analysis_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node function for novelty document improvement.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with novelty improvement results
    """
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # Send progress update
            if state.get("progress_callback"):
                await state["progress_callback"]("novelty_analysis", "novelty", state.get("intent", "document_analysis"))
            
            # Extract required information from state
            openai_client = state.get("openai_client")
            document_content = state.get("document_content", "")
            
            if not openai_client:
                raise ValueError("OpenAI client not available in state")
            
            if not document_content:
                logger.warning("No document content provided for novelty improvement")
                return {
                    "improved_documents": [{"agent": "novelty", "content": ""}]
                }
            
            # Create analysis context
            context = AnalysisContext(
                document_content=document_content,
                document_id=state.get("document_id"),
                version_number=state.get("version_number"),
                user_input=state.get("user_input")
            )
            
            # Create and run novelty agent
            agent = await create_novelty_agent(openai_client)
            improved_document = await agent.improve_document(context)
            
            logger.info(f"Novelty improvement completed: {len(improved_document)} characters")
            
            # Return improved document for parallel execution
            return {
                "improved_documents": [{"agent": "novelty", "content": improved_document}]
            }
            
        except Exception as e:
            retry_count += 1
            logger.error(f"Novelty improvement failed (attempt {retry_count}/{max_retries}): {e}")
            
            if retry_count >= max_retries:
                # Return original content on final failure
                return {
                    "improved_documents": [{"agent": "novelty", "content": state.get("document_content", "")}]
                }
            
            # Wait briefly before retry
            import asyncio
            await asyncio.sleep(1)