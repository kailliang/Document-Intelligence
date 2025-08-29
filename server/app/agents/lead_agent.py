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
   - Determine which suggestions take precedence when there are contradictions
   - Ensure recommendations are coherent and complementary
   - Merge similar suggestions from different agents

3. **Quality Assurance**
   - Validate that suggestions are accurate and actionable
   - Ensure suggestions are appropriately categorized and prioritized
   - Check that original text matches and replacements are appropriate
   - Verify confidence levels are realistic

4. **Comprehensive Analysis**
   - Ensure all critical aspects are covered (technical, legal, novelty)
   - Identify any gaps in the analysis that need attention
   - Provide holistic view of document strengths and weaknesses
   - Balance different perspectives for optimal recommendations

5. **Final Coordination**
   - Organize suggestions in logical priority order
   - Ensure clear, actionable recommendations
   - Provide context for why each suggestion is important
   - Create coherent narrative across all suggestions

**Evaluation Criteria:**
- **Impact**: How significantly will this improve the patent?
- **Validity**: How accurate and appropriate is the suggestion?
- **Urgency**: How critical is this issue for patent success?
- **Feasibility**: How easily can this recommendation be implemented?
- **Coherence**: How well does this fit with other recommendations?

**Prioritization Guidelines:**
- Legal compliance issues typically have highest priority
- Technical accuracy problems are high priority
- Novelty enhancements are important for patent strength
- Minor formatting issues are lower priority
- Consider cumulative impact of related suggestions

You will receive analysis results from Technical, Legal, and Novelty agents. Your task is to evaluate, synthesize, and provide the final coordinated set of recommendations.
"""
    
    @property
    def function_tools(self) -> List[Dict[str, Any]]:
        # Lead agent doesn't use function calling - it processes existing suggestions
        return []
    
    async def _perform_analysis(self, context: AnalysisContext) -> List[Suggestion]:
        """
        This method is not used by Lead Agent. Use evaluate_agent_results instead.
        """
        raise NotImplementedError("Lead agent uses evaluate_agent_results method")
    
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
    
    async def evaluate_agent_results(self, agent_results: Dict[str, AnalysisResult], 
                                   context: AnalysisContext) -> AnalysisResult:
        """
        Evaluate and synthesize results from all specialized agents.
        
        Args:
            agent_results: Dictionary of results from each agent type
            context: Analysis context
            
        Returns:
            Synthesized AnalysisResult with final recommendations
        """
        start_time = datetime.utcnow()
        
        try:
            logger.info("Starting lead agent evaluation and synthesis")
            
            # Collect all suggestions from agents
            all_suggestions = []
            for agent_type, result in agent_results.items():
                if result and result.suggestions:
                    all_suggestions.extend(result.suggestions)
            
            if not all_suggestions:
                logger.warning("No suggestions to evaluate from any agent")
                return AnalysisResult(
                    agent_type="lead",
                    suggestions=[],
                    processing_time=0.0,
                    confidence=0.0,
                    error_message="No suggestions from specialized agents"
                )
            
            # Synthesize and evaluate suggestions
            final_suggestions = await self._synthesize_suggestions(
                all_suggestions, agent_results, context
            )
            
            # Calculate processing time
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()
            
            # Calculate overall confidence
            overall_confidence = self._calculate_overall_confidence(
                final_suggestions, agent_results
            )
            
            logger.info(f"Lead evaluation complete: {len(final_suggestions)} final suggestions")
            
            return AnalysisResult(
                agent_type="lead",
                suggestions=final_suggestions,
                processing_time=processing_time,
                confidence=overall_confidence
            )
            
        except Exception as e:
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()
            
            logger.error(f"Lead agent evaluation failed: {e}")
            return AnalysisResult(
                agent_type="lead",
                suggestions=[],
                processing_time=processing_time,
                confidence=0.0,
                error_message=str(e)
            )
    
    async def _synthesize_suggestions(self, all_suggestions: List[Suggestion],
                                    agent_results: Dict[str, AnalysisResult],
                                    context: AnalysisContext) -> List[Suggestion]:
        """
        Synthesize suggestions from all agents using AI evaluation.
        
        Args:
            all_suggestions: All suggestions from specialized agents
            agent_results: Original agent results
            context: Analysis context
            
        Returns:
            List of synthesized and prioritized suggestions
        """
        try:
            # First, perform rule-based preprocessing
            deduplicated_suggestions = self._deduplicate_suggestions(all_suggestions)
            resolved_suggestions = self._resolve_conflicts(deduplicated_suggestions)
            
            # Prepare data for AI synthesis
            suggestions_summary = self._create_suggestions_summary(resolved_suggestions)
            agent_summary = self._create_agent_summary(agent_results)
            
            # Use AI to evaluate and refine suggestions
            synthesis_prompt = f"""
Analyze these patent document suggestions from specialized agents and provide final evaluation:

**Document Content (first 500 chars):**
{context.document_content[:500]}...

**Agent Performance Summary:**
{agent_summary}

**All Suggestions Summary:**
{suggestions_summary}

