"""
Document Chunking Manager for Suggestion Algorithm

This module handles splitting patent documents into paragraph chunks
and managing chunk operations for the new suggestion generation system.
"""

import logging
import re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    """
    Represents a single chunk of a document (typically a paragraph).
    
    Attributes:
        chunk_id: Unique identifier for this chunk
        text: The actual text content of the chunk
        position: Zero-based position in the document
        start_char: Character position where chunk starts in full document
        end_char: Character position where chunk ends in full document
    """
    chunk_id: str
    text: str
    position: int
    start_char: int
    end_char: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert chunk to dictionary representation."""
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "position": self.position,
            "start_char": self.start_char,
            "end_char": self.end_char
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentChunk":
        """Create DocumentChunk from dictionary."""
        return cls(
            chunk_id=data["chunk_id"],
            text=data["text"],
            position=data["position"],
            start_char=data["start_char"],
            end_char=data["end_char"]
        )


class ChunkManager:
    """
    Manages document chunking operations for the suggestion system.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def split_document_into_chunks(self, document_text: str) -> List[DocumentChunk]:
        """
        Split document into paragraph chunks.
        
        Args:
            document_text: Full document text (plain text)
            
        Returns:
            List of DocumentChunk objects, one per paragraph
        """
        self.logger.info("Splitting document into paragraph chunks")
        
        if not document_text or not document_text.strip():
            self.logger.warning("Empty document provided for chunking")
            return []
        
        # Split by double newlines first (paragraph breaks)
        paragraphs = re.split(r'\n\s*\n', document_text.strip())
        
        # Filter out empty paragraphs and clean up
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        chunks = []
        current_char_pos = 0
        
        for i, paragraph in enumerate(paragraphs):
            # Find the actual start position in the original text
            start_pos = document_text.find(paragraph, current_char_pos)
            if start_pos == -1:
                # Fallback: use current position
                start_pos = current_char_pos
            
            end_pos = start_pos + len(paragraph)
            
            chunk = DocumentChunk(
                chunk_id=f"chunk_{i:03d}_{uuid4().hex[:8]}",
                text=paragraph,
                position=i,
                start_char=start_pos,
                end_char=end_pos
            )
            
            chunks.append(chunk)
            current_char_pos = end_pos
        
        self.logger.info(f"Created {len(chunks)} chunks from document")
        return chunks
    
    def reconstruct_document_from_chunks(self, chunks: List[DocumentChunk]) -> str:
        """
        Reconstruct full document from chunks.
        
        Args:
            chunks: List of DocumentChunk objects
            
        Returns:
            Reconstructed document text with paragraph separators
        """
        if not chunks:
            return ""
        
        # Sort chunks by position to ensure correct order
        sorted_chunks = sorted(chunks, key=lambda c: c.position)
        
        # Join with double newlines (paragraph separators)
        document_text = "\n\n".join(chunk.text for chunk in sorted_chunks)
        
        self.logger.info(f"Reconstructed document from {len(chunks)} chunks")
        return document_text
    
    def create_chunk_mapping(self, original_chunks: List[DocumentChunk], 
                           suggested_chunks: List[DocumentChunk]) -> Dict[str, List[str]]:
        """
        Create basic mapping between suggested and original chunks.
        This is a simple implementation - the mapping_agent will do the intelligent mapping.
        
        Args:
            original_chunks: Original document chunks
            suggested_chunks: Suggested document chunks
            
        Returns:
            Dictionary mapping suggested chunk IDs to list of original chunk IDs
        """
        self.logger.info("Creating basic chunk mapping")
        
        # Simple position-based mapping for now
        # The mapping agent will create the intelligent mapping
        mapping = {}
        
        for suggested in suggested_chunks:
            # Map to corresponding original chunk by position
            if suggested.position < len(original_chunks):
                original_id = original_chunks[suggested.position].chunk_id
                mapping[suggested.chunk_id] = [original_id]
            else:
                # If more suggested chunks than original, map to last original
                if original_chunks:
                    mapping[suggested.chunk_id] = [original_chunks[-1].chunk_id]
        
        self.logger.info(f"Created basic mapping for {len(mapping)} suggested chunks")
        return mapping
    
    def get_chunk_by_id(self, chunks: List[DocumentChunk], chunk_id: str) -> Optional[DocumentChunk]:
        """
        Get a specific chunk by ID.
        
        Args:
            chunks: List of chunks to search
            chunk_id: ID of chunk to find
            
        Returns:
            DocumentChunk if found, None otherwise
        """
        for chunk in chunks:
            if chunk.chunk_id == chunk_id:
                return chunk
        return None
    
    def validate_chunks(self, chunks: List[DocumentChunk]) -> bool:
        """
        Validate chunk integrity.
        
        Args:
            chunks: List of chunks to validate
            
        Returns:
            True if chunks are valid, False otherwise
        """
        if not chunks:
            return True
        
        # Check for duplicate IDs
        chunk_ids = [c.chunk_id for c in chunks]
        if len(chunk_ids) != len(set(chunk_ids)):
            self.logger.error("Duplicate chunk IDs found")
            return False
        
        # Check position sequence
        positions = [c.position for c in chunks]
        expected_positions = list(range(len(chunks)))
        if sorted(positions) != expected_positions:
            self.logger.error("Invalid chunk positions")
            return False
        
        # Check for empty chunks
        if any(not chunk.text.strip() for chunk in chunks):
            self.logger.warning("Empty chunks found")
        
        self.logger.info(f"Validated {len(chunks)} chunks successfully")
        return True


# Factory function for dependency injection
def create_chunk_manager() -> ChunkManager:
    """
    Create a ChunkManager instance.
    
    Returns:
        Configured ChunkManager instance
    """
    return ChunkManager()


# Utility functions for common operations
def split_into_chunks(document_text: str) -> List[DocumentChunk]:
    """
    Convenience function to split document into chunks.
    
    Args:
        document_text: Document text to split
        
    Returns:
        List of DocumentChunk objects
    """
    manager = create_chunk_manager()
    return manager.split_document_into_chunks(document_text)


def reconstruct_from_chunks(chunks: List[DocumentChunk]) -> str:
    """
    Convenience function to reconstruct document from chunks.
    
    Args:
        chunks: List of chunks to reconstruct
        
    Returns:
        Reconstructed document text
    """
    manager = create_chunk_manager()
    return manager.reconstruct_document_from_chunks(chunks)