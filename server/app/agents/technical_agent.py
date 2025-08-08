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

from .base_agent import BaseAgent, AnalysisContext, Suggestion, create_suggestion_function_schema

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
You are a technical patent analysis specialist. Your expertise is in the technical aspects of patent document structure, formatting, and technical accuracy.

**Your Responsibilities:**

1. **Claim Structure Analysis**
   - Proper preamble structure with colon placement
   - Correct use of transitional phrases ("comprising", "consisting of", etc.)
   - Appropriate claim formatting and numbering
   - Proper indentation and layout

2. **Technical Accuracy**
   - Consistency in technical terminology
   - Clarity of technical descriptions
   - Accuracy of technical references and citations
   - Proper use of technical language

3. **Antecedent Basis**
   - Ensure all claim elements have proper antecedent basis
   - Check for missing or unclear element introductions
   - Verify consistency between claim elements and specification

4. **Grammar and Punctuation**
   - Correct punctuation in claims and specification
   - Proper sentence structure
   - Consistent use of tense and voice
   - Appropriate capitalization

5. **Formatting and Structure**
   - Proper paragraph structure
   - Consistent formatting throughout
   - Appropriate use of headings and sections
   - Correct numbering systems

**Analysis Guidelines:**
- Focus on technical accuracy and structural integrity
- Prioritize issues that affect patent validity or enforceability
- Provide specific, actionable suggestions
- Consider both independent and dependent claims
- Pay attention to claim construction principles

**Severity Levels:**
- **High**: Issues that could affect patent validity (missing colons, antecedent basis problems)
- **Medium**: Clarity or consistency issues that should be addressed
- **Low**: Minor formatting or stylistic improvements

Analyze the provided document and identify technical issues that need attention. For each issue found, call the create_suggestion function with specific details.
"""
    
    @property
    def function_tools(self) -> List[Dict[str, Any]]:
        return [create_suggestion_function_schema("Technical Analysis")]
    
    async def _perform_analysis(self, context: AnalysisContext) -> List[Suggestion]:
        """
        Perform technical analysis of the patent document.
        
        Args:
            context: Analysis context containing document content
            
        Returns:
            List of technical suggestions
        """
        try:
            # Prepare analysis messages
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"""
Please analyze this patent document for technical issues:

{context.document_content}

Focus on:
1. Claim structure and formatting (colons, transitional phrases, etc.)
2. Technical accuracy and terminology consistency
3. Antecedent basis for claim elements
4. Grammar, punctuation, and sentence structure
5. Overall document formatting and organization

