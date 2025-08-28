"""
Chat History Manager

Manages chat history storage and retrieval for document version-specific conversations.
Handles saving messages, loading chat history, and managing suggestion card states.
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

from ..models import ChatHistory, ChatMessage
from ..internal.db import get_db

logger = logging.getLogger(__name__)


class ChatHistoryManager:
    """
    Manages chat history operations for document version-specific conversations.
    
    This class provides methods for:
    - Saving chat messages to database
    - Loading chat history for specific document versions
    - Managing suggestion card states (accept/dismiss)
    - Cleaning up old messages
    """
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    async def save_user_message(self, document_id: int, version_number: str, 
                               content: str) -> ChatHistory:
        """Save a user message to the database"""
        try:
            message = ChatHistory.create_user_message(document_id, version_number, content)
            self.db.add(message)
            self.db.commit()
            self.db.refresh(message)
            
            logger.info(f"Saved user message for doc {document_id} v{version_number}")
            return message
            
        except Exception as e:
            logger.error(f"Error saving user message: {e}")
            self.db.rollback()
            raise
    
    async def save_assistant_message(self, document_id: int, version_number: str, 
                                   content: str, agents_used: Optional[List[str]] = None) -> ChatHistory:
        """Save an assistant message to the database"""
        try:
            message = ChatHistory.create_assistant_message(
                document_id, version_number, content, agents_used
            )
            self.db.add(message)
            self.db.commit()
            self.db.refresh(message)
            
            logger.info(f"Saved assistant message for doc {document_id} v{version_number}")
            return message
            
        except Exception as e:
            logger.error(f"Error saving assistant message: {e}")
            self.db.rollback()
            raise
    
    async def save_suggestion_cards(self, document_id: int, version_number: str, 
                                  suggestion_cards: List[Dict[str, Any]], 
                                  agents_used: List[str]) -> ChatHistory:
        """Save suggestion cards as a message to the database"""
        try:
            message = ChatHistory.create_suggestion_cards_message(
                document_id, version_number, suggestion_cards, agents_used
            )
            self.db.add(message)
            self.db.commit()
            self.db.refresh(message)
            
            logger.info(f"Saved {len(suggestion_cards)} suggestion cards for doc {document_id} v{version_number}")
            return message
            
        except Exception as e:
            logger.error(f"Error saving suggestion cards: {e}")
            self.db.rollback()
            raise
    
    async def load_chat_history(self, document_id: int, version_number: str, 
                               limit: int = 100) -> List[ChatMessage]:
        """
        Load chat history for a specific document version.
        
        Args:
            document_id: The document ID
            version_number: The version number (e.g., "v1.0")
            limit: Maximum number of messages to retrieve (default: 100)
        
        Returns:
            List of ChatMessage objects ordered by creation time
        """
        try:
            # Query chat history for this document version
            chat_records = self.db.query(ChatHistory).filter(
                and_(
                    ChatHistory.document_id == document_id,
                    ChatHistory.version_number == version_number
                )
            ).order_by(ChatHistory.created_at).limit(limit).all()
            
            # Convert to ChatMessage objects
            messages = [ChatMessage.from_db_record(record) for record in chat_records]
            
            logger.info(f"Loaded {len(messages)} chat messages for doc {document_id} v{version_number}")
            return messages
            
        except Exception as e:
            logger.error(f"Error loading chat history: {e}")
            return []
    
    async def mark_suggestion_card_action(self, message_id: int, card_id: str, 
                                        action: str) -> bool:
        """
        Mark a suggestion card as accepted or dismissed.
        
        Args:
            message_id: The chat message ID containing the suggestion cards
            card_id: The ID of the specific suggestion card
            action: 'accepted' or 'dismissed'
        
        Returns:
            True if successful, False otherwise
        """
        try:
            message = self.db.query(ChatHistory).filter(ChatHistory.id == message_id).first()
            
            if not message:
                logger.error(f"Chat message {message_id} not found")
                return False
            
            if message.message_type != "suggestion_cards":
                logger.error(f"Message {message_id} is not a suggestion cards message")
                return False
            
            # Mark the card action
            message.mark_card_action(card_id, action)
            self.db.commit()
            
            logger.info(f"Marked card {card_id} as {action} in message {message_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error marking card action: {e}")
            self.db.rollback()
            return False
    
    async def remove_suggestion_card_message(self, message_id: int) -> bool:
        """
        Remove a suggestion cards message (when all cards are accepted/dismissed).
        
        Args:
            message_id: The chat message ID to remove
        
        Returns:
            True if successful, False otherwise
        """
        try:
            message = self.db.query(ChatHistory).filter(ChatHistory.id == message_id).first()
            
            if not message:
                logger.error(f"Chat message {message_id} not found")
                return False
            
            if message.message_type != "suggestion_cards":
                logger.error(f"Message {message_id} is not a suggestion cards message")
                return False
            
            # Check if all cards have been acted upon
            active_cards = message.get_active_suggestion_cards()
            if active_cards:
                logger.info(f"Message {message_id} still has {len(active_cards)} active cards")
                return False
            
            # Remove the message
            self.db.delete(message)
            self.db.commit()
            
            logger.info(f"Removed suggestion cards message {message_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing suggestion cards message: {e}")
            self.db.rollback()
            return False
    
    async def get_active_suggestion_cards(self, document_id: int, 
                                        version_number: str) -> List[Dict[str, Any]]:
        """
        Get all active (unacted upon) suggestion cards for a document version.
        
        Args:
            document_id: The document ID
            version_number: The version number
        
        Returns:
            List of active suggestion card dictionaries
        """
        try:
            # Get all suggestion cards messages for this document version
            messages = self.db.query(ChatHistory).filter(
                and_(
                    ChatHistory.document_id == document_id,
                    ChatHistory.version_number == version_number,
                    ChatHistory.message_type == "suggestion_cards"
                )
            ).order_by(desc(ChatHistory.created_at)).all()
            
            all_active_cards = []
            for message in messages:
                active_cards = message.get_active_suggestion_cards()
                all_active_cards.extend(active_cards)
            
            logger.info(f"Found {len(all_active_cards)} active suggestion cards for doc {document_id} v{version_number}")
            return all_active_cards
            
        except Exception as e:
            logger.error(f"Error getting active suggestion cards: {e}")
            return []
    
    async def clear_chat_history(self, document_id: int, version_number: str) -> bool:
        """
        Clear all chat history for a specific document version.
        
        Args:
            document_id: The document ID
            version_number: The version number (e.g., "v1.0")
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Delete all chat history records for this document version
            deleted_count = self.db.query(ChatHistory).filter(
                and_(
                    ChatHistory.document_id == document_id,
                    ChatHistory.version_number == version_number
                )
            ).delete(synchronize_session=False)
            
            self.db.commit()
            
            logger.info(f"Cleared {deleted_count} chat messages for document {document_id} version {version_number}")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing chat history: {e}")
            self.db.rollback()
            return False
    
    async def cleanup_old_messages(self, document_id: int, version_number: str, 
                                  keep_count: int = 100) -> int:
        """
        Clean up old chat messages, keeping only the most recent ones.
        
        Args:
            document_id: The document ID
            version_number: The version number
            keep_count: Number of messages to keep (default: 100)
        
        Returns:
            Number of messages deleted
        """
        try:
            # Get all messages for this document version, ordered by creation time (newest first)
            all_messages = self.db.query(ChatHistory).filter(
                and_(
                    ChatHistory.document_id == document_id,
                    ChatHistory.version_number == version_number
                )
            ).order_by(desc(ChatHistory.created_at)).all()
            
            if len(all_messages) <= keep_count:
                return 0
            
            # Delete old messages (keep the newest ones)
            messages_to_delete = all_messages[keep_count:]
            deleted_count = 0
            
            for message in messages_to_delete:
                self.db.delete(message)
                deleted_count += 1
            
            self.db.commit()
            
            logger.info(f"Cleaned up {deleted_count} old messages for doc {document_id} v{version_number}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up old messages: {e}")
            self.db.rollback()
            return 0
    
    async def initialize_document_chat(self, document_id: int, version_number: str) -> ChatHistory:
        """
        Initialize chat history for a new document version with a welcome message.
        
        Args:
            document_id: The document ID
            version_number: The version number
        
        Returns:
            The created welcome message
        """
        try:
            welcome_content = (
                "Hello! I'm your AI assistant. I can help you review and improve your patent document "
                "with technical, legal, and novelty analysis. Just ask me to analyze it or ask any questions you have!"
            )
            
            message = await self.save_assistant_message(
                document_id, version_number, welcome_content, ["system"]
            )
            
            logger.info(f"Initialized chat for doc {document_id} v{version_number}")
            return message
            
        except Exception as e:
            logger.error(f"Error initializing document chat: {e}")
            raise


def get_chat_manager(db: Session = None) -> ChatHistoryManager:
    """
    Get a ChatHistoryManager instance.
    
    Args:
        db: Optional database session. If not provided, will get a new one.
    
    Returns:
        ChatHistoryManager instance
    """
    if db is None:
        db = next(get_db())
    
    return ChatHistoryManager(db)