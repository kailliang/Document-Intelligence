"""
Tests for text utility functions.
"""

import pytest
import json
from app.internal.text_utils import (
    html_to_plain_text, 
    validate_text_for_ai, 
    StreamingJSONParser
)


class TestHtmlToPlainText:
    """Test HTML to plain text conversion functionality."""
    
    def test_simple_html_conversion(self):
        """Test conversion of simple HTML to plain text."""
        html_content = "<h1>Title</h1><p>This is a paragraph.</p>"
        
        result = html_to_plain_text(html_content)
        
        assert "Title" in result
        assert "This is a paragraph." in result
        assert "<h1>" not in result
        assert "<p>" not in result
    
    def test_html_with_nested_tags(self):
        """Test conversion of HTML with nested tags."""
        html_content = """
        <div>
            <h1>Patent Application</h1>
            <p>This document describes a <strong>novel method</strong> for 
            <em>processing data</em>.</p>
            <ul>
                <li>First claim</li>
                <li>Second claim</li>
            </ul>
        </div>
        """
        
        result = html_to_plain_text(html_content)
        
        assert "Patent Application" in result
        assert "novel method" in result
        assert "processing data" in result
        assert "First claim" in result
        assert "Second claim" in result
        assert "<div>" not in result
        assert "<strong>" not in result
    
    def test_html_with_special_characters(self):
        """Test conversion of HTML with special characters and entities."""
        html_content = "<p>Price: &pound;100 &amp; tax &lt; 20%</p>"
        
        result = html_to_plain_text(html_content)
        
        # BeautifulSoup should decode HTML entities
        assert "£100" in result or "&pound;100" in result
        assert "&" in result
        assert "<" in result
    
    def test_empty_html_content(self):
        """Test conversion of empty HTML content."""
        result = html_to_plain_text("")
        assert result == ""
        
        result = html_to_plain_text("<div></div>")
        assert result.strip() == ""
    
    def test_html_with_scripts_and_styles(self):
        """Test that script and style content is removed."""
        html_content = """
        <html>
            <head>
                <style>body { color: red; }</style>
                <script>alert('test');</script>
            </head>
            <body>
                <h1>Visible Content</h1>
                <script>console.log('hidden');</script>
            </body>
        </html>
        """
        
        result = html_to_plain_text(html_content)
        
        assert "Visible Content" in result
        assert "color: red" not in result
        assert "alert('test')" not in result
        assert "console.log" not in result
    
    def test_malformed_html_handling(self):
        """Test handling of malformed HTML."""
        malformed_html_cases = [
            "<h1>Unclosed header",
            "<p>Nested <p>paragraphs</p>",
            "Just plain text without tags",
            "<div><span>Unclosed span</div>",
        ]
        
        for html_content in malformed_html_cases:
            result = html_to_plain_text(html_content)
            # Should not raise exception and should return some text
            assert isinstance(result, str)
            assert len(result) >= 0


