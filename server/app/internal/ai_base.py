"""
Abstract base class for AI providers (OpenAI, Gemini, etc.)
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, List, Dict, Any

class AIProvider(ABC):
    """Abstract base class for AI providers"""
    
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
    
    @abstractmethod
    async def review_document_with_functions(self, document: str) -> AsyncGenerator[str | None, None]:
        """
        Review patent document using Function Calling for more precise suggestions.
        
        Arguments:
        document -- Patent document to review
        
        Response:
        Yields JSON with suggestions including originalText and replaceTo fields
        """
        pass
    
    @abstractmethod
    async def chat_with_user(self, messages: List[Dict[str, str]]) -> AsyncGenerator[str | None, None]:
        """
        Chat functionality, supports Function Calling
        
        Arguments:
        messages -- Chat history message list
        
        Response:
        Streaming AI response
        """
        pass
    
    @abstractmethod
    async def chat_with_document_context(self, messages: List[Dict[str, str]], document_content: str = "") -> AsyncGenerator[str | None, None]:
        """
        Chat functionality with document context, supports diagram insertion
        
        Arguments:
        messages -- Chat history message list
        document_content -- Current document content (HTML format)
        
        Response:
        Streaming AI response, including possible diagram insertion instructions
        """
        pass