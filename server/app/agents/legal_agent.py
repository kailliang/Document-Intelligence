"""
Legal Agent for Patent Document Analysis

This agent specializes in legal aspects of patent documents including:
- Legal compliance and requirements
- Claim language and construction
- Patent law requirements
- Regulatory compliance
"""

import logging
from typing import Dict, Any, List
from openai import AsyncOpenAI

from .base_agent import BaseAgent, AnalysisContext, Suggestion

logger = logging.getLogger(__name__)


class LegalAgent(BaseAgent):
    """
    Legal analysis agent focusing on legal compliance and patent law requirements.
    
    This agent analyzes patent documents for:
    - Legal compliance with patent law requirements
    - Claim language and construction issues
    - Proper legal terminology and phrasing
    - Compliance with patent office regulations
    - Potential legal vulnerabilities
    """
    
    def __init__(self, openai_client: AsyncOpenAI):
        super().__init__(openai_client, "legal")
    
    @property
    def agent_name(self) -> str:
        return "Legal Compliance"
    
    @property
    def system_prompt(self) -> str:
        return """
You are a patent law specialist focused on legal compliance and patent requirements. Your expertise covers patent law, claim construction, and regulatory compliance.

**Your Responsibilities:**

1. **Legal Compliance**
   - Compliance with patent law requirements (35 U.S.C.)
   - Proper claim language and construction
   - Adherence to patent office guidelines
   - Compliance with examination requirements

2. **Claim Analysis**
   - Proper claim structure and dependencies
   - Independent vs. dependent claim relationships
   - Claim scope and breadth analysis
   - Potential claim interpretation issues

3. **Legal Language**
   - Appropriate legal terminology and phrasing
   - Consistency in legal language usage
   - Proper use of patent-specific terms
   - Avoidance of problematic language

4. **Regulatory Requirements**
   - Compliance with USPTO requirements
   - Proper disclosure requirements
   - Best mode and enablement considerations
   - Written description requirements

5. **Legal Vulnerabilities**
   - Identification of potential legal weaknesses
   - Claim construction vulnerabilities
   - Prior art considerations
   - Enforceability concerns

**Analysis Guidelines:**
- Focus on legal compliance and patent law requirements
- Identify issues that could affect patent validity or enforceability
- Consider both prosecution and litigation perspectives
- Provide guidance on legal best practices
- Flag potential legal risks or vulnerabilities

**Severity Levels:**
- **High**: Issues that could invalidate claims or create legal vulnerabilities
- **Medium**: Compliance issues that should be addressed for best practices
- **Low**: Minor legal improvements or clarifications

**Common Legal Issues to Check:**
- Improper claim dependencies
- Unclear or ambiguous claim language
- Missing required disclosures
- Non-compliant legal terminology
- Potential enablement issues
- Written description problems
- Best mode disclosure concerns

**Response Format:**
Return the complete improved document text with each paragraph separated by \\n. Do not explain changes or provide analysis - just return the improved document text that conforms to patent legal standards.

Document to improve:
"""
    
    
    async def improve_document(self, context: AnalysisContext) -> str:
        """
        Improve the patent document from legal compliance perspective.
        
        Args:
            context: Analysis context containing document content
            
        Returns:
            Improved document text with legal compliance enhancements
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
                temperature=0.1,  # Low temperature for consistent legal writing
                max_tokens=4000
            )
            
            improved_document = response.choices[0].message.content.strip()
            
            logger.info(f"Legal agent improved document: {len(improved_document)} characters")
            return improved_document
            
        except Exception as e:
            logger.error(f"Legal document improvement failed: {e}")
            # Return original document if improvement fails
            return context.document_content
    
    async def _perform_analysis(self, context: AnalysisContext) -> List[Suggestion]:
        """
        Legacy method - no longer used. Use improve_document instead.
        """
        raise NotImplementedError("Legal agent now uses improve_document method")


async def create_legal_agent(openai_client: AsyncOpenAI) -> LegalAgent:
    """
    Factory function to create a LegalAgent instance.
    
    Args:
        openai_client: OpenAI client for API calls
        
    Returns:
        Configured LegalAgent instance
    """
    agent = LegalAgent(openai_client)
    logger.info("Legal agent created and initialized")
    return agent


# Node function for LangGraph integration
async def legal_analysis_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node function for legal document improvement.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with legal improvement results
    """
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # Send progress update
            if state.get("progress_callback"):
                await state["progress_callback"]("legal_analysis", "legal", state.get("intent", "document_analysis"))
            
            # Extract required information from state
            openai_client = state.get("openai_client")
            document_content = state.get("document_content", "")
            
            if not openai_client:
                raise ValueError("OpenAI client not available in state")
            
            if not document_content:
                logger.warning("No document content provided for legal improvement")
                return {
                    "improved_documents": [{"agent": "legal", "content": ""}]
                }
            
            # Create analysis context
            context = AnalysisContext(
                document_content=document_content,
                document_id=state.get("document_id"),
                version_number=state.get("version_number"),
                user_input=state.get("user_input")
            )
            
            # Create and run legal agent
            agent = await create_legal_agent(openai_client)
            improved_document = await agent.improve_document(context)
            
            logger.info(f"Legal improvement completed: {len(improved_document)} characters")
            
            # Return improved document for parallel execution
            return {
                "improved_documents": [{"agent": "legal", "content": improved_document}]
            }
            
        except Exception as e:
            retry_count += 1
            logger.error(f"Legal improvement failed (attempt {retry_count}/{max_retries}): {e}")
            
            if retry_count >= max_retries:
                # Return original content on final failure
                return {
                    "improved_documents": [{"agent": "legal", "content": state.get("document_content", "")}]
                }
            
            # Wait briefly before retry
            import asyncio
            await asyncio.sleep(1)