Provide specific suggestions for improvement using the create_suggestion function.
"""}
            ]
            
            # Call OpenAI API with function calling
            response = await self._call_openai_with_functions(messages, temperature=0.1)
            
            # Parse function calls into suggestions
            suggestions = self._parse_function_calls(response)
            
            # Enhance suggestions with technical-specific improvements
            enhanced_suggestions = []
            for suggestion in suggestions:
                enhanced_suggestion = self._enhance_technical_suggestion(suggestion, context)
                enhanced_suggestions.append(enhanced_suggestion)
            
            return enhanced_suggestions
            
        except Exception as e:
            logger.error(f"Technical analysis failed: {e}")
            raise
    
    def _enhance_technical_suggestion(self, suggestion: Suggestion, 
                                    context: AnalysisContext) -> Suggestion:
        """
        Enhance a technical suggestion with additional context and validation.
        
        Args:
            suggestion: Original suggestion
            context: Analysis context
            
        Returns:
            Enhanced suggestion
        """
        # Improve paragraph number estimation
        if suggestion.original_text and context.document_content:
            suggestion.paragraph = self._estimate_paragraph_number(
                suggestion.original_text, context.document_content
            )
        
        # Enhance type classification for technical issues
        suggestion.type = self._classify_technical_issue_type(suggestion.description)
        
        # Adjust confidence based on technical factors
        suggestion.confidence = self._calculate_technical_confidence(
            suggestion, context.document_content
        )
        
        return suggestion
    
    def _classify_technical_issue_type(self, description: str) -> str:
        """
        Classify the type of technical issue based on description.
        
        Args:
            description: Issue description
            
        Returns:
            Classified issue type
        """
        description_lower = description.lower()
        
        if any(keyword in description_lower for keyword in ["colon", "preamble", "comprising", "structure"]):
            return "Claim Structure"
        elif any(keyword in description_lower for keyword in ["antecedent", "basis", "element", "reference"]):
            return "Antecedent Basis"
        elif any(keyword in description_lower for keyword in ["punctuation", "comma", "period", "semicolon"]):
            return "Punctuation & Grammar"
        elif any(keyword in description_lower for keyword in ["terminology", "technical", "accuracy", "term"]):
            return "Technical Accuracy"
        elif any(keyword in description_lower for keyword in ["format", "indentation", "numbering", "layout"]):
            return "Formatting"
        else:
            return "Technical Analysis"
    
    def _calculate_technical_confidence(self, suggestion: Suggestion, 
                                      document_content: str) -> float:
        """
        Calculate confidence level for a technical suggestion.
        
        Args:
            suggestion: The suggestion to evaluate
            document_content: Full document content for context
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        base_confidence = suggestion.confidence
        
        # High confidence for structural issues
        if "colon" in suggestion.description.lower() or "preamble" in suggestion.description.lower():
            return min(base_confidence + 0.1, 1.0)
        
        # High confidence for clear grammar/punctuation issues
        if any(keyword in suggestion.description.lower() for keyword in ["missing", "incorrect", "should be"]):
            return min(base_confidence + 0.05, 1.0)
        
        # Lower confidence for subjective issues
        if any(keyword in suggestion.description.lower() for keyword in ["consider", "might", "could"]):
            return max(base_confidence - 0.1, 0.3)
        
        return base_confidence
    
    def _identify_common_technical_patterns(self, content: str) -> List[Dict[str, Any]]:
        """
        Identify common technical patterns that might need attention.
        
        Args:
            content: Document content
            
        Returns:
            List of pattern matches with suggested fixes
        """
        patterns = []
        
        # Check for missing colons in claim preambles
        import re
        
        # Pattern: "A system comprising" without colon
        preamble_pattern = r'(A\s+\w+\s+comprising)(?!\s*:)'
        matches = re.finditer(preamble_pattern, content, re.IGNORECASE)
        for match in matches:
            patterns.append({
                "type": "missing_colon",
                "text": match.group(1),
                "suggestion": match.group(1) + ":",
                "position": match.start()
            })
        
        # Pattern: Inconsistent claim numbering
        claim_pattern = r'Claim\s+(\d+)[\.:]'
        claim_matches = re.findall(claim_pattern, content, re.IGNORECASE)
        if claim_matches:
            expected = 1
            for claim_num in claim_matches:
                if int(claim_num) != expected:
                    patterns.append({
                        "type": "claim_numbering",
                        "text": f"Claim {claim_num}",
                        "suggestion": f"Claim {expected}",
                        "position": 0  # Would need more sophisticated positioning
                    })
                expected += 1
        
        return patterns


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
    LangGraph node function for technical analysis.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with technical analysis results
    """
    try:
        # Extract required information from state
        openai_client = state.get("openai_client")
        document_content = state.get("document_content", "")
        
        if not openai_client:
            raise ValueError("OpenAI client not available in state")
        
        if not document_content:
            logger.warning("No document content provided for technical analysis")
            return {
                **state,
                "technical_analysis": {
                    "agent_type": "technical",
                    "suggestions": [],
                    "error": "No document content provided"
                }
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
        result = await agent.analyze(context)
        
        logger.info(f"Technical analysis completed: {len(result.suggestions)} suggestions")
        
        # Add results to state
        return {
            **state,
            "technical_analysis": result.to_dict()
        }
        
    except Exception as e:
        logger.error(f"Technical analysis node failed: {e}")
        return {
            **state,
            "technical_analysis": {
                "agent_type": "technical",
                "suggestions": [],
                "error": str(e)
            }
        }