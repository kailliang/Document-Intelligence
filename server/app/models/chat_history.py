"""
Chat History Models for Document Version-Specific Conversations

This module defines the database models for storing chat history tied to specific
document versions, enabling conversation persistence across document version switches.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import json
from typing import Dict, Any, Optional

from ..internal.db import Base


class ChatHistory(Base):
    """
    Chat history table for storing messages tied to document versions.
    
    Each message is associated with a specific document and version, allowing
    for separate conversation histories per document version.
    """
    __tablename__ = "chat_history"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("document.id"), nullable=False)
    version_number = Column(String, nullable=False)
    message_type = Column(String, nullable=False)  # 'user', 'assistant', 'suggestion_cards'
    content = Column(Text, nullable=False)
    metadata = Column(JSON, nullable=True)  # Store suggestion card data, user actions, etc.
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship to document
    document = relationship("Document", back_populates="chat_messages")
    
    def __repr__(self):
        return f"<ChatHistory(id={self.id}, doc_id={self.document_id}, version={self.version_number}, type={self.message_type})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert chat message to dictionary format for API responses"""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "version_number": self.version_number,
            "message_type": self.message_type,
            "content": self.content,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }
    
    @classmethod
    def create_user_message(cls, document_id: int, version_number: str, content: str) -> "ChatHistory":
        """Create a user message entry"""
        return cls(
            document_id=document_id,
            version_number=version_number,
            message_type="user",
            content=content,
            metadata={}
        )
    
    @classmethod
    def create_assistant_message(cls, document_id: int, version_number: str, content: str, 
                               agents_used: Optional[list] = None) -> "ChatHistory":
        """Create an assistant message entry"""
        metadata = {}
        if agents_used:
            metadata["agents_used"] = agents_used
            
        return cls(
            document_id=document_id,
            version_number=version_number,
            message_type="assistant",
            content=content,
            metadata=metadata
        )
    
    @classmethod
    def create_suggestion_cards_message(cls, document_id: int, version_number: str, 
                                      suggestion_cards: list, agents_used: list) -> "ChatHistory":
        """Create a suggestion cards message entry"""
        metadata = {
            "suggestion_cards": suggestion_cards,
            "agents_used": agents_used,
            "card_actions": {}  # Track accept/dismiss actions
        }
        
        return cls(
            document_id=document_id,
            version_number=version_number,
            message_type="suggestion_cards",
            content=f"AI Analysis Results ({len(suggestion_cards)} suggestions from {len(agents_used)} agents)",
            metadata=metadata
        )
    
    def mark_card_action(self, card_id: str, action: str) -> None:
        """Mark a suggestion card as accepted or dismissed"""
        if not self.metadata:
            self.metadata = {}
        
        if "card_actions" not in self.metadata:
            self.metadata["card_actions"] = {}
        
        self.metadata["card_actions"][card_id] = action
        
        # Mark the object as modified for SQLAlchemy
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(self, "metadata")
    
    def get_active_suggestion_cards(self) -> list:
        """Get suggestion cards that haven't been accepted or dismissed"""
        if self.message_type != "suggestion_cards" or not self.metadata:
            return []
        
        suggestion_cards = self.metadata.get("suggestion_cards", [])
        card_actions = self.metadata.get("card_actions", {})
        
        # Filter out cards that have been acted upon
        active_cards = []
        for card in suggestion_cards:
            card_id = card.get("id")
            if card_id and card_id not in card_actions:
                active_cards.append(card)
        
        return active_cards


class ChatMessage:
    """
    Data transfer object for chat messages used in API responses.
    
    This class provides a clean interface for working with chat messages
    without exposing database implementation details.
    """
    
    def __init__(self, id: str, message_type: str, content: str, 
                 timestamp: datetime, document_version: str, 
                 metadata: Optional[Dict[str, Any]] = None):
        self.id = id
        self.type = message_type
        self.content = content
        self.timestamp = timestamp
        self.document_version = document_version
        self.metadata = metadata or {}
    
    @property
    def suggestion_cards(self) -> list:
        """Get active suggestion cards from metadata"""
        if self.type == "suggestion_cards" and self.metadata:
            return self.metadata.get("suggestion_cards", [])
        return []
    
    @property
    def agents_used(self) -> list:
        """Get list of agents that contributed to this message"""
        return self.metadata.get("agents_used", [])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = {
            "id": self.id,
            "type": self.type,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "document_version": self.document_version
        }
        
        if self.suggestion_cards:
            data["suggestion_cards"] = self.suggestion_cards
        
        if self.agents_used:
            data["agents_used"] = self.agents_used
        
        return data
    
    @classmethod
    def from_db_record(cls, chat_history: ChatHistory) -> "ChatMessage":
        """Create ChatMessage from database record"""
        return cls(
            id=str(chat_history.id),
            message_type=chat_history.message_type,
            content=chat_history.content,
            timestamp=chat_history.created_at,
            document_version=chat_history.version_number,
            metadata=chat_history.metadata
        )