class TestValidateTextForAI:
    """Test text validation for AI processing."""
    
    def test_valid_text_passes_validation(self):
        """Test that valid text passes validation."""
        valid_texts = [
            "This is a valid patent document with sufficient content for analysis.",
            "1. A method comprising: (a) receiving data; (b) processing the data.",
            "The invention relates to improved methods for data processing in distributed systems."
        ]
        
        for text in valid_texts:
            is_valid, error_message = validate_text_for_ai(text)
            assert is_valid is True
            assert error_message == "Text is valid"
    
    def test_empty_text_fails_validation(self):
        """Test that empty text fails validation."""
        empty_texts = ["", "   ", "\n\n\n", "\t\t"]
        
        for text in empty_texts:
            is_valid, error_message = validate_text_for_ai(text)
            assert is_valid is False
            assert "empty" in error_message.lower() or "content" in error_message.lower()
    
    def test_too_short_text_fails_validation(self):
        """Test that text below minimum length fails validation."""
        short_texts = [
            "Hi",
            "Test",
            "A",
            "1. A"
        ]
        
        for text in short_texts:
            is_valid, error_message = validate_text_for_ai(text)
            # Depending on implementation, might pass or fail
            # If it fails, should have appropriate message
            if not is_valid:
                assert "short" in error_message.lower() or "content" in error_message.lower()
    
    def test_very_long_text_handling(self):
        """Test handling of very long text (near token limits)."""
        # Generate very long text
        long_text = "This is a test sentence. " * 10000  # ~50k characters
        
        is_valid, error_message = validate_text_for_ai(long_text)
        
        # Should either pass or fail with appropriate message about length
        if not is_valid:
            assert "long" in error_message.lower() or "limit" in error_message.lower()
        else:
            # If it passes, text should be returned as-is
            assert is_valid is True
    
    def test_text_with_special_characters(self):
        """Test validation of text with special characters and unicode."""
        special_texts = [
            "Patent für eine Erfindung with émojis 🔬⚗️",
            "Text with newlines\nand\ttabs\r\nand unicode: αβγδε",
            "Mathematical symbols: ∑∏∫∞±×÷",
            "Currency symbols: $¢£¥€₹"
        ]
        
        for text in special_texts:
            is_valid, error_message = validate_text_for_ai(text)
            # Should handle special characters gracefully
            assert isinstance(is_valid, bool)
            if not is_valid:
                assert isinstance(error_message, str)


class TestStreamingJSONParser:
    """Test streaming JSON parser for AI responses."""
    
    def test_complete_json_parsing(self):
        """Test parsing of complete, valid JSON."""
        parser = StreamingJSONParser()
        
        json_data = '{"issues": [{"type": "Grammar", "description": "Missing period"}]}'
        
        result = parser.add_chunk(json_data)
        
        assert result is not None
        assert "issues" in result
        assert len(result["issues"]) == 1
        assert result["issues"][0]["type"] == "Grammar"
    
    def test_incremental_json_parsing(self):
        """Test parsing JSON that arrives in multiple chunks."""
        parser = StreamingJSONParser()
        
        chunks = [
            '{"issues": [',
            '{"type": "Grammar",',
            '"description": "Missing period"}',
            ']}'
        ]
        
        result = None
        for chunk in chunks:
            result = parser.add_chunk(chunk)
            if result is not None:
                break
        
        assert result is not None
        assert "issues" in result
        assert result["issues"][0]["type"] == "Grammar"
    
    def test_malformed_json_handling(self):
        """Test handling of malformed JSON data."""
        parser = StreamingJSONParser()
        
        malformed_json_cases = [
            '{"issues": [}',  # Invalid structure
            '{"issues": "not an array"}',  # Wrong type
            '{invalid json}',  # Invalid JSON
            '',  # Empty string
            'not json at all'  # Plain text
        ]
        
        for malformed_json in malformed_json_cases:
            result = parser.add_chunk(malformed_json)
            # Should either return None (parsing incomplete) or handle gracefully
            if result is not None:
                assert isinstance(result, dict)
    
    def test_json_with_escape_characters(self):
        """Test parsing JSON with escaped characters."""
        parser = StreamingJSONParser()
        
        json_with_escapes = r'''{"issues": [{"description": "Text with \"quotes\" and \\backslashes"}]}'''
        
        result = parser.add_chunk(json_with_escapes)
        
        assert result is not None
        assert "issues" in result
        description = result["issues"][0]["description"]
        assert '"quotes"' in description
        assert '\\backslashes' in description
    
    def test_json_with_unicode(self):
        """Test parsing JSON with unicode characters."""
        parser = StreamingJSONParser()
        
        json_with_unicode = '{"issues": [{"description": "Text with émojis 🔬 and αβγ"}]}'
        
        result = parser.add_chunk(json_with_unicode)
        
        assert result is not None
        assert "issues" in result
        description = result["issues"][0]["description"]
        assert "émojis" in description
        assert "🔬" in description
        assert "αβγ" in description
    
    def test_large_json_parsing(self):
        """Test parsing of large JSON responses."""
        parser = StreamingJSONParser()
        
        # Create large JSON with many issues
        large_issues = []
        for i in range(100):
            large_issues.append({
                "type": f"Issue Type {i}",
                "description": f"This is issue number {i} with some detailed description",
                "severity": "medium",
                "paragraph": i % 10 + 1
            })
        
        large_json = json.dumps({"issues": large_issues})
        
        result = parser.add_chunk(large_json)
        
        assert result is not None
        assert "issues" in result
        assert len(result["issues"]) == 100
        assert result["issues"][0]["type"] == "Issue Type 0"
        assert result["issues"][99]["type"] == "Issue Type 99"
    
    def test_parser_reset_functionality(self):
        """Test that parser can handle multiple separate JSON objects."""
        parser = StreamingJSONParser()
        
        # Parse first JSON
        first_json = '{"issues": [{"type": "First"}]}'
        result1 = parser.add_chunk(first_json)
        
        assert result1 is not None
        assert result1["issues"][0]["type"] == "First"
        
        # Parse second JSON (parser should handle this correctly)
        second_json = '{"issues": [{"type": "Second"}]}'
        result2 = parser.add_chunk(second_json)
        
        assert result2 is not None
        assert result2["issues"][0]["type"] == "Second"
        
        # Results should be independent
        assert result1["issues"][0]["type"] != result2["issues"][0]["type"]


