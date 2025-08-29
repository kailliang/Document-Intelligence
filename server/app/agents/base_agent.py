"""
Base Agent Framework for Patent Document Analysis

This module provides the foundation for all specialized agents in the system,
defining common interfaces, data structures, and utility functions.
"""

import logging
import os
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Literal
from dataclasses import dataclass, asdict
from datetime import datetime
import json
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

# Type definitions
SeverityLevel = Literal["high", "medium", "low"]
AgentType = Literal["technical", "legal", "novelty", "lead"]


@dataclass
class Suggestion:
    """
    Data structure for a single suggestion from an agent.
    
    This represents one improvement suggestion with all necessary metadata
    for display and processing.
    """
    id: str
    type: str  # e.g., "Structure & Punctuation", "Legal Compliance", "Novelty & Innovation"
    severity: SeverityLevel
    paragraph: int
    description: str
    original_text: str
    replace_to: str
    confidence: float  # 0.0 to 1.0
    agent: AgentType
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert suggestion to dictionary for JSON serialization"""
        data = asdict(self)
        if self.created_at:
            data['created_at'] = self.created_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Suggestion":
        """Create Suggestion from dictionary"""
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        return cls(**data)


@dataclass 
class AnalysisContext:
    """
    Context information provided to agents for analysis.
    
    Contains document content and metadata needed for comprehensive analysis.
    """
    document_content: str
    document_id: Optional[int] = None
    version_number: Optional[str] = None
    user_input: Optional[str] = None
    chat_history: Optional[List[Dict[str, Any]]] = None
    previous_suggestions: Optional[List[Suggestion]] = None
    
    def get_content_length(self) -> int:
        """Get length of document content"""
        return len(self.document_content) if self.document_content else 0
    
    def get_paragraph_count(self) -> int:
        """Estimate paragraph count in document"""
        if not self.document_content:
            return 0
        # Simple paragraph counting - could be enhanced
        return len([p for p in self.document_content.split('\n') if p.strip()])


@dataclass
class AnalysisResult:
    """
    Result from an agent's analysis of a document.
    
    Contains suggestions and metadata about the analysis process.
    """
    agent_type: AgentType
    suggestions: List[Suggestion]
    processing_time: float  # seconds
    confidence: float  # overall confidence in analysis
    error_message: Optional[str] = None
    
    def get_suggestion_count(self) -> int:
        """Get total number of suggestions"""
        return len(self.suggestions)
    
    def get_high_priority_count(self) -> int:
        """Get number of high priority suggestions"""
        return len([s for s in self.suggestions if s.severity == "high"])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary"""
        return {
            "agent_type": self.agent_type,
            "suggestions": [s.to_dict() for s in self.suggestions],
            "processing_time": self.processing_time,
            "confidence": self.confidence,
            "error_message": self.error_message,
            "suggestion_count": self.get_suggestion_count(),
            "high_priority_count": self.get_high_priority_count()
        }


