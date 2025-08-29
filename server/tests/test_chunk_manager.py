"""
Test suite for document chunking system
"""

import pytest
import re
from app.internal.chunk_manager import ChunkManager, DocumentChunk, create_chunk_manager
from app.internal.text_utils import create_chunks_from_text, reconstruct_text_from_chunks, convert_chunks_to_full_text


class TestDocumentChunk:
    """Test DocumentChunk dataclass"""
    
    def test_chunk_creation(self):
        """Test basic chunk creation"""
        chunk = DocumentChunk(
            chunk_id="test_001",
            text="This is a test paragraph.",
            position=0,
            start_char=0,
            end_char=25
        )
        
        assert chunk.chunk_id == "test_001"
        assert chunk.text == "This is a test paragraph."
        assert chunk.position == 0
    
    def test_chunk_to_dict(self):
        """Test chunk serialization"""
        chunk = DocumentChunk(
            chunk_id="test_001",
            text="Test text",
            position=0,
            start_char=0,
            end_char=9
        )
        
        chunk_dict = chunk.to_dict()
        
        assert chunk_dict["chunk_id"] == "test_001"
        assert chunk_dict["text"] == "Test text"
        assert chunk_dict["position"] == 0
    
    def test_chunk_from_dict(self):
        """Test chunk deserialization"""
        chunk_data = {
            "chunk_id": "test_001",
            "text": "Test text",
            "position": 0,
            "start_char": 0,
            "end_char": 9
        }
        
        chunk = DocumentChunk.from_dict(chunk_data)
        
        assert chunk.chunk_id == "test_001"
        assert chunk.text == "Test text"


class TestChunkManager:
    """Test ChunkManager functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        self.manager = create_chunk_manager()
        self.sample_document = """This is the first paragraph of a patent document.
It contains technical details about the invention.

This is the second paragraph.
It provides background information and prior art discussion.

