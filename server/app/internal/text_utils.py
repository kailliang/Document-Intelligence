"""
Text processing utility module
For handling HTML to plain text conversion and other text-related operations

Why do we need this module?
- TipTap editor outputs HTML format content
- AI service only accepts plain text input
- Need to maintain document logical structure (paragraphs, line breaks, etc.)
"""

from bs4 import BeautifulSoup
import re
import logging
import json
from typing import Optional, Dict, Any, List
from .chunk_manager import DocumentChunk, create_chunk_manager

# Configure logging
logger = logging.getLogger(__name__)


def html_to_plain_text(html_content: str) -> str:
    """
    Convert HTML content to plain text processable by AI
    
    Conversion process:
    1. Use BeautifulSoup to parse HTML structure
    2. Preserve paragraph structure (<p> tags converted to line breaks)
    3. Remove all HTML tags
    4. Clean excess whitespace characters
    
    Args:
        html_content (str): HTML content from TipTap editor
        
    Returns:
        str: Cleaned plain text, maintaining logical structure
        
    Example:
        Input: "<p>First paragraph content</p><p>Second paragraph content</p>"
        Output: "First paragraph content\n\nSecond paragraph content"
    """
    if not html_content or not html_content.strip():
        return ""
    
    try:
        # Use BeautifulSoup to parse HTML
        # html.parser is Python's built-in parser, fast and stable
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Simplified processing: maintain consistency with TipTap editor's getText() method
        # TipTap's getText() adds line breaks after each block-level element
        # Use double newlines to ensure proper paragraph separation for chunk splitting
        for tag in soup.find_all(['p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li']):
            tag.insert_after('\n\n')
        
        # Get plain text content
        text = soup.get_text()
        
        # Clean text:
        # 1. Remove HTML entities (&nbsp; etc.)
        text = re.sub(r'&[a-zA-Z]+;', ' ', text)
        
        # 2. Normalize line breaks (Windows/Mac/Linux compatible)
        text = re.sub(r'\r\n|\r', '\n', text)
        
        # 3. Clean excess whitespace characters
        # Replace multiple consecutive spaces with single space
        text = re.sub(r'[ \t]+', ' ', text)
        
        # 4. Clean excess line breaks (simplified processing)
        # Remove excess consecutive line breaks
        text = re.sub(r'\n\s*\n+', '\n\n', text)
        
        # 5. Remove leading and trailing whitespace
        text = text.strip()
        
        logger.info(f"HTML conversion complete: {len(html_content)} -> {len(text)} characters")
        return text
        
    except Exception as e:
        logger.error(f"HTML to plain text conversion failed: {e}")
        # Fallback processing: simple HTML tag removal
        return re.sub(r'<[^>]+>', '', html_content).strip()


def validate_text_for_ai(text: str) -> tuple[bool, str]:
    """
    Validate if text is suitable for AI processing
    
    Check items:
    1. Text length is reasonable
    2. Contains HTML tags (sign of conversion failure)
    3. Is empty or contains only whitespace characters
    
    Args:
        text (str): Plain text to validate
        
    Returns:
        tuple[bool, str]: (is_valid, error_message)
    """
    if not text or not text.strip():
        return False, "Text is empty"
    
    # Check if still contains HTML tags
    if re.search(r'<[^>]+>', text):
        return False, "Text still contains HTML tags, conversion may have failed"
    
    # Check text length (AI has token limits)
    if len(text) > 10000:  # Limit of approximately 4000 tokens
        return False, f"Text too long ({len(text)} characters), may exceed AI processing limit"
    
    if len(text) < 10:
        return False, "Text too short, may not be valid patent content"
    
    return True, "Text is valid"


def extract_claims_section(text: str) -> str:
    """
    Extract Claims section from patent document
    
    AI prompts are specifically designed to analyze patent Claims section,
    so we only need to send the Claims section to AI
    
    Args:
        text (str): Complete patent document text
        
    Returns:
        str: Claims section text, returns full text if not found
    """
    # Find start of Claims section
    claims_patterns = [
        r'(?i)claims?\s*:?\s*\n',  # "Claims:" or "Claim:"
        r'(?i)什么是声明\s*:?\s*\n',  # Chinese
        r'(?i)权利要求\s*:?\s*\n',   # Chinese patent terminology
    ]
    
    for pattern in claims_patterns:
        match = re.search(pattern, text)
        if match:
            # From Claims start to end of document
            claims_text = text[match.start():]
            logger.info(f"Found Claims section, length: {len(claims_text)}")
            return claims_text
    
    # If Claims section not found, return full text
    logger.warning("Claims section not found, using full text")
    return text


