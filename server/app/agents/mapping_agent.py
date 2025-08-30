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
   - One original chunk can have one, multiple, or zero corresponding suggested chunks

2. **Change Analysis**
   - Assess the significance of changes between chunks
   - Identify technical improvements, legal compliance fixes, and novelty enhancements

3. **Severity Assessment**
   - **High**: Major structural changes, legal compliance fixes, critical technical corrections
   - **Medium**: Significant improvements to clarity, terminology, or technical accuracy  
   - **Low**: Minor refinements, formatting improvements, stylistic changes

4. **Confidence Scoring**
   - **0.9-1.0**: Very confident in the suggested improvements
   - **0.7-0.8**: Confident with minor uncertainty
   - **0.4-0.6**: Moderately confident in suggestions
   - **0.1-0.3**: Low confidence, suggestions may need review

**Response Format:**
Return ONLY a valid JSON object in this exact format (NO markdown formatting):

{
  "original_chunk_id1": {
    "suggested_chunks": ["suggested_chunk_id1", "suggested_chunk_id2"],
    "severity": "high|medium|low",
    "confidence": 0.85,
    "change_type": "technical|legal|novelty|combined",
    "description": "Brief description of the change with no more than 30 words"
  }
}

**Important:**
- Each original chunk must have exactly one output mapping
- Only select chunk IDs provided, do NOT create new chunk IDs
- Severity must reflect actual change significance
- Change type should indicate the primary improvement category
- Confidence reflects how confident you are in the suggested improvements
- Return raw JSON only, do NOT wrap in markdown code blocks