This is the third paragraph with claims.
Claim 1: A system comprising a processor configured to execute instructions."""
    
    def test_split_document_into_chunks(self):
        """Test document splitting functionality"""
        chunks = self.manager.split_document_into_chunks(self.sample_document)
        
        # Should create 3 chunks for 3 paragraphs
        assert len(chunks) == 3
        
        # Check chunk properties
        for i, chunk in enumerate(chunks):
            assert chunk.position == i
            assert chunk.chunk_id.startswith(f"chunk_{i:03d}")
            assert len(chunk.text.strip()) > 0
            assert chunk.start_char >= 0
            assert chunk.end_char > chunk.start_char
    
    def test_split_empty_document(self):
        """Test handling of empty documents"""
        chunks = self.manager.split_document_into_chunks("")
        assert len(chunks) == 0
        
        chunks = self.manager.split_document_into_chunks("   \n\n  ")
        assert len(chunks) == 0
    
    def test_split_single_paragraph(self):
        """Test single paragraph document"""
        single_para = "This is a single paragraph document without line breaks."
        chunks = self.manager.split_document_into_chunks(single_para)
        
        assert len(chunks) == 1
        assert chunks[0].text == single_para
        assert chunks[0].position == 0
    
    def test_reconstruct_document_from_chunks(self):
        """Test document reconstruction"""
        chunks = self.manager.split_document_into_chunks(self.sample_document)
        reconstructed = self.manager.reconstruct_document_from_chunks(chunks)
        
        # Should be nearly identical (may have minor whitespace differences)
        original_normalized = re.sub(r'\n\s*\n+', '\n\n', self.sample_document.strip())
        reconstructed_normalized = reconstructed.strip()
        
        assert original_normalized == reconstructed_normalized
    
    def test_reconstruct_empty_chunks(self):
        """Test reconstruction with empty chunk list"""
        reconstructed = self.manager.reconstruct_document_from_chunks([])
        assert reconstructed == ""
    
    def test_validate_chunks(self):
        """Test chunk validation"""
        chunks = self.manager.split_document_into_chunks(self.sample_document)
        
        # Valid chunks should pass validation
        assert self.manager.validate_chunks(chunks) is True
        
        # Empty list should be valid
        assert self.manager.validate_chunks([]) is True
    
    def test_validate_chunks_duplicate_ids(self):
        """Test validation with duplicate chunk IDs"""
        chunk1 = DocumentChunk("dup_id", "Text 1", 0, 0, 6)
        chunk2 = DocumentChunk("dup_id", "Text 2", 1, 7, 13)
        
        assert self.manager.validate_chunks([chunk1, chunk2]) is False
    
    def test_validate_chunks_invalid_positions(self):
        """Test validation with invalid positions"""
        chunk1 = DocumentChunk("id1", "Text 1", 0, 0, 6)
        chunk2 = DocumentChunk("id2", "Text 2", 2, 7, 13)  # Position 2 but should be 1
        
        assert self.manager.validate_chunks([chunk1, chunk2]) is False
    
    def test_get_chunk_by_id(self):
        """Test finding chunks by ID"""
        chunks = self.manager.split_document_into_chunks(self.sample_document)
        
        # Get first chunk
        first_chunk = chunks[0]
        found_chunk = self.manager.get_chunk_by_id(chunks, first_chunk.chunk_id)
        
        assert found_chunk is not None
        assert found_chunk.chunk_id == first_chunk.chunk_id
        assert found_chunk.text == first_chunk.text
        
        # Try non-existent ID
        not_found = self.manager.get_chunk_by_id(chunks, "nonexistent_id")
        assert not_found is None
    
    def test_create_chunk_mapping(self):
        """Test basic chunk mapping creation"""
        original_chunks = self.manager.split_document_into_chunks(self.sample_document)
        
        # Create modified version (same structure but different text)
        modified_document = self.sample_document.replace("patent", "invention")
        suggested_chunks = self.manager.split_document_into_chunks(modified_document)
        
        mapping = self.manager.create_chunk_mapping(original_chunks, suggested_chunks)
        
        # Should have mapping for each suggested chunk
        assert len(mapping) == len(suggested_chunks)
        
        # Each mapping should point to corresponding original chunk
        for suggested_chunk in suggested_chunks:
            assert suggested_chunk.chunk_id in mapping
            assert len(mapping[suggested_chunk.chunk_id]) == 1


class TestTextUtilsIntegration:
    """Test text_utils integration with chunking"""
    
    def test_create_chunks_from_text(self):
        """Test convenience function for chunk creation"""
        text = "First paragraph.\n\nSecond paragraph."
        chunks = create_chunks_from_text(text)
        
        assert len(chunks) == 2
        assert chunks[0].position == 0
        assert chunks[1].position == 1
    
    def test_reconstruct_text_from_chunks(self):
        """Test convenience function for reconstruction"""
        text = "First paragraph.\n\nSecond paragraph."
        chunks = create_chunks_from_text(text)
        reconstructed = reconstruct_text_from_chunks(chunks)
        
        assert reconstructed.strip() == text.strip()
    
    def test_convert_chunks_to_full_text(self):
        """Test conversion to agent format"""
        text = "First paragraph.\n\nSecond paragraph."
        chunks = create_chunks_from_text(text)
        agent_text = convert_chunks_to_full_text(chunks)
        
        # Should have single newlines between paragraphs for agent processing
        expected = "First paragraph.\nSecond paragraph."
        assert agent_text == expected


if __name__ == "__main__":
    # Run basic tests
    import sys
    sys.path.append("/Users/kai/Desktop/SI Challenge/Document-Intelligence/server")
    
    print("🧪 Running chunk manager tests...")
    
    # Test document chunk
    chunk = DocumentChunk("test", "Test text", 0, 0, 9)
    print(f"Chunk creation: ✅")
    
    # Test chunk manager
    manager = ChunkManager()
    test_text = "Para 1.\n\nPara 2."
    chunks = manager.split_document_into_chunks(test_text)
    print(f"Chunking: {'✅' if len(chunks) == 2 else '❌'}")
    
    reconstructed = manager.reconstruct_document_from_chunks(chunks)
    print(f"Reconstruction: {'✅' if reconstructed.strip() == test_text.strip() else '❌'}")
    
    print("Basic tests completed!")