# Test functions
def test_html_conversion():
    """
    Simple test function for testing HTML conversion functionality
    """
    test_cases = [
        # Simple paragraphs
        ("<p>This is first paragraph</p><p>This is second paragraph</p>", "This is first paragraph\n\nThis is second paragraph"),
        
        # Contains lists
        ("<ul><li>First item</li><li>Second item</li></ul>", "- First item\n- Second item"),
        
        # Complex HTML
        ("<div><h1>Title</h1><p>Content with <strong>bold</strong> part</p></div>", "Title\nContent with bold part"),
    ]
    
    print("🧪 Testing HTML conversion functionality...")
    for i, (html_input, expected) in enumerate(test_cases, 1):
        result = html_to_plain_text(html_input)
        success = result.strip() == expected.strip()
        print(f"Test {i}: {'✅' if success else '❌'}")
        if not success:
            print(f"  Expected: {repr(expected)}")
            print(f"  Actual: {repr(result)}")


class StreamingJSONParser:
    """
    Streaming JSON parser
    
    Why do we need this class?
    - AI service returns streaming responses, JSON data sent in multiple chunks
    - Need to cache incomplete JSON data until complete reception
    - Handle potential format errors in AI responses
    
    Usage example:
        parser = StreamingJSONParser()
        for chunk in ai_stream:
            result = parser.add_chunk(chunk)
            if result:
                # Process complete JSON object
                handle_ai_suggestion(result)
    """
    
    def __init__(self):
        """Initialize parser"""
        self.buffer = ""  # Cache incomplete JSON data
        self.reset_count = 0  # Reset counter for debugging
    
    def add_chunk(self, chunk: str) -> Optional[Dict[Any, Any]]:
        """
        Add new JSON data chunk and try to parse
        
        Args:
            chunk (str): JSON data chunk from AI
            
        Returns:
            Optional[Dict]: Returns JSON object if parsing succeeds, otherwise None
        """
        if not chunk:
            return None
        
        # Add new chunk to buffer
        self.buffer += chunk
        
        # Try multiple ways to parse JSON
        return self._try_parse_json()
    
    def _try_parse_json(self) -> Optional[Dict[Any, Any]]:
        """
        Try to parse JSON data in buffer
        
        Processing strategies:
        1. Direct parsing of complete JSON
        2. Clean common format issues
        3. Find and extract possible JSON objects
        """
        if not self.buffer.strip():
            return None
        
        # Strategy 1: Direct parsing
        try:
            result = json.loads(self.buffer)
            self.buffer = ""  # Clear buffer after success
            logger.info("JSON parsing successful (direct parsing)")
            return result
        except json.JSONDecodeError:
            pass
        
        # Strategy 2: Parse after cleaning common issues
        cleaned_buffer = self._clean_json_buffer()
        if cleaned_buffer != self.buffer:
            try:
                result = json.loads(cleaned_buffer)
                self.buffer = ""
                logger.info("JSON parsing successful (after cleaning)")
                return result
            except json.JSONDecodeError:
                pass
        
        # Strategy 3: Find possible complete JSON object
        json_obj = self._extract_json_object()
        if json_obj:
            try:
                result = json.loads(json_obj)
                # Remove parsed part from buffer
                self.buffer = self.buffer[self.buffer.find(json_obj) + len(json_obj):]
                logger.info("JSON parsing successful (object extraction)")
                return result
            except json.JSONDecodeError:
                pass
        
        # If buffer too large, reset to prevent memory issues
        if len(self.buffer) > 10000:
            logger.warning(f"Buffer too large ({len(self.buffer)}), resetting parser")
            self.reset()
        
        return None
    
    def _clean_json_buffer(self) -> str:
        """
        Clean common issues in JSON buffer
        
        Common issues:
        - Excess line breaks and spaces
        - AI-added prefix text
        - Incomplete escape characters
        """
        cleaned = self.buffer
        
        # Remove leading and trailing whitespace
        cleaned = cleaned.strip()
        
        # Remove possible AI prefix (like "Here's the analysis:" etc.)
        # Find first { character, start from there
        first_brace = cleaned.find('{')
        if first_brace > 0:
            cleaned = cleaned[first_brace:]
        
        # Normalize line breaks
        cleaned = re.sub(r'\r\n|\r', '\n', cleaned)
        
        # Remove excess whitespace in JSON (but preserve whitespace within strings)
        # This is more complex, handle simply for now
        cleaned = re.sub(r'\n\s*', '\n', cleaned)
        
        return cleaned
    
    def _extract_json_object(self) -> Optional[str]:
        """
        Extract a possible complete JSON object from the buffer.

        Uses bracket counting to find the boundaries of a complete JSON object.
        """
        cleaned = self._clean_json_buffer()
        
        # Find first { character
        start = cleaned.find('{')
        if start == -1:
            return None
        
        # Use bracket counting to find matching }
        brace_count = 0
        in_string = False
        escape_next = False
        
        for i, char in enumerate(cleaned[start:], start):
            if escape_next:
                escape_next = False
                continue
                
            if char == '\\':
                escape_next = True
                continue
                
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
                
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    
                    # Found matching closing bracket
                    if brace_count == 0:
                        return cleaned[start:i+1]
        
        return None
    
    def reset(self):
        """Reset parser state"""
        self.buffer = ""
        self.reset_count += 1
        logger.info(f"JSON parser reset (attempt {self.reset_count})")
    
    def get_buffer_info(self) -> str:
        """Get buffer information for debugging"""
        return f"Buffer length: {len(self.buffer)}, reset count: {self.reset_count}"