**Your Tasks:**
1. Evaluate the quality and importance of each suggestion
2. Identify the most critical issues that need immediate attention
3. Ensure suggestions are coherent and don't conflict
4. Adjust confidence levels based on suggestion quality
5. Provide final prioritization recommendations

Please respond with your evaluation analysis focusing on which suggestions are most important and why.
"""
            
            # Call OpenAI for synthesis evaluation
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": synthesis_prompt}
            ]
            
            response = await self._call_openai_with_functions(messages, temperature=0.2)
            
            # Process AI feedback and apply to suggestions
            final_suggestions = self._apply_ai_evaluation(
                resolved_suggestions, response, context
            )
            
            # Final prioritization
            prioritized_suggestions = self._prioritize_suggestions(final_suggestions)
            
            return prioritized_suggestions
            
        except Exception as e:
            logger.error(f"Suggestion synthesis failed: {e}")
            # Fallback to rule-based synthesis
            return self._fallback_synthesis(all_suggestions)
    
    def _deduplicate_suggestions(self, suggestions: List[Suggestion]) -> List[Suggestion]:
        """
        Remove duplicate or highly similar suggestions.
        
        Args:
            suggestions: List of all suggestions
            
        Returns:
            Deduplicated suggestions
        """
        deduplicated = []
        seen_texts = set()
        
        for suggestion in suggestions:
            # Create a key for comparison
            comparison_key = (
                suggestion.original_text.lower().strip(),
                suggestion.type.lower(),
                suggestion.paragraph
            )
            
            if comparison_key not in seen_texts:
                seen_texts.add(comparison_key)
                deduplicated.append(suggestion)
            else:
                # If duplicate, keep the one with higher confidence
                for i, existing in enumerate(deduplicated):
                    existing_key = (
                        existing.original_text.lower().strip(),
                        existing.type.lower(),
                        existing.paragraph
                    )
                    if existing_key == comparison_key:
                        if suggestion.confidence > existing.confidence:
                            deduplicated[i] = suggestion
                        break
        
        logger.info(f"Deduplicated {len(suggestions)} → {len(deduplicated)} suggestions")
        return deduplicated
    
    def _resolve_conflicts(self, suggestions: List[Suggestion]) -> List[Suggestion]:
        """
        Resolve conflicting suggestions from different agents.
        
        Args:
            suggestions: Deduplicated suggestions
            
        Returns:
            Conflict-resolved suggestions
        """
        resolved = []
        conflict_groups = self._group_conflicting_suggestions(suggestions)
        
        for group in conflict_groups:
            if len(group) == 1:
                resolved.append(group[0])
            else:
                # Resolve conflict by prioritizing based on agent type and severity
                best_suggestion = self._select_best_from_conflict(group)
                resolved.append(best_suggestion)
        
        return resolved
    
    def _group_conflicting_suggestions(self, suggestions: List[Suggestion]) -> List[List[Suggestion]]:
        """
        Group suggestions that might conflict with each other.
        
        Args:
            suggestions: List of suggestions
            
        Returns:
            Groups of potentially conflicting suggestions
        """
        groups = []
        remaining = suggestions.copy()
        
        while remaining:
            current = remaining.pop(0)
            group = [current]
            
            # Find suggestions that might conflict (same text, similar position)
            to_remove = []
            for other in remaining:
                if self._suggestions_might_conflict(current, other):
                    group.append(other)
                    to_remove.append(other)
            
            # Remove conflicting suggestions from remaining
            for suggestion in to_remove:
                remaining.remove(suggestion)
            
            groups.append(group)
        
        return groups
    
    def _suggestions_might_conflict(self, s1: Suggestion, s2: Suggestion) -> bool:
        """
        Check if two suggestions might conflict.
        
        Args:
            s1, s2: Suggestions to compare
            
        Returns:
            True if suggestions might conflict
        """
        # Same original text
        if s1.original_text == s2.original_text:
            return True
        
        # Overlapping text regions
        if (s1.paragraph == s2.paragraph and 
            len(s1.original_text) > 10 and len(s2.original_text) > 10):
            # Check for text overlap
            if s1.original_text in s2.original_text or s2.original_text in s1.original_text:
                return True
        
        return False
    
    def _select_best_from_conflict(self, conflicting_suggestions: List[Suggestion]) -> Suggestion:
        """
        Select the best suggestion from a group of conflicting suggestions.
        
        Args:
            conflicting_suggestions: Group of conflicting suggestions
            
        Returns:
            Best suggestion from the group
        """
        # Priority order: legal > technical > novelty
        agent_priority = {"legal": 3, "technical": 2, "novelty": 1}
        severity_priority = {"high": 3, "medium": 2, "low": 1}
        
        best_suggestion = conflicting_suggestions[0]
        best_score = 0
        
        for suggestion in conflicting_suggestions:
            # Calculate priority score
            agent_score = agent_priority.get(suggestion.agent, 0)
            severity_score = severity_priority.get(suggestion.severity, 0)
            confidence_score = suggestion.confidence
            
            total_score = (agent_score * 3) + (severity_score * 2) + confidence_score
            
            if total_score > best_score:
                best_score = total_score
                best_suggestion = suggestion
        
        logger.info(f"Resolved conflict: selected {best_suggestion.agent} suggestion over {len(conflicting_suggestions)-1} others")
        return best_suggestion
    
    def _create_suggestions_summary(self, suggestions: List[Suggestion]) -> str:
        """Create a summary of all suggestions for AI evaluation."""
        if not suggestions:
            return "No suggestions available."
        
        summary_parts = []
        for i, suggestion in enumerate(suggestions, 1):
            summary_parts.append(
                f"{i}. [{suggestion.agent.upper()}] {suggestion.type} ({suggestion.severity})\n"
                f"   Text: '{suggestion.original_text[:100]}...'\n"
                f"   Issue: {suggestion.description[:200]}...\n"
                f"   Confidence: {suggestion.confidence:.2f}\n"
            )
        
        return "\n".join(summary_parts)
    
    def _create_agent_summary(self, agent_results: Dict[str, AnalysisResult]) -> str:
        """Create a summary of agent performance."""
        summary_parts = []
        for agent_type, result in agent_results.items():
            if result:
                summary_parts.append(
                    f"{agent_type.upper()}: {len(result.suggestions)} suggestions, "
                    f"confidence: {result.confidence:.2f}, "
                    f"time: {result.processing_time:.1f}s"
                )
            else:
                summary_parts.append(f"{agent_type.upper()}: No results")
        
        return "\n".join(summary_parts)
    
    def _apply_ai_evaluation(self, suggestions: List[Suggestion], ai_response: Any,
                           context: AnalysisContext) -> List[Suggestion]:
        """
        Apply AI evaluation feedback to suggestions.
        
        Args:
            suggestions: Current suggestions
            ai_response: AI evaluation response
            context: Analysis context
            
        Returns:
            AI-refined suggestions
        """
        try:
            # Extract insights from AI response
            ai_content = ai_response.choices[0].message.content
            
            # For now, apply simple confidence adjustments based on AI feedback
            # This could be enhanced with more sophisticated parsing
            
            enhanced_suggestions = []
            for suggestion in suggestions:
                enhanced = suggestion
                
                # Simple keyword-based confidence adjustment
                if suggestion.agent == "legal" and "legal" in ai_content.lower():
                    enhanced.confidence = min(enhanced.confidence + 0.05, 1.0)
                elif suggestion.severity == "high" and "critical" in ai_content.lower():
                    enhanced.confidence = min(enhanced.confidence + 0.1, 1.0)
                
                enhanced_suggestions.append(enhanced)
            
            return enhanced_suggestions
            
        except Exception as e:
            logger.error(f"Failed to apply AI evaluation: {e}")
            return suggestions
    
    def _prioritize_suggestions(self, suggestions: List[Suggestion]) -> List[Suggestion]:
        """
        Final prioritization of suggestions.
        
        Args:
            suggestions: Suggestions to prioritize
            
        Returns:
            Prioritized suggestions
        """
        def priority_score(suggestion: Suggestion) -> tuple:
            # Return tuple for sorting: (severity_rank, agent_priority, confidence, type)
            severity_rank = {"high": 3, "medium": 2, "low": 1}.get(suggestion.severity, 1)
            agent_priority = {"legal": 3, "technical": 2, "novelty": 1}.get(suggestion.agent, 1)
            
            return (severity_rank, agent_priority, suggestion.confidence, suggestion.type)
        
        # Sort by priority (descending)
        prioritized = sorted(suggestions, key=priority_score, reverse=True)
        
        logger.info(f"Prioritized {len(prioritized)} suggestions")
        return prioritized
    
    def _calculate_overall_confidence(self, suggestions: List[Suggestion],
                                    agent_results: Dict[str, AnalysisResult]) -> float:
        """
        Calculate overall confidence in the analysis.
        
        Args:
            suggestions: Final suggestions
            agent_results: Original agent results
            
        Returns:
            Overall confidence score
        """
        if not suggestions:
            return 0.0
        
        # Average confidence of final suggestions
        suggestion_confidence = sum(s.confidence for s in suggestions) / len(suggestions)
        
        # Average confidence of contributing agents
        agent_confidences = [r.confidence for r in agent_results.values() if r and r.confidence > 0]
        agent_confidence = sum(agent_confidences) / len(agent_confidences) if agent_confidences else 0.0
        
        # Weighted combination
        overall_confidence = (suggestion_confidence * 0.7) + (agent_confidence * 0.3)
        
        return min(overall_confidence, 1.0)
    
    def _fallback_synthesis(self, all_suggestions: List[Suggestion]) -> List[Suggestion]:
        """
        Fallback rule-based synthesis when AI synthesis fails.
        
        Args:
            all_suggestions: All suggestions from agents
            
        Returns:
            Rule-based synthesized suggestions
        """
        logger.warning("Using fallback rule-based synthesis")
        
        # Simple deduplication and prioritization
        deduplicated = self._deduplicate_suggestions(all_suggestions)
        prioritized = self._prioritize_suggestions(deduplicated)
        
        return prioritized


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