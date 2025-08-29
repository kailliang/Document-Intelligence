"""
Suggestion Generator for Chunk-Based Suggestions

This module creates unique suggestion cards from chunk mappings,
ensuring no duplicate suggestions are generated.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import uuid4

from .chunk_manager import DocumentChunk

logger = logging.getLogger(__name__)


class SuggestionGenerator:
    """
    Generates unique suggestion cards from chunk mappings.
    
    This generator takes chunk mappings (from mapping agent) and creates
    suggestion cards that:
    - Have unique IDs to prevent duplicates
    - Include severity and confidence from mapping
    - Contain original and suggested text for highlighting
    - Follow the existing suggestion card format
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def generate_suggestions_from_mapping(self, 
                                        chunk_mapping: Dict[str, Any],
                                        original_chunks: List[Dict[str, Any]],
                                        suggested_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate suggestion cards from chunk mapping.
        
        Args:
            chunk_mapping: Mapping from mapping agent with severity/confidence
            original_chunks: Original document chunks
            suggested_chunks: Suggested document chunks
            
        Returns:
            List of suggestion card dictionaries
        """
        self.logger.info(f"Generating suggestions from {len(chunk_mapping)} chunk mappings")
        
        if not chunk_mapping:
            self.logger.warning("No chunk mapping provided")
            return []
        
        # Create lookup dictionaries for chunks
        original_chunks_dict = {chunk.get("chunk_id"): chunk for chunk in original_chunks}
        suggested_chunks_dict = {chunk.get("chunk_id"): chunk for chunk in suggested_chunks}
        
        suggestions = []
        
        for suggested_chunk_id, mapping_data in chunk_mapping.items():
            try:
                suggestion = self._create_suggestion_from_mapping(
                    suggested_chunk_id=suggested_chunk_id,
                    mapping_data=mapping_data,
                    original_chunks_dict=original_chunks_dict,
                    suggested_chunks_dict=suggested_chunks_dict
                )
                
                if suggestion:
                    suggestions.append(suggestion)
                    
            except Exception as e:
                self.logger.error(f"Failed to create suggestion for chunk {suggested_chunk_id}: {e}")
                continue
        
        self.logger.info(f"Generated {len(suggestions)} unique suggestion cards")
        return suggestions
    
    def _create_suggestion_from_mapping(self,
                                      suggested_chunk_id: str,
                                      mapping_data: Dict[str, Any],
                                      original_chunks_dict: Dict[str, Dict[str, Any]],
                                      suggested_chunks_dict: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Create a single suggestion card from mapping data.
        """
        try:
            # Get suggested chunk
            suggested_chunk = suggested_chunks_dict.get(suggested_chunk_id)
            if not suggested_chunk:
                self.logger.warning(f"Suggested chunk not found: {suggested_chunk_id}")
                return None
            
            # Get original chunks that this suggestion maps to
            original_chunk_ids = mapping_data.get("original_chunks", [])
            if not original_chunk_ids:
                self.logger.warning(f"No original chunks mapped for {suggested_chunk_id}")
                return None
            
            # Get the primary original chunk (first in list)
            primary_original_id = original_chunk_ids[0]
            original_chunk = original_chunks_dict.get(primary_original_id)
            
            if not original_chunk:
                self.logger.warning(f"Original chunk not found: {primary_original_id}")
                return None
            
            # Extract text content
            original_text = original_chunk.get("text", "").strip()
            suggested_text = suggested_chunk.get("text", "").strip()
            
            # Skip if texts are identical (no actual change)
            if original_text == suggested_text:
                self.logger.debug(f"Skipping identical chunks: {suggested_chunk_id}")
                return None
            
            # Create suggestion card
            suggestion = {
                "id": f"chunk_{suggested_chunk_id}_{uuid4().hex[:8]}",
                "type": self._determine_suggestion_type(mapping_data),
                "severity": mapping_data.get("severity", "medium"),
                "paragraph": original_chunk.get("position", 0),
                "description": self._create_description(mapping_data, original_text, suggested_text),
                "original_text": original_text,
                "replace_to": suggested_text,
                "confidence": float(mapping_data.get("confidence", 0.7)),
                "agent": self._determine_primary_agent(mapping_data),
                "created_at": datetime.utcnow().isoformat(),
                
                # Additional metadata for chunk-based suggestions
                "chunk_mapping": {
                    "suggested_chunk_id": suggested_chunk_id,
                    "original_chunk_ids": original_chunk_ids,
                    "change_type": mapping_data.get("change_type", "combined")
                }
            }
            
            return suggestion
            
        except Exception as e:
            self.logger.error(f"Error creating suggestion from mapping: {e}")
            return None
    
    def _determine_suggestion_type(self, mapping_data: Dict[str, Any]) -> str:
        """
        Determine the suggestion type from mapping data.
        """
        change_type = mapping_data.get("change_type", "combined")
        severity = mapping_data.get("severity", "medium")
        
        # Map change types to suggestion types
        type_mapping = {
            "technical": "Technical Improvement",
            "legal": "Legal Compliance", 
            "novelty": "Innovation Enhancement",
            "combined": "Document Improvement"
        }
        
        base_type = type_mapping.get(change_type, "Document Improvement")
        
        # Add severity indicator for high-severity changes
        if severity == "high":
            return f"Critical {base_type}"
        
        return base_type
    
    def _create_description(self, mapping_data: Dict[str, Any], 
                          original_text: str, suggested_text: str) -> str:
        """
        Create a descriptive message for the suggestion.
        """
        # Use mapping description if available and meaningful
        mapping_desc = mapping_data.get("description", "").strip()
        if mapping_desc and mapping_desc != "Automated fallback mapping":
            return mapping_desc
        
        # Generate description based on change characteristics
        change_type = mapping_data.get("change_type", "combined")
        severity = mapping_data.get("severity", "medium")
        
        # Analyze text changes to create description
        if len(suggested_text) > len(original_text) * 1.2:
            base_desc = "Expanded content with additional details"
        elif len(suggested_text) < len(original_text) * 0.8:
            base_desc = "Condensed and refined content"
        else:
            base_desc = "Improved content quality and clarity"
        
        # Add change type context
        type_context = {
            "technical": "with technical accuracy improvements",
            "legal": "for legal compliance",
            "novelty": "emphasizing innovation",
            "combined": "incorporating multiple improvements"
        }
        
        context = type_context.get(change_type, "")
        if context:
            base_desc += f" {context}"
        
        return base_desc
    
    def _determine_primary_agent(self, mapping_data: Dict[str, Any]) -> str:
        """
        Determine which agent should be credited for the suggestion.
        """
        change_type = mapping_data.get("change_type", "combined")
        
        agent_mapping = {
            "technical": "technical",
            "legal": "legal",
            "novelty": "novelty",
            "combined": "lead"
        }
        
        return agent_mapping.get(change_type, "lead")
    
    def validate_suggestions(self, suggestions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate and clean suggestion cards.
        
        Args:
            suggestions: List of suggestion dictionaries
            
        Returns:
            Validated and cleaned suggestion list
        """
        validated = []
        seen_ids = set()
        
        for suggestion in suggestions:
            try:
                # Check for required fields
                required_fields = ["id", "type", "severity", "description", "original_text", "replace_to"]
                if not all(field in suggestion for field in required_fields):
                    self.logger.warning(f"Suggestion missing required fields: {suggestion.get('id', 'unknown')}")
                    continue
                
                # Check for duplicate IDs
                suggestion_id = suggestion.get("id")
                if suggestion_id in seen_ids:
                    self.logger.warning(f"Duplicate suggestion ID: {suggestion_id}")
                    # Generate new ID
                    suggestion["id"] = f"chunk_duplicate_{uuid4().hex[:8]}"
                
                seen_ids.add(suggestion.get("id"))
                
                # Validate confidence score
                confidence = suggestion.get("confidence", 0.7)
                if not isinstance(confidence, (int, float)) or not (0 <= confidence <= 1):
                    suggestion["confidence"] = 0.7
                
                # Validate severity
                if suggestion.get("severity") not in ["high", "medium", "low"]:
                    suggestion["severity"] = "medium"
                
                # Ensure texts are not empty
                if not suggestion.get("original_text", "").strip():
                    self.logger.warning(f"Empty original text for suggestion: {suggestion_id}")
                    continue
                
                if not suggestion.get("replace_to", "").strip():
                    self.logger.warning(f"Empty replacement text for suggestion: {suggestion_id}")
                    continue
                
                validated.append(suggestion)
                
            except Exception as e:
                self.logger.error(f"Error validating suggestion: {e}")
                continue
        
        self.logger.info(f"Validated {len(validated)} suggestions from {len(suggestions)} candidates")
        return validated


# Factory function for dependency injection
def create_suggestion_generator() -> SuggestionGenerator:
    """
    Create a SuggestionGenerator instance.
    
    Returns:
        Configured SuggestionGenerator instance
    """
    return SuggestionGenerator()


# Utility functions for external use
def generate_suggestions_from_chunk_mapping(chunk_mapping: Dict[str, Any],
                                          original_chunks: List[Dict[str, Any]],
                                          suggested_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convenience function to generate suggestions from chunk mapping.
    
    Args:
        chunk_mapping: Mapping from mapping agent
        original_chunks: Original document chunks
        suggested_chunks: Suggested document chunks
        
    Returns:
        List of suggestion card dictionaries
    """
    generator = create_suggestion_generator()
    suggestions = generator.generate_suggestions_from_mapping(
        chunk_mapping, original_chunks, suggested_chunks
    )
    return generator.validate_suggestions(suggestions)