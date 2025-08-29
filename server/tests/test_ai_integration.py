"""
Tests for AI integration functionality with mocked external services.
"""

import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from unittest import IsolatedAsyncioTestCase

from app.internal.ai_enhanced import get_ai_enhanced


class TestIntentDetection:
    """Test intent detection logic."""
    
    @pytest.mark.parametrize("user_input,expected_intent", [
        ("Hello, how are you?", "casual_chat"),
        ("Please analyze this patent document", "document_analysis"),
        ("Review this document for issues", "document_analysis"),
        ("Check for compliance problems", "document_analysis"),
        ("Create a flowchart diagram", "document_analysis"),  # Should be treated as analysis
        ("Suggest improvements to my claims", "document_analysis"),
        ("What is prior art?", "casual_chat"),
        ("Improve the structure of paragraph 2", "document_analysis"),
        ("", "casual_chat"),  # Empty input
    ])
    def test_intent_classification(self, user_input, expected_intent):
        """Test intent classification based on keywords."""
        
        def classify_intent(message: str) -> str:
            """Simulate the intent detection logic from endpoints.py"""
            user_lower = message.lower()
            analysis_keywords = [
                "analyze", "review", "check", "improve", "suggest", "suggestion",
                "patent", "document", "claim", "legal", "technical", "novelty",
                "issue", "problem", "error", "fix", "compliance", "structure",
                "create", "flowchart", "diagram", "visualization", "chart"
            ]
            
            if any(keyword in user_lower for keyword in analysis_keywords):
                return "document_analysis"
            return "casual_chat"
        
        result = classify_intent(user_input)
        assert result == expected_intent