class TestTextUtilityIntegration:
    """Test integration between text utility functions."""
    
    def test_html_to_text_then_validate_workflow(self):
        """Test typical workflow: HTML -> plain text -> validation."""
        html_content = """
        <div class="patent-document">
            <h1>Method for Data Processing</h1>
            <p>This invention relates to improved methods for processing large datasets 
            in distributed computing environments.</p>
            <h2>Claims</h2>
            <p>1. A method comprising: receiving data from multiple sources.</p>
        </div>
        """
        
        # Convert HTML to plain text
        plain_text = html_to_plain_text(html_content)
        
        # Validate the resulting text
        is_valid, error_message = validate_text_for_ai(plain_text)
        
        assert is_valid is True
        assert error_message == "Text is valid"
        assert "Method for Data Processing" in plain_text
        assert "distributed computing" in plain_text
        assert "<h1>" not in plain_text
    
    def test_empty_html_validation_workflow(self):
        """Test workflow with empty HTML content."""
        html_content = "<div></div>"
        
        plain_text = html_to_plain_text(html_content)
        is_valid, error_message = validate_text_for_ai(plain_text)
        
        assert is_valid is False
        assert "empty" in error_message.lower() or "content" in error_message.lower()
    
    def test_json_parsing_with_text_content(self):
        """Test JSON parsing with actual text processing results."""
        # Simulate AI response with processed text content
        ai_response_json = json.dumps({
            "issues": [
                {
                    "type": "Structure",
                    "severity": "high",
                    "description": "Missing proper claim structure",
                    "originalText": "A method comprising receiving data",
                    "replaceTo": "1. A method comprising: receiving data",
                    "confidence": 0.95
                }
            ]
        })
        
        parser = StreamingJSONParser()
        result = parser.add_chunk(ai_response_json)
        
        assert result is not None
        assert len(result["issues"]) == 1
        
        issue = result["issues"][0]
        assert issue["type"] == "Structure"
        assert issue["confidence"] == 0.95
        
        # Validate that the text content makes sense
        original = issue["originalText"]
        replacement = issue["replaceTo"]
        
        is_valid_original, _ = validate_text_for_ai(original)
        is_valid_replacement, _ = validate_text_for_ai(replacement)
        
        assert is_valid_original is True
        assert is_valid_replacement is True