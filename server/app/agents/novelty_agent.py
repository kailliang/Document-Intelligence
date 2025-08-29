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

from .base_agent import BaseAgent, AnalysisContext, Suggestion, create_suggestion_function_schema

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
    
    @property
    def function_tools(self) -> List[Dict[str, Any]]:
        # No function tools needed - agent returns improved text directly
        return []
    
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
        """
        Perform novelty analysis of the patent document.
        
        Args:
            context: Analysis context containing document content
            
        Returns:
            List of novelty enhancement suggestions
        """
        try:
            # Prepare analysis messages
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"""
Please analyze this patent document for novelty and innovation opportunities:

{context.document_content}

Focus on:
1. Identifying unique technical features and innovations
2. Opportunities to better emphasize novel aspects
3. Ways to strengthen differentiation from prior art
4. Improvements to innovation communication and clarity
5. Additional novel features that could be highlighted

Provide specific suggestions for enhancing novelty presentation using the create_suggestion function.
"""}
            ]
            
            # Call OpenAI API with function calling
            response = await self._call_openai_with_functions(messages, temperature=0.15)  # Slightly higher for creativity
            
            # Parse function calls into suggestions
            suggestions = self._parse_function_calls(response)
            
            # Enhance suggestions with novelty-specific improvements
            enhanced_suggestions = []
            for suggestion in suggestions:
                enhanced_suggestion = self._enhance_novelty_suggestion(suggestion, context)
                enhanced_suggestions.append(enhanced_suggestion)
            
            return enhanced_suggestions
            
        except Exception as e:
            logger.error(f"Novelty analysis failed: {e}")
            raise
    
    def _enhance_novelty_suggestion(self, suggestion: Suggestion, 
                                  context: AnalysisContext) -> Suggestion:
        """
        Enhance a novelty suggestion with additional context and validation.
        
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
        
        # Enhance type classification for novelty issues
        suggestion.type = self._classify_novelty_issue_type(suggestion.description)
        
        # Adjust confidence based on novelty factors
        suggestion.confidence = self._calculate_novelty_confidence(
            suggestion, context.document_content
        )
        
        return suggestion
    
    def _classify_novelty_issue_type(self, description: str) -> str:
        """
        Classify the type of novelty issue based on description.
        
        Args:
            description: Issue description
            
        Returns:
            Classified issue type
        """
        description_lower = description.lower()
        
        if any(keyword in description_lower for keyword in ["unique", "novel", "innovative", "distinguish"]):
            return "Innovation Highlighting"
        elif any(keyword in description_lower for keyword in ["advantage", "benefit", "superior", "improvement"]):
            return "Technical Advantages"
        elif any(keyword in description_lower for keyword in ["differentiation", "competitive", "prior art", "conventional"]):
            return "Competitive Differentiation"
        elif any(keyword in description_lower for keyword in ["unexpected", "surprising", "unpredictable", "result"]):
            return "Unexpected Results"
        elif any(keyword in description_lower for keyword in ["combination", "integration", "synthesis", "merge"]):
            return "Novel Combinations"
        elif any(keyword in description_lower for keyword in ["application", "use case", "implementation", "deployment"]):
            return "Innovative Applications"
        elif any(keyword in description_lower for keyword in ["emphasis", "highlight", "stress", "feature"]):
            return "Feature Enhancement"
        else:
            return "Novelty & Innovation"
    
    def _calculate_novelty_confidence(self, suggestion: Suggestion, 
                                    document_content: str) -> float:
        """
        Calculate confidence level for a novelty suggestion.
        
        Args:
            suggestion: The suggestion to evaluate
            document_content: Full document content for context
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        base_confidence = suggestion.confidence
        
        # Higher confidence for clear technical innovations
        if any(keyword in suggestion.description.lower() for keyword in ["unique", "novel", "first", "innovative"]):
            return min(base_confidence + 0.1, 1.0)
        
        # Higher confidence for concrete improvements
        if any(keyword in suggestion.description.lower() for keyword in ["faster", "efficient", "better", "improved"]):
            return min(base_confidence + 0.05, 1.0)
        
        # Lower confidence for subjective assessments
        if any(keyword in suggestion.description.lower() for keyword in ["consider", "might", "potentially", "could"]):
            return max(base_confidence - 0.05, 0.4)
        
        # Higher confidence for unexpected results
        if any(keyword in suggestion.description.lower() for keyword in ["unexpected", "surprising", "unpredictable"]):
            return min(base_confidence + 0.15, 1.0)
        
        return base_confidence
    
    def _identify_innovation_patterns(self, content: str) -> List[Dict[str, Any]]:
        """
        Identify patterns that suggest innovation opportunities.
        
        Args:
            content: Document content
            
        Returns:
            List of innovation patterns
        """
        patterns = []
        
        import re
        
        # Look for technical terms that suggest innovation
        innovation_keywords = [
            r'\b(?:novel|innovative|unique|first|new|advanced|improved)\b',
            r'\b(?:breakthrough|cutting-edge|state-of-the-art|revolutionary)\b',
            r'\b(?:unprecedented|groundbreaking|pioneering|disruptive)\b'
        ]
        
        for pattern in innovation_keywords:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                patterns.append({
                    "type": "innovation_keyword",
                    "text": match.group(0),
                    "context": content[max(0, match.start()-50):match.end()+50],
                    "position": match.start(),
                    "opportunity": "Already using innovation language - could be emphasized more"
                })
        
        # Look for technical advantages
        advantage_patterns = [
            r'(?:faster|quicker|more efficient|improved|better|superior|enhanced)',
            r'(?:reduces|minimizes|eliminates|avoids|prevents)',
            r'(?:increases|maximizes|optimizes|improves|enhances)'
        ]
        
        for pattern in advantage_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                patterns.append({
                    "type": "technical_advantage",
                    "text": match.group(0),
                    "context": content[max(0, match.start()-30):match.end()+30],
                    "position": match.start(),
                    "opportunity": "Technical advantage that could be highlighted as novel feature"
                })
        
        # Look for problem-solution patterns
        problem_solution_pattern = r'(?:problem|issue|difficulty|challenge|limitation).*?(?:solv|address|overcome|mitigate)'
        matches = re.finditer(problem_solution_pattern, content, re.IGNORECASE | re.DOTALL)
        for match in matches:
            if len(match.group(0)) < 200:  # Keep reasonable length
                patterns.append({
                    "type": "problem_solution",
                    "text": match.group(0),
                    "position": match.start(),
                    "opportunity": "Problem-solution relationship that demonstrates innovation"
                })
        
        return patterns
    
    def _assess_innovation_strength(self, content: str) -> Dict[str, Any]:
        """
        Assess the overall innovation strength of the document.
        
        Args:
            content: Document content
            
        Returns:
            Innovation strength assessment
        """
        assessment = {
            "innovation_indicators": 0,
            "technical_advantages": 0,
            "novel_features": 0,
            "differentiation_points": 0,
            "overall_score": 0.0
        }
        
        import re
        
        # Count innovation indicators
        innovation_terms = re.findall(
            r'\b(?:novel|innovative|unique|new|advanced|improved|breakthrough)\b',
            content, re.IGNORECASE
        )
        assessment["innovation_indicators"] = len(innovation_terms)
        
        # Count technical advantages
        advantage_terms = re.findall(
            r'\b(?:advantage|benefit|improvement|superior|better|efficient)\b',
            content, re.IGNORECASE
        )
        assessment["technical_advantages"] = len(advantage_terms)
        
        # Look for feature descriptions
        feature_patterns = re.findall(
            r'(?:feature|characteristic|aspect|element|component)',
            content, re.IGNORECASE
        )
        assessment["novel_features"] = len(feature_patterns)
        
        # Look for differentiation language
        diff_patterns = re.findall(
            r'(?:unlike|different|contrary|alternative|instead)',
            content, re.IGNORECASE
        )
        assessment["differentiation_points"] = len(diff_patterns)
        
        # Calculate overall score (0-1)
        total_indicators = (
            assessment["innovation_indicators"] + 
            assessment["technical_advantages"] + 
            assessment["novel_features"] + 
            assessment["differentiation_points"]
        )
        
        # Normalize based on content length
        content_length = len(content.split())
        if content_length > 0:
            assessment["overall_score"] = min(total_indicators / max(content_length / 100, 1), 1.0)
        
        return assessment


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
        
    except Exception as e:
        logger.error(f"Novelty analysis node failed: {e}")
        return {
            "novelty_suggestions": []
        }