class BaseAgent(ABC):
    """
    Abstract base class for all patent analysis agents.
    
    Provides common functionality and defines the interface that all
    specialized agents must implement.
    """
    
    def __init__(self, openai_client: AsyncOpenAI, agent_type: AgentType):
        self.client = openai_client
        self.agent_type = agent_type
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @property
    @abstractmethod
    def agent_name(self) -> str:
        """Return the human-readable name of this agent"""
        pass
    
    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Return the system prompt for this agent"""
        pass
    
    @property
    @abstractmethod
    def function_tools(self) -> List[Dict[str, Any]]:
        """Return the OpenAI function tools for this agent"""
        pass
    
    async def analyze(self, context: AnalysisContext) -> AnalysisResult:
        """
        Analyze document content and return suggestions.
        
        This is the main entry point for agent analysis.
        
        Args:
            context: Analysis context containing document and metadata
            
        Returns:
            AnalysisResult containing suggestions and metadata
        """
        start_time = datetime.utcnow()
        
        try:
            self.logger.info(f"Starting {self.agent_type} analysis")
            
            # Validate input
            if not context.document_content or not context.document_content.strip():
                return AnalysisResult(
                    agent_type=self.agent_type,
                    suggestions=[],
                    processing_time=0.0,
                    confidence=0.0,
                    error_message="No document content provided"
                )
            
            # Perform the analysis
            suggestions = await self._perform_analysis(context)
            
            # Calculate processing time
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()
            
            # Calculate overall confidence (average of suggestion confidences)
            overall_confidence = 0.0
            if suggestions:
                overall_confidence = sum(s.confidence for s in suggestions) / len(suggestions)
            
            self.logger.info(
                f"{self.agent_type} analysis complete: {len(suggestions)} suggestions "
                f"in {processing_time:.2f}s"
            )
            
            return AnalysisResult(
                agent_type=self.agent_type,
                suggestions=suggestions,
                processing_time=processing_time,
                confidence=overall_confidence
            )
            
        except Exception as e:
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()
            
            self.logger.error(f"Error in {self.agent_type} analysis: {e}")
            
            return AnalysisResult(
                agent_type=self.agent_type,
                suggestions=[],
                processing_time=processing_time,
                confidence=0.0,
                error_message=str(e)
            )
    
    @abstractmethod
    async def _perform_analysis(self, context: AnalysisContext) -> List[Suggestion]:
        """
        Perform the actual analysis. Must be implemented by subclasses.
        
        Args:
            context: Analysis context
            
        Returns:
            List of suggestions
        """
        pass
    
    async def _call_openai_with_functions(self, messages: List[Dict[str, Any]], 
                                        temperature: float = 0.1) -> Any:
        """
        Call OpenAI API with function calling.
        
        Args:
            messages: List of message dictionaries
            temperature: Sampling temperature
            
        Returns:
            OpenAI API response
        """
        try:
            response = await self.client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4.1"),
                temperature=temperature,
                messages=messages,
                tools=self.function_tools,
                tool_choice="auto",
                stream=False  # Use non-streaming for easier processing
            )
            
            return response
            
        except Exception as e:
            self.logger.error(f"OpenAI API call failed: {e}")
            raise
    
    def _parse_function_calls(self, response: Any) -> List[Suggestion]:
        """
        Parse function calls from OpenAI response into suggestions.
        
        Args:
            response: OpenAI API response
            
        Returns:
            List of parsed suggestions
        """
        suggestions = []
        
        try:
            message = response.choices[0].message
            
            if not message.tool_calls:
                self.logger.warning("No function calls in OpenAI response")
                return suggestions
            
            for tool_call in message.tool_calls:
                if tool_call.function.name == "create_suggestion":
                    try:
                        args = json.loads(tool_call.function.arguments)
                        suggestion = self._create_suggestion_from_args(args)
                        if suggestion:
                            suggestions.append(suggestion)
                    except json.JSONDecodeError as e:
                        self.logger.error(f"Failed to parse function arguments: {e}")
                    except Exception as e:
                        self.logger.error(f"Failed to create suggestion: {e}")
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Error parsing function calls: {e}")
            return suggestions
    
    def _create_suggestion_from_args(self, args: Dict[str, Any]) -> Optional[Suggestion]:
        """
        Create a Suggestion object from function call arguments.
        
        Args:
            args: Function call arguments dictionary
            
        Returns:
            Suggestion object or None if creation fails
        """
        try:
            # Generate unique ID
            suggestion_id = f"{self.agent_type}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
            
            # Create suggestion with agent attribution
            suggestion = Suggestion(
                id=suggestion_id,
                type=args.get("type", f"{self.agent_name} Analysis"),
                severity=args.get("severity", "medium"),
                paragraph=args.get("paragraph", 1),
                description=args.get("description", ""),
                original_text=args.get("original_text", ""),
                replace_to=args.get("replace_to", ""),
                confidence=args.get("confidence", 0.8),
                agent=self.agent_type
            )
            
            return suggestion
            
        except Exception as e:
            self.logger.error(f"Failed to create suggestion from args: {e}")
            return None
    
    def _estimate_paragraph_number(self, original_text: str, 
                                 document_content: str) -> int:
        """
        Estimate which paragraph contains the original text.
        
        Args:
            original_text: Text to find
            document_content: Full document content
            
        Returns:
            Estimated paragraph number (1-based)
        """
        if not original_text or not document_content:
            return 1
        
        try:
            # Split document into paragraphs
            paragraphs = [p.strip() for p in document_content.split('\n') if p.strip()]
            
            # Find paragraph containing the text
            for i, paragraph in enumerate(paragraphs, 1):
                if original_text.strip() in paragraph:
                    return i
            
            # If not found, return 1
            return 1
            
        except Exception:
            return 1


class AgentRegistry:
    """
    Registry for managing all available agents.
    
    Provides methods to register agents and retrieve them by type.
    """
    
    _agents: Dict[AgentType, BaseAgent] = {}
    
    @classmethod
    def register_agent(cls, agent: BaseAgent) -> None:
        """Register an agent"""
        cls._agents[agent.agent_type] = agent
    
    @classmethod
    def get_agent(cls, agent_type: AgentType) -> Optional[BaseAgent]:
        """Get an agent by type"""
        return cls._agents.get(agent_type)
    
    @classmethod
    def get_all_agents(cls) -> List[BaseAgent]:
        """Get all registered agents"""
        return list(cls._agents.values())
    
    @classmethod
    def get_analysis_agents(cls) -> List[BaseAgent]:
        """Get all analysis agents (excludes lead agent)"""
        return [agent for agent in cls._agents.values() if agent.agent_type != "lead"]
    
    @classmethod
    def clear_registry(cls) -> None:
        """Clear all registered agents (useful for testing)"""
        cls._agents.clear()


# Utility functions
def create_suggestion_function_schema(agent_name: str) -> Dict[str, Any]:
    """
    Create the standard create_suggestion function schema for an agent.
    
    Args:
        agent_name: Name of the agent for descriptions
        
    Returns:
        Function schema dictionary
    """
    return {
        "type": "function",
        "function": {
            "name": "create_suggestion",
            "description": f"Create a suggestion for improving the patent document from the {agent_name} perspective",
            "parameters": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "description": f"Type of issue found (e.g., 'Structure & Punctuation' for technical, 'Legal Compliance' for legal, 'Novelty & Innovation' for novelty)"
                    },
                    "severity": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                        "description": "Severity level of the issue"
                    },
                    "paragraph": {
                        "type": "integer",
                        "description": "Paragraph number where the issue occurs (1-based)"
                    },
                    "description": {
                        "type": "string", 
                        "description": "Detailed description of the issue and why it needs attention"
                    },
                    "original_text": {
                        "type": "string",
                        "description": "Exact text from the document that needs improvement"
                    },
                    "replace_to": {
                        "type": "string",
                        "description": "Suggested replacement text that addresses the issue"
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "description": "Confidence level in this suggestion (0.0 to 1.0)"
                    }
                },
                "required": ["type", "severity", "paragraph", "description", "original_text", "replace_to", "confidence"]
            }
        }
    }