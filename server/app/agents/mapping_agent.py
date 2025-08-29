"""
Mapping Agent for Document Chunk Analysis

This agent creates mappings between original and suggested document chunks,
generating severity and confidence scores for each mapping to enable
unique suggestion card generation.
"""

import logging
import json
from typing import Dict, Any, List, Optional
from openai import AsyncOpenAI

from .base_agent import BaseAgent, AnalysisContext
from ..internal.chunk_manager import DocumentChunk
from ..internal.text_utils import create_chunks_from_text

logger = logging.getLogger(__name__)


class MappingAgent(BaseAgent):
    """
    Specialized agent for creating chunk mappings between original and suggested documents.
    
    This agent analyzes the differences between original document chunks and suggested
    document chunks, creating a mapping that includes:
    - Which suggested chunks correspond to which original chunks
    - Severity levels (high/medium/low) for each mapping
    - Confidence scores (0-1) for the mapping quality
    """
    
    def __init__(self, openai_client: AsyncOpenAI):
        super().__init__(openai_client, "mapping")
    
    @property
    def agent_name(self) -> str:
        return "Chunk Mapping"
    
    @property
    def system_prompt(self) -> str:
        return """
You are a document chunk mapping specialist. Your role is to analyze the relationship between original patent document chunks and improved document chunks, creating precise mappings with severity and confidence scores.

**Your Task:**
Compare original document chunks with improved document chunks and create a JSON mapping that shows:

1. **Chunk Relationships**
   - Which suggested chunks correspond to which original chunks
   - Handle one-to-one, many-to-one, and one-to-many relationships
   - Identify merged or split paragraphs

2. **Change Analysis**
   - Assess the significance of changes between chunks
   - Identify technical improvements, legal compliance fixes, and novelty enhancements
   - Evaluate the impact of modifications

3. **Severity Assessment**
   - **High**: Major structural changes, legal compliance fixes, critical technical corrections
   - **Medium**: Significant improvements to clarity, terminology, or technical accuracy  
   - **Low**: Minor refinements, formatting improvements, stylistic changes

4. **Confidence Scoring**
   - **0.9-1.0**: Very clear mapping with obvious chunk relationships
   - **0.7-0.8**: Clear mapping with minor ambiguity
   - **0.5-0.6**: Reasonable mapping with some uncertainty
   - **0.3-0.4**: Uncertain mapping requiring manual review
   - **0.1-0.2**: Poor mapping quality

**Response Format:**
Return ONLY a valid JSON object in this exact format:
```json
{
  "suggested_chunk_id": {
    "original_chunks": ["original_chunk_id1", "original_chunk_id2"],
    "severity": "high|medium|low",
    "confidence": 0.85,
    "change_type": "technical|legal|novelty|combined",
    "description": "Brief description of the change"
  }
}
```

**Important:**
- Each suggested chunk must have exactly one mapping entry
- Original chunks can be referenced by multiple suggested chunks
- Severity and confidence must reflect actual change significance
- Change type should indicate the primary improvement category
- Description should be concise (max 100 characters)

**Example Mapping:**
```json
{
  "chunk_001_abc123": {
    "original_chunks": ["chunk_000_def456"],
    "severity": "high", 
    "confidence": 0.92,
    "change_type": "technical",
    "description": "Added missing colon and fixed claim structure"
  }
}
```
"""
    
    @property
    def function_tools(self) -> List[Dict[str, Any]]:
        # No function tools needed - agent returns JSON directly
        return []
    
    async def create_chunk_mapping(self, original_chunks: List[Dict[str, Any]], 
                                  suggested_chunks: List[Dict[str, Any]],
                                  context: AnalysisContext) -> Dict[str, Any]:
        """
        Create mapping between original and suggested chunks.
        
        Args:
            original_chunks: List of original document chunks (as dicts)
            suggested_chunks: List of suggested document chunks (as dicts)  
            context: Analysis context
            
        Returns:
            Chunk mapping dictionary with severity and confidence scores
        """
        try:
            logger.info(f"Creating chunk mapping: {len(original_chunks)} -> {len(suggested_chunks)} chunks")
            
            if not original_chunks or not suggested_chunks:
                logger.warning("Empty chunks provided for mapping")
                return {}
            
            # Create mapping prompt
            mapping_prompt = self._create_mapping_prompt(original_chunks, suggested_chunks)
            
            # Prepare messages for mapping
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": mapping_prompt}
            ]
            
            # Call OpenAI API for chunk mapping
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1,  # Low temperature for consistent mapping
                max_tokens=3000
            )
            
            mapping_response = response.choices[0].message.content.strip()
            
            # Parse JSON response
            try:
                chunk_mapping = json.loads(mapping_response)
                
                # Validate mapping structure
                if self._validate_mapping(chunk_mapping, original_chunks, suggested_chunks):
                    logger.info(f"Chunk mapping created: {len(chunk_mapping)} mappings")
                    return chunk_mapping
                else:
                    logger.warning("Invalid mapping structure, creating fallback mapping")
                    return self._create_fallback_mapping(original_chunks, suggested_chunks)
                    
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse mapping JSON: {e}")
                logger.debug(f"Raw response: {mapping_response}")
                return self._create_fallback_mapping(original_chunks, suggested_chunks)
            
        except Exception as e:
            logger.error(f"Chunk mapping creation failed: {e}")
            return self._create_fallback_mapping(original_chunks, suggested_chunks)
    
    def _create_mapping_prompt(self, original_chunks: List[Dict[str, Any]], 
                             suggested_chunks: List[Dict[str, Any]]) -> str:
        """
        Create the mapping analysis prompt.
        """
        prompt_parts = [
            "Analyze the relationship between original and suggested document chunks.",
            "",
            "ORIGINAL CHUNKS:",
        ]
        
        for chunk in original_chunks:
            chunk_id = chunk.get("chunk_id", "unknown")
            text = chunk.get("text", "")[:200] + "..." if len(chunk.get("text", "")) > 200 else chunk.get("text", "")
            prompt_parts.append(f"ID: {chunk_id}")
            prompt_parts.append(f"Text: {text}")
            prompt_parts.append("")
        
        prompt_parts.extend([
            "SUGGESTED CHUNKS:",
        ])
        
        for chunk in suggested_chunks:
            chunk_id = chunk.get("chunk_id", "unknown")
            text = chunk.get("text", "")[:200] + "..." if len(chunk.get("text", "")) > 200 else chunk.get("text", "")
            prompt_parts.append(f"ID: {chunk_id}")
            prompt_parts.append(f"Text: {text}")
            prompt_parts.append("")
        
        prompt_parts.extend([
            "Create a JSON mapping showing how suggested chunks relate to original chunks.",
            "Include severity (high/medium/low), confidence (0-1), change type, and description.",
            "Return ONLY the JSON mapping object."
        ])
        
        return "\n".join(prompt_parts)
    
    def _validate_mapping(self, mapping: Dict[str, Any], 
                         original_chunks: List[Dict[str, Any]], 
                         suggested_chunks: List[Dict[str, Any]]) -> bool:
        """
        Validate the structure of the chunk mapping.
        """
        try:
            # Get chunk IDs for validation
            original_ids = {chunk.get("chunk_id") for chunk in original_chunks}
            suggested_ids = {chunk.get("chunk_id") for chunk in suggested_chunks}
            
            for suggested_id, mapping_data in mapping.items():
                # Check if suggested chunk ID exists
                if suggested_id not in suggested_ids:
                    logger.warning(f"Invalid suggested chunk ID in mapping: {suggested_id}")
                    return False
                
                # Check required fields
                required_fields = ["original_chunks", "severity", "confidence", "change_type", "description"]
                if not all(field in mapping_data for field in required_fields):
                    logger.warning(f"Missing required fields in mapping for {suggested_id}")
                    return False
                
                # Validate original chunk references
                original_chunk_refs = mapping_data.get("original_chunks", [])
                if not isinstance(original_chunk_refs, list):
                    logger.warning(f"Invalid original_chunks format for {suggested_id}")
                    return False
                
                for orig_id in original_chunk_refs:
                    if orig_id not in original_ids:
                        logger.warning(f"Invalid original chunk reference: {orig_id}")
                        return False
                
                # Validate severity
                if mapping_data.get("severity") not in ["high", "medium", "low"]:
                    logger.warning(f"Invalid severity for {suggested_id}")
                    return False
                
                # Validate confidence
                confidence = mapping_data.get("confidence")
                if not isinstance(confidence, (int, float)) or not (0 <= confidence <= 1):
                    logger.warning(f"Invalid confidence for {suggested_id}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Mapping validation failed: {e}")
            return False
    
    def _create_fallback_mapping(self, original_chunks: List[Dict[str, Any]], 
                               suggested_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create a simple position-based fallback mapping if AI mapping fails.
        """
        logger.info("Creating fallback chunk mapping")
        
        fallback_mapping = {}
        
        for i, suggested_chunk in enumerate(suggested_chunks):
            suggested_id = suggested_chunk.get("chunk_id", f"suggested_{i}")
            
            # Map to corresponding original chunk by position
            if i < len(original_chunks):
                original_id = original_chunks[i].get("chunk_id", f"original_{i}")
            else:
                # If more suggested chunks than original, map to last original
                original_id = original_chunks[-1].get("chunk_id", "original_last")
            
            fallback_mapping[suggested_id] = {
                "original_chunks": [original_id],
                "severity": "medium",  # Default severity
                "confidence": 0.6,     # Moderate confidence for fallback
                "change_type": "combined",
                "description": "Automated fallback mapping"
            }
        
        logger.info(f"Fallback mapping created: {len(fallback_mapping)} mappings")
        return fallback_mapping
    
    async def _perform_analysis(self, context: AnalysisContext) -> List:
        """
        Legacy method - not used by mapping agent.
        """
        raise NotImplementedError("Mapping agent uses create_chunk_mapping method")


async def create_mapping_agent(openai_client: AsyncOpenAI) -> MappingAgent:
    """
    Factory function to create a MappingAgent instance.
    
    Args:
        openai_client: OpenAI client for API calls
        
    Returns:
        Configured MappingAgent instance
    """
    agent = MappingAgent(openai_client)
    logger.info("Mapping agent created and initialized")
    return agent


# Node function for LangGraph integration
async def mapping_analysis_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node function for chunk mapping analysis.
    
    Args:
        state: Current workflow state containing original chunks and final improved document
        
    Returns:
        Updated state with chunk mapping results
    """
    try:
        # Extract required information from state
        openai_client = state.get("openai_client")
        original_chunks = state.get("original_chunks", [])
        final_improved_document = state.get("final_improved_document", "")
        
        if not openai_client:
            raise ValueError("OpenAI client not available in state")
        
        if not original_chunks:
            logger.warning("No original chunks available for mapping")
            return {
                "chunk_mapping": {}
            }
        
        if not final_improved_document:
            logger.warning("No improved document available for mapping")
            return {
                "chunk_mapping": {}
            }
        
        # Create chunks from final improved document
        suggested_chunks_objects = create_chunks_from_text(final_improved_document)
        suggested_chunks = [chunk.to_dict() for chunk in suggested_chunks_objects]
        
        # Create analysis context
        context = AnalysisContext(
            document_content=final_improved_document,
            document_id=state.get("document_id"),
            version_number=state.get("version_number"),
            user_input=state.get("user_input")
        )
        
        # Create and run mapping agent
        agent = await create_mapping_agent(openai_client)
        chunk_mapping = await agent.create_chunk_mapping(original_chunks, suggested_chunks, context)
        
        logger.info(f"Chunk mapping completed: {len(chunk_mapping)} mappings created")
        
        # Return chunk mapping for suggestion generation
        return {
            "chunk_mapping": chunk_mapping
        }
        
    except Exception as e:
        logger.error(f"Mapping analysis node failed: {e}")
        return {
            "chunk_mapping": {}
        }