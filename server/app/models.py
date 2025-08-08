from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.internal.db import Base


class Document(Base):
    """
    Document main table - stores basic document information and metadata
    
    Why separate Document and DocumentVersion?
    - Document: stores basic document information (title, current version, etc.)
    - DocumentVersion: stores specific content for each version
    This design makes version management clearer and facilitates future feature extensions
    """
    __tablename__ = "document"
    
    # Primary key ID
    id = Column(Integer, primary_key=True, index=True)
    
    # Document title - user-friendly document name
    title = Column(String, nullable=False, default="Untitled Document")
    
    # Current active version ID - points to the version user is currently viewing/editing
    current_version_id = Column(Integer, ForeignKey("document_version.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationship definition - SQLAlchemy ORM functionality
    # back_populates creates bidirectional relationship, allows access to versions from Document and document from Version
    # foreign_keys explicitly specifies which foreign key to use for this relationship, avoiding ambiguity
    versions = relationship(
        "DocumentVersion", 
        back_populates="document", 
        cascade="all, delete-orphan",
        foreign_keys="DocumentVersion.document_id"  # Explicitly specify foreign key
    )
    
    # Current version relationship - separately defined for quick access to current version
    current_version = relationship(
        "DocumentVersion", 
        foreign_keys=[current_version_id], 
        post_update=True
    )
    
    # Chat messages relationship - for accessing chat history
    chat_messages = relationship(
        "ChatHistory",
        back_populates="document",
        cascade="all, delete-orphan"
    )


class DocumentVersion(Base):
    """
    Document version table - stores specific content and version information for each version
    
    Why need version_number?
    - Version number shown to users (v1.0, v2.0, etc.)
    - More friendly and meaningful than database ID
    
    Why need is_active?
    - Mark which version is the currently active version
    - Allow users to switch between different versions
    """
    __tablename__ = "document_version"
    
    # Primary key ID
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key - associate to which document
    document_id = Column(Integer, ForeignKey("document.id"), nullable=False, index=True)
    
    # Version number - increment from 1 (v1.0, v2.0...)
    version_number = Column(Integer, nullable=False)
    
    # Version content - actual document content for this version
    content = Column(String, nullable=False, default="")
    
    # Whether this is the current active version
    is_active = Column(Boolean, default=False, nullable=False)
    
    # Creation time - record when this version was created
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship definition - reverse relationship to Document
    document = relationship("Document", back_populates="versions", foreign_keys=[document_id])


# ChatHistory model for document version-specific conversations
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
    content = Column(String, nullable=False)
    chat_metadata = Column(String, nullable=True)  # Store JSON data as text
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship to document
    document = relationship("Document", back_populates="chat_messages")
    
    def __repr__(self):
        return f"<ChatHistory(id={self.id}, doc_id={self.document_id}, version={self.version_number}, type={self.message_type})>"
    
    def to_dict(self):
        """Convert chat message to dictionary format for API responses"""
        import json
        metadata_dict = {}
        if self.chat_metadata:
            try:
                metadata_dict = json.loads(self.chat_metadata)
            except json.JSONDecodeError:
                metadata_dict = {}
                
        return {
            "id": self.id,
            "document_id": self.document_id,
            "version_number": self.version_number,
            "message_type": self.message_type,
            "content": self.content,
            "metadata": metadata_dict,
            "created_at": self.created_at.isoformat(),
        }
    
    @classmethod
    def create_user_message(cls, document_id: int, version_number: str, content: str):
        """Create a user message entry"""
        return cls(
            document_id=document_id,
            version_number=version_number,
            message_type="user",
            content=content,
            chat_metadata="{}"
        )
    
    @classmethod
    def create_assistant_message(cls, document_id: int, version_number: str, content: str, 
                               agents_used=None):
        """Create an assistant message entry"""
        import json
        metadata = {}
        if agents_used:
            metadata["agents_used"] = agents_used
            
        return cls(
            document_id=document_id,
            version_number=version_number,
            message_type="assistant",
            content=content,
            chat_metadata=json.dumps(metadata)
        )
    
    @classmethod
    def create_suggestion_cards_message(cls, document_id: int, version_number: str, 
                                      suggestion_cards, agents_used):
        """Create a suggestion cards message entry"""
        import json
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
            chat_metadata=json.dumps(metadata)
        )
    
    def mark_card_action(self, card_id: str, action: str):
        """Mark a suggestion card as accepted or dismissed"""
        import json
        metadata_dict = {}
        if self.chat_metadata:
            try:
                metadata_dict = json.loads(self.chat_metadata)
            except json.JSONDecodeError:
                metadata_dict = {}
        
        if "card_actions" not in metadata_dict:
            metadata_dict["card_actions"] = {}
        
        metadata_dict["card_actions"][card_id] = action
        self.chat_metadata = json.dumps(metadata_dict)
    
    def get_active_suggestion_cards(self):
        """Get suggestion cards that haven't been accepted or dismissed"""
        import json
        if self.message_type != "suggestion_cards" or not self.chat_metadata:
            return []
        
        try:
            metadata_dict = json.loads(self.chat_metadata)
        except json.JSONDecodeError:
            return []
        
        suggestion_cards = metadata_dict.get("suggestion_cards", [])
        card_actions = metadata_dict.get("card_actions", {})
        
        # Filter out cards that have been acted upon
        active_cards = []
        for card in suggestion_cards:
            card_id = card.get("id")
            if card_id and card_id not in card_actions:
                active_cards.append(card)
        
        return active_cards


# ChatMessage data transfer object
class ChatMessage:
    """
    Data transfer object for chat messages used in API responses.
    """
    
    def __init__(self, id: str, message_type: str, content: str, 
                 timestamp: datetime, document_version: str, 
                 metadata=None):
        self.id = id
        self.type = message_type
        self.content = content
        self.timestamp = timestamp
        self.document_version = document_version
        self.metadata = metadata or {}
    
    @property
    def suggestion_cards(self):
        """Get active suggestion cards from metadata"""
        if self.type == "suggestion_cards" and self.metadata:
            return self.metadata.get("suggestion_cards", [])
        return []
    
    @property
    def agents_used(self):
        """Get list of agents that contributed to this message"""
        return self.metadata.get("agents_used", [])
    
    def to_dict(self):
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
    def from_db_record(cls, chat_history):
        """Create ChatMessage from database record"""
        return cls(
            id=str(chat_history.id),
            message_type=chat_history.message_type,
            content=chat_history.content,
            timestamp=chat_history.created_at,
            document_version=chat_history.version_number,
            metadata=chat_history.to_dict().get("metadata", {})
        )


# Include your models here, and they will automatically be created as tables in the database on start-up