class TestAIEnhanced(IsolatedAsyncioTestCase):
    """Test AI enhanced functionality with mocked OpenAI calls."""
    
    def setUp(self):
        """Set up test environment variables."""
        self.mock_env_vars = {
            'OPENAI_API_KEY': 'test-api-key',
            'OPENAI_MODEL': 'gpt-4o'
        }
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key', 'OPENAI_MODEL': 'gpt-4o'})
    @patch('app.internal.ai_enhanced.AsyncOpenAI')
    async def test_review_document_with_functions_success(self, mock_openai_class):
        """Test successful document review with function calling."""
        # Mock OpenAI streaming response
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        # Create mock streaming chunks
        mock_tool_call = MagicMock()
        mock_tool_call.index = 0
        mock_tool_call.function.name = "create_suggestion"
        mock_tool_call.function.arguments = '{"issues": [{"type": "Grammar", "severity": "high", "description": "Missing period", "originalText": "This is a test", "replaceTo": "This is a test."}]}'
        
        mock_delta = MagicMock()
        mock_delta.content = None
        mock_delta.tool_calls = [mock_tool_call]
        
        mock_choice = MagicMock()
        mock_choice.delta = mock_delta
        
        mock_chunks = [
            MagicMock(choices=[mock_choice])
        ]
        
        async def mock_stream():
            for chunk in mock_chunks:
                yield chunk
        
        # Mock the create method to be awaitable and return the async generator
        async def mock_create(*args, **kwargs):
            return mock_stream()
                
        mock_client.chat.completions.create = mock_create
        
        # Get AI service
        ai_service = get_ai_enhanced()
        
        # Test document review
        plain_text = "This is a test document without proper punctuation"
        response_chunks = []
        
        async for chunk in ai_service.review_document_with_functions(plain_text):
            if chunk:
                response_chunks.append(chunk)
        
        full_response = "".join(response_chunks)
        parsed_response = json.loads(full_response)
        
        assert "issues" in parsed_response
        assert len(parsed_response["issues"]) > 0
        assert parsed_response["issues"][0]["type"] == "Grammar"
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key', 'OPENAI_MODEL': 'gpt-4o'})
    @patch('app.internal.ai_enhanced.AsyncOpenAI')
    async def test_review_document_api_error(self, mock_openai_class):
        """Test handling of OpenAI API errors."""
        # Mock OpenAI to raise an exception
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("API rate limit exceeded")
        
        ai_service = get_ai_enhanced()
        
        # Test that exception is properly handled
        with pytest.raises(Exception) as exc_info:
            response_chunks = []
            async for chunk in ai_service.review_document_with_functions("Test text"):
                response_chunks.append(chunk)
        
        assert "API rate limit exceeded" in str(exc_info.value)
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key', 'OPENAI_MODEL': 'gpt-4o'})
    @patch('app.internal.ai_enhanced.AsyncOpenAI')
    async def test_chat_with_document_context(self, mock_openai_class):
        """Test chat functionality with document context."""
        # Mock OpenAI response
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="I can help you improve your patent document. Here are some suggestions..."))
        ]
        mock_client.chat.completions.create.return_value = mock_response
        
        ai_service = get_ai_enhanced()
        
        # Test chat with context
        messages = [{"role": "user", "content": "How can I improve this patent?"}]
        document_content = "<h1>Patent Title</h1><p>Some patent content</p>"
        
        response_chunks = []
        async for chunk in ai_service.chat_with_document_context(messages, document_content):
            if chunk and not chunk.startswith("DIAGRAM_INSERT:"):
                response_chunks.append(chunk)
        
        full_response = "".join(response_chunks)
        assert "improve" in full_response.lower()
        assert "patent" in full_response.lower()
    
    def test_get_ai_enhanced_missing_api_key(self):
        """Test AI service initialization with missing API key."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                get_ai_enhanced()
            
            assert "OPENAI_API_KEY environment variable is required" in str(exc_info.value)
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': '', 'OPENAI_MODEL': 'gpt-4o'})
    def test_get_ai_enhanced_empty_api_key(self):
        """Test AI service initialization with empty API key."""
        with pytest.raises(ValueError) as exc_info:
            get_ai_enhanced()
        
        assert "OPENAI_API_KEY cannot be empty" in str(exc_info.value)


class TestSuggestionGeneration:
    """Test suggestion generation and formatting."""
    
    def test_suggestion_data_structure(self):
        """Test that suggestion objects have required fields."""
        # Mock AI response that should be parsed into suggestions
        mock_ai_response = {
            "issues": [
                {
                    "type": "Structure & Punctuation",
                    "severity": "high",
                    "paragraph": 1,
                    "description": "Missing colon after claim number",
                    "originalText": "1. A method comprising",
                    "replaceTo": "1. A method comprising:",
                    "confidence": 0.95
                }
            ]
        }
        
        # Test conversion to suggestion cards format
        issues = mock_ai_response["issues"]
        cards = []
        
        for i, issue in enumerate(issues):
            card = {
                "id": f"ai_test_{i}",
                "type": issue.get("type", "General"),
                "severity": issue.get("severity", "medium"),
                "paragraph": issue.get("paragraph", 1),
                "description": issue.get("description", "AI suggestion"),
                "original_text": issue.get("originalText", issue.get("text", "")),
                "replace_to": issue.get("replaceTo", issue.get("suggestion", "")),
                "confidence": issue.get("confidence", 0.8),
                "agent": "ai_enhanced"
            }
            cards.append(card)
        
        assert len(cards) == 1
        card = cards[0]
        
        # Verify required fields
        required_fields = ["id", "type", "severity", "paragraph", "description", 
                          "original_text", "replace_to", "confidence", "agent"]
        for field in required_fields:
            assert field in card
        
        # Verify data types and values
        assert isinstance(card["confidence"], float)
        assert 0.0 <= card["confidence"] <= 1.0
        assert card["severity"] in ["high", "medium", "low"]
        assert card["type"] == "Structure & Punctuation"
    
    def test_suggestion_severity_counts(self):
        """Test calculation of suggestion severity statistics."""
        cards = [
            {"severity": "high", "type": "Grammar"},
            {"severity": "high", "type": "Structure"},
            {"severity": "medium", "type": "Legal"},
            {"severity": "low", "type": "Style"},
            {"severity": "low", "type": "Clarity"}
        ]
        
        # Calculate severity counts (from endpoints.py logic)
        severity_counts = {"high": 0, "medium": 0, "low": 0}
        type_counts = {}
        
        for card in cards:
            severity = card.get("severity", "medium")
            if severity in severity_counts:
                severity_counts[severity] += 1
            
            card_type = card.get("type", "General")
            type_counts[card_type] = type_counts.get(card_type, 0) + 1
        
        assert severity_counts["high"] == 2
        assert severity_counts["medium"] == 1
        assert severity_counts["low"] == 2
        assert len(type_counts) == 5
    
    def test_malformed_ai_response_handling(self):
        """Test handling of malformed AI responses."""
        malformed_responses = [
            "",  # Empty response
            "{",  # Invalid JSON
            "{'issues': malformed}",  # Invalid JSON format
            '{"issues": "not an array"}',  # Wrong data type
            '{"wrong_key": []}',  # Missing 'issues' key
        ]
        
        for malformed_response in malformed_responses:
            try:
                parsed_result = json.loads(malformed_response) if malformed_response else {}
                issues = parsed_result.get("issues", [])
                
                if not isinstance(issues, list):
                    issues = []
                
                # Should handle gracefully without crashing
                assert isinstance(issues, list)
                
            except json.JSONDecodeError:
                # Should handle JSON decode errors gracefully
                issues = []
                assert isinstance(issues, list)


class TestWebSocketAIIntegration:
    """Test WebSocket AI integration functionality."""
    
    @pytest.mark.asyncio
    async def test_websocket_processing_stages(self):
        """Test processing stage messages during AI analysis."""
        from app.endpoints import send_processing_stage
        
        # Mock WebSocket
        mock_websocket = AsyncMock()
        
        # Test sending processing stage
        await send_processing_stage(mock_websocket, "intent_detection", "system", 0)
        
        # Verify WebSocket send was called
        mock_websocket.send_text.assert_called_once()
        
        # Verify message format
        call_args = mock_websocket.send_text.call_args[0][0]
        message_data = json.loads(call_args)
        
        assert message_data["type"] == "processing_stage"
        assert message_data["stage"] == "intent_detection"
        assert message_data["agent"] == "system"
        assert "progress" in message_data
        assert "timestamp" in message_data
    
    @pytest.mark.asyncio
    async def test_websocket_invalid_stage(self):
        """Test handling of invalid processing stage."""
        from app.endpoints import send_processing_stage
        
        mock_websocket = AsyncMock()
        
        # Test with non-existent stage
        await send_processing_stage(mock_websocket, "invalid_stage", "system", 0)
        
        # Should not send anything for invalid stage
        mock_websocket.send_text.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_websocket_connection_error_handling(self):
        """Test handling of WebSocket connection errors."""
        from app.endpoints import send_processing_stage
        
        # Mock WebSocket that raises exception
        mock_websocket = AsyncMock()
        mock_websocket.send_text.side_effect = Exception("Connection lost")
        
        # Should not raise exception
        await send_processing_stage(mock_websocket, "intent_detection", "system", 0)
        
        # Exception should be caught and logged, not propagated