**Example Mapping:**
{
  "chunk_000_abc123": {
    "suggested_chunks": ["chunk_001_def456", "chunk_002_ghi789"],
    "severity": "high", 
    "confidence": 0.92,
    "change_type": "technical",
    "description": "Split original claim into two separate claims with added technical details"
  }
}
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
                
                # Try to extract JSON from markdown if direct parsing failed
                extracted_json = self._extract_json_from_markdown(mapping_response)
                if extracted_json:
                    try:
                        chunk_mapping = json.loads(extracted_json)
                        if self._validate_mapping(chunk_mapping, original_chunks, suggested_chunks):
                            logger.info(f"Successfully extracted JSON from markdown: {len(chunk_mapping)} mappings")
                            return chunk_mapping
                    except json.JSONDecodeError:
                        logger.error("Extracted JSON is still invalid")
                
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
            text = chunk.get("text", "")[:1000] + "..." if len(chunk.get("text", "")) > 1000 else chunk.get("text", "")
            prompt_parts.append(f"ID: {chunk_id}")
            prompt_parts.append(f"Text: {text}")
            prompt_parts.append("")
        
        prompt_parts.extend([
            "SUGGESTED CHUNKS:",
        ])
        
        for chunk in suggested_chunks:
            chunk_id = chunk.get("chunk_id", "unknown")
            text = chunk.get("text", "")[:1000] + "..." if len(chunk.get("text", "")) > 1000 else chunk.get("text", "")
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
        
        New format expects original chunk IDs as keys mapping to suggested chunks.
        """
        try:
            # Get chunk IDs for validation
            original_ids = {chunk.get("chunk_id") for chunk in original_chunks}
            suggested_ids = {chunk.get("chunk_id") for chunk in suggested_chunks}
            
            for original_id, mapping_data in mapping.items():
                # Check if original chunk ID exists
                if original_id not in original_ids:
                    logger.warning(f"Invalid original chunk ID in mapping: {original_id}")
                    return False
                
                # Check required fields
                required_fields = ["suggested_chunks", "severity", "confidence", "change_type", "description"]
                if not all(field in mapping_data for field in required_fields):
                    logger.warning(f"Missing required fields in mapping for {original_id}")
                    return False
                
                # Validate suggested chunk references
                suggested_chunk_refs = mapping_data.get("suggested_chunks", [])
                if not isinstance(suggested_chunk_refs, list):
                    logger.warning(f"Invalid suggested_chunks format for {original_id}")
                    return False
                
                for sugg_id in suggested_chunk_refs:
                    if sugg_id not in suggested_ids:
                        logger.warning(f"Invalid suggested chunk reference: {sugg_id}")
                        return False
                
                # Validate severity
                if mapping_data.get("severity") not in ["high", "medium", "low"]:
                    logger.warning(f"Invalid severity for {original_id}")
                    return False
                
                # Validate confidence
                confidence = mapping_data.get("confidence")
                if not isinstance(confidence, (int, float)) or not (0 <= confidence <= 1):
                    logger.warning(f"Invalid confidence for {original_id}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Mapping validation failed: {e}")
            return False
    
    def _extract_json_from_markdown(self, text: str) -> Optional[str]:
        """
        Extract JSON content from markdown code blocks.
        
        Args:
            text: Text that may contain JSON wrapped in markdown
            
        Returns:
            Extracted JSON string or None if not found
        """
        import re
        
        # Look for JSON wrapped in markdown code blocks
        patterns = [
            r'```json\s*\n(.*?)\n```',  # ```json\n{...}\n```
            r'```\s*\n(.*?)\n```',     # ```\n{...}\n```
            r'`([^`]*{[^`]*}[^`]*)`',  # `{...}`
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                extracted = match.group(1).strip()
                # Check if it looks like JSON (starts with { and ends with })
                if extracted.startswith('{') and extracted.endswith('}'):
                    return extracted
        
        return None
    
    def _create_fallback_mapping(self, original_chunks: List[Dict[str, Any]], 
                               suggested_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create a simple position-based fallback mapping if AI mapping fails.
        
        New format: original chunk IDs as keys mapping to suggested chunks.
        """
        logger.info("Creating fallback chunk mapping")
        logger.debug(f"Fallback input - Original chunks: {len(original_chunks)}, Suggested chunks: {len(suggested_chunks)}")
        
        fallback_mapping = {}
        
        # Create mapping from each original chunk to corresponding suggested chunks
        for i, original_chunk in enumerate(original_chunks):
            original_id = original_chunk.get("chunk_id", f"original_{i}")
            
            # Map to corresponding suggested chunks by position
            # If fewer suggested chunks than original, some original chunks may map to empty arrays
            suggested_chunk_ids = []
            
            # Simple 1-to-1 mapping by position, or 1-to-many if more suggested chunks
            if i < len(suggested_chunks):
                suggested_id = suggested_chunks[i].get("chunk_id", f"suggested_{i}")
                suggested_chunk_ids.append(suggested_id)
            
            # If there are more suggested chunks than original chunks, 
            # distribute extra suggested chunks among original chunks
            extra_suggested_start = len(original_chunks)
            if i == 0 and len(suggested_chunks) > len(original_chunks):
                # Add extra suggested chunks to the first original chunk
                for j in range(extra_suggested_start, len(suggested_chunks)):
                    extra_suggested_id = suggested_chunks[j].get("chunk_id", f"suggested_{j}")
                    suggested_chunk_ids.append(extra_suggested_id)
            
            fallback_mapping[original_id] = {
                "suggested_chunks": suggested_chunk_ids,
                "severity": "medium",  # Default severity
                "confidence": 0.6,     # Moderate confidence for fallback
                "change_type": "combined",
                "description": "Automated fallback mapping"
            }
            
            if i < 3:  # Log first few for debugging
                logger.debug(f"Fallback mapping {i}: {original_id} -> {suggested_chunk_ids}")
        
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
        # Send progress update for suggestion mapping
        if state.get("progress_callback"):
            await state["progress_callback"]("suggestion_mapping", "mapping", "document_analysis")
            
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
        
        # Return chunk mapping AND suggested chunks to maintain ID consistency
        return {
            "chunk_mapping": chunk_mapping,
            "suggested_chunks": suggested_chunks  # Store chunks to avoid recreating with new IDs
        }
        
    except Exception as e:
        logger.error(f"Mapping analysis node failed: {e}")
        return {
            "chunk_mapping": {}
        }