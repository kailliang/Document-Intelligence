"""
Patent Document Analysis Agents Package

This package contains all specialized agents for patent document analysis:
- Intent detection for routing user requests
- Technical agent for structural and technical analysis
- Legal agent for compliance and legal requirements
- Novelty agent for innovation and uniqueness analysis
- Lead agent for coordination and synthesis

The package also includes the LangGraph workflow builder that orchestrates
all agents in a coherent analysis pipeline.
"""

from .base_agent import BaseAgent, Suggestion, AnalysisContext, AnalysisResult
from .intent_detector import IntentDetector, detect_intent_node
from .technical_agent import TechnicalAgent, technical_analysis_node
from .legal_agent import LegalAgent, legal_analysis_node
from .novelty_agent import NoveltyAgent, novelty_analysis_node
from .lead_agent import LeadAgent, lead_evaluation_node
from .graph_builder import create_chat_workflow, execute_chat_workflow

__all__ = [
    # Base classes
    "BaseAgent",
    "Suggestion", 
    "AnalysisContext",
    "AnalysisResult",
    
    # Specialized agents
    "IntentDetector",
    "TechnicalAgent",
    "LegalAgent", 
    "NoveltyAgent",
    "LeadAgent",
    
    # LangGraph nodes
    "detect_intent_node",
    "technical_analysis_node",
    "legal_analysis_node", 
    "novelty_analysis_node",
    "lead_evaluation_node",
    
    # Workflow
    "create_chat_workflow",
    "execute_chat_workflow"
]