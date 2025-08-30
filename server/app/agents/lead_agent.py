"""
Lead Agent for Coordinating Multi-Agent Analysis

This agent synthesizes and evaluates suggestions from all specialized agents,
providing comprehensive analysis coordination and final recommendations.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from openai import AsyncOpenAI

from .base_agent import BaseAgent, AnalysisContext, Suggestion, AnalysisResult

logger = logging.getLogger(__name__)


class LeadAgent(BaseAgent):
    """
    Lead coordination agent that synthesizes results from specialized agents.
    
    This agent:
    - Coordinates analysis from Technical, Legal, and Novelty agents
    - Evaluates and prioritizes suggestions from all agents
    - Resolves conflicts between agent recommendations
    - Provides comprehensive final analysis
    - Ensures coherent and actionable output
    """
    
    def __init__(self, openai_client: AsyncOpenAI):
        super().__init__(openai_client, "lead")
    
    @property
    def agent_name(self) -> str:
        return "Lead Coordinator"
    
    @property
    def system_prompt(self) -> str:
        return """
You are the Lead Coordinator for patent document analysis. Your role is to synthesize and evaluate suggestions from specialized agents (Technical, Legal, and Novelty) to provide comprehensive, coherent recommendations.

**Your Responsibilities:**

1. **Suggestion Evaluation**
   - Review suggestions from all specialized agents
   - Assess quality, relevance, and importance of each suggestion
   - Identify overlapping or conflicting recommendations
   - Prioritize suggestions based on impact and importance

2. **Conflict Resolution**
   - Resolve conflicts between different agent recommendations
   - Ensure recommendations are coherent and complementary
   - Merge similar suggestions from different agents

4. **Final Coordination**
   - Check that original text matches and replacements are appropriate

**Evaluation Criteria:**
- **Impact**: How significantly will this improve the patent?
- **Validity**: How accurate and appropriate is the suggestion?
- **Coherence**: How well does this fit with other recommendations?

You will receive analysis results from Technical, Legal, and Novelty agents. Your task is to evaluate, synthesize, and provide final synthesized document text with no explanations.
"""
    
    
    
    async def synthesize_improved_documents(self, improved_documents: List[Dict[str, str]], 
                                          context: AnalysisContext) -> str:
        """
        Synthesize improved documents from all specialized agents into a final version.
        
        Args:
            improved_documents: List of improved documents from agents
            context: Analysis context
            
        Returns:
            Final synthesized improved document
        """
        try:
            logger.info("Starting lead agent document synthesis")
            
            if not improved_documents:
                logger.warning("No improved documents to synthesize")
                return context.document_content
            
            # Create synthesis prompt
            synthesis_prompt = self._create_synthesis_prompt(improved_documents, context)
            
            # Prepare messages for synthesis
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": synthesis_prompt}
            ]
            
            # Call OpenAI for final synthesis
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1,  # Low temperature for consistent synthesis
                max_tokens=5000
            )
            
            final_document = response.choices[0].message.content.strip()
            
            logger.info(f"Lead synthesis completed: {len(final_document)} characters")
            return final_document
            
        except Exception as e:
            logger.error(f"Document synthesis failed: {e}")
            # Return the best available document or original
            if improved_documents:
                return improved_documents[0].get("content", context.document_content)
            return context.document_content
    
    def _create_synthesis_prompt(self, improved_documents: List[Dict[str, str]], 
                               context: AnalysisContext) -> str:
        """
        Create synthesis prompt for combining improved documents.
        """
        prompt_parts = [
            "You are synthesizing improved patent document versions from multiple specialized agents.",
            "Your task is to create the BEST FINAL VERSION by combining the improvements from all agents.",
            "",
            "ORIGINAL DOCUMENT:",
            context.document_content,
            "",
            "IMPROVED VERSIONS:",
        ]
        
        for doc in improved_documents:
            agent = doc.get("agent", "unknown")
            content = doc.get("content", "")
            prompt_parts.extend([
                f"",
                f"=== {agent.upper()} AGENT VERSION ===",
                content,
                ""
            ])
        
        prompt_parts.extend([
            "SYNTHESIS INSTRUCTIONS:",
            "1. Take the BEST improvements from each agent version",
            "2. Ensure technical accuracy (from technical agent)",
            "3. Maintain legal compliance (from legal agent)",
            "4. Emphasize novelty and innovation (from novelty agent)",
            "5. Create a coherent, well-structured final document",
            "6. Each paragraph should be separated by a single newline (\\n)",
            "",
            "Return ONLY the final synthesized document text with no explanations."
        ])
        
        return "\n".join(prompt_parts)
    
    async def _perform_analysis(self, context: AnalysisContext) -> List[Suggestion]:
        """
        Lead agent doesn't use the standard analysis method - it uses synthesize_improved_documents.
        This method should never be called.
        """
        raise NotImplementedError("Lead agent uses synthesize_improved_documents method instead")


async def create_lead_agent(openai_client: AsyncOpenAI) -> LeadAgent:
    """
    Factory function to create a LeadAgent instance.
    
    Args:
        openai_client: OpenAI client for API calls
        
    Returns:
        Configured LeadAgent instance
    """
    agent = LeadAgent(openai_client)
    logger.info("Lead agent created and initialized")
    return agent


# Node function for LangGraph integration
async def lead_evaluation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node function for lead agent document synthesis.
    
    Args:
        state: Current workflow state containing improved documents from agents
        
    Returns:
        Updated state with final synthesized document
    """
    try:
        # Send progress update for lead synthesis
        if state.get("progress_callback"):
            await state["progress_callback"]("lead_synthesis", "lead", "document_analysis")
            
        # Get improved documents from all agents
        improved_documents = state.get("improved_documents", [])
        
        if not improved_documents:
            logger.warning("No improved documents available for synthesis")
            return {
                "final_improved_document": state.get("document_content", ""),
                "agents_used": ["lead"]
            }
        
        # Create analysis context
        context = AnalysisContext(
            document_content=state.get("document_content", ""),
            document_id=state.get("document_id"),
            version_number=state.get("version_number"),
            user_input=state.get("user_input")
        )
        
        # Create and run lead agent
        openai_client = state.get("openai_client")
        agent = await create_lead_agent(openai_client)
        final_document = await agent.synthesize_improved_documents(improved_documents, context)
        
        # Get list of agents that contributed
        contributing_agents = [doc.get("agent", "unknown") for doc in improved_documents]
        agents_used = list(set(contributing_agents)) + ["lead"]
        
        logger.info(f"Lead synthesis completed: {len(final_document)} characters from {len(contributing_agents)} agents")
        
        # Return synthesized document
        return {
            "final_improved_document": final_document,
            "agents_used": agents_used
        }
        
    except Exception as e:
        logger.error(f"Lead synthesis node failed: {e}")
        return {
            "final_improved_document": state.get("document_content", ""),
            "agents_used": ["lead"],
            "error": str(e)
        }