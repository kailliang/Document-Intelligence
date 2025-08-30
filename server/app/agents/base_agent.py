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
        self.openai_client = openai_client  # For backward compatibility
        self.agent_type = agent_type
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @property
    def model(self) -> str:
        """Return the OpenAI model to use"""
        return os.getenv("OPENAI_MODEL", "gpt-4.1")
    
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