def create_chunks_from_text(text: str) -> List[DocumentChunk]:
    """
    Create document chunks from plain text.
    
    Args:
        text: Plain text document
        
    Returns:
        List of DocumentChunk objects
    """
    chunk_manager = create_chunk_manager()
    return chunk_manager.split_document_into_chunks(text)


def reconstruct_text_from_chunks(chunks: List[DocumentChunk]) -> str:
    """
    Reconstruct document text from chunks.
    
    Args:
        chunks: List of DocumentChunk objects
        
    Returns:
        Reconstructed document text
    """
    chunk_manager = create_chunk_manager()
    return chunk_manager.reconstruct_document_from_chunks(chunks)


def convert_chunks_to_full_text(chunks: List[DocumentChunk]) -> str:
    """
    Convert chunks to full text with paragraph separators for agent processing.
    
    Args:
        chunks: List of DocumentChunk objects
        
    Returns:
        Full text with \n separators between paragraphs
    """
    return "\n".join(chunk.text for chunk in chunks)


def test_streaming_json_parser():
    """
    Test streaming JSON parser
    """
    print("\n🧪 Testing streaming JSON parser...")
    parser = StreamingJSONParser()
    
    # Test case 1: Send complete JSON in chunks
    chunks = ['{"issues":', ' [{"type":', ' "grammar",', ' "severity": "high"}]}']
    print("Test 1: Chunked JSON parsing")
    
    result = None
    for i, chunk in enumerate(chunks):
        print(f"  Adding chunk {i+1}: {chunk}")
        result = parser.add_chunk(chunk)
        if result:
            print(f"  ✅ Parsing successful: {result}")
            break
    
    if not result:
        print("  ❌ Parsing failed")
    
    # Test case 2: JSON with prefix
    parser.reset()
    print("\nTest 2: JSON with prefix")
    messy_json = 'Here is the analysis: {"issues": [{"type": "test"}]}'
    result = parser.add_chunk(messy_json)
    if result:
        print(f"  ✅ Parsing successful: {result}")
    else:
        print("  ❌ Parsing failed")
    
    # Test case 3: Malformed JSON
    parser.reset()
    print("\nTest 3: Malformed JSON handling")
    bad_json = '{"issues": [{"type": "test"'  # Incomplete JSON
    result = parser.add_chunk(bad_json)
    print(f"  Buffer status: {parser.get_buffer_info()}")
    
    # Complete JSON
    result = parser.add_chunk('}]}')
    if result:
        print(f"  ✅ Final parsing successful: {result}")
    else:
        print("  ❌ Final parsing failed")


def test_chunking_operations():
    """
    Test document chunking operations
    """
    print("\n🧪 Testing document chunking...")
    
    test_document = """This is the first paragraph of a patent document.
It describes the technical field of the invention.

This is the second paragraph.
It provides background information about existing solutions.

This is the third paragraph containing claims.
Claim 1: A system comprising a processor and memory."""
    
    # Test chunking
    chunks = create_chunks_from_text(test_document)
    print(f"Created {len(chunks)} chunks:")
    for chunk in chunks:
        print(f"  {chunk.chunk_id}: {chunk.text[:50]}...")
    
    # Test reconstruction
    reconstructed = reconstruct_text_from_chunks(chunks)
    success = reconstructed.strip() == test_document.strip()
    print(f"Reconstruction test: {'✅' if success else '❌'}")
    
    # Test conversion to agent format
    agent_text = convert_chunks_to_full_text(chunks)
    print(f"Agent format text length: {len(agent_text)}")
    print(f"Paragraph count: {agent_text.count(chr(10)) + 1}")


if __name__ == "__main__":
    # Run tests
    test_html_conversion()
    test_streaming_json_parser()
    test_chunking_operations()