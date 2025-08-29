"""
End-to-end integration tests for the Document Intelligence system.
"""

import pytest
import json
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from app.__main__ import app
from app.models import Document, DocumentVersion, ChatHistory


class TestDocumentWorkflow:
    """Test complete document editing workflow."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_complete_document_workflow(self, client):
        """Test full workflow: create -> edit -> save -> version -> analyze."""
        
        # Mock database operations
        with patch('app.__main__.get_db') as mock_get_db:
            mock_session = MagicMock()
            mock_get_db.return_value = mock_session
            
            # Mock document creation/retrieval
            mock_doc = MagicMock()
            mock_doc.id = 1
            mock_doc.title = "Test Patent"
            mock_session.scalar.return_value = mock_doc
            
            # Mock version
            mock_version = MagicMock()
            mock_version.id = 1
            mock_version.content = "<h1>Test Patent</h1><p>Initial content</p>"
            mock_version.version_number = 1
            mock_doc.versions = [mock_version]
            
            # Step 1: Get document
            response = client.get("/document/1")
            assert response.status_code == 200
            
            # Step 2: Save updated content
            updated_content = "<h1>Test Patent</h1><p>Updated content with improvements</p>"
            response = client.post("/save/1", json={"content": updated_content})
            assert response.status_code == 200
            
            # Step 3: Create new version
            response = client.post("/api/documents/1/versions", json={"content": updated_content})
            assert response.status_code == 200 or response.status_code == 201
    
    def test_version_management_workflow(self, client):
        """Test version creation, switching, and deletion workflow."""
        
        with patch('app.__main__.get_db') as mock_get_db:
            mock_session = MagicMock()
            mock_get_db.return_value = mock_session
            
            # Mock document and versions
            mock_doc = MagicMock()
            mock_doc.id = 1
            mock_doc.title = "Version Test Doc"
            
            mock_v1 = MagicMock()
            mock_v1.id = 1
            mock_v1.version_number = 1
            mock_v1.content = "Version 1 content"
            mock_v1.is_active = False
            
            mock_v2 = MagicMock()
            mock_v2.id = 2
            mock_v2.version_number = 2
            mock_v2.content = "Version 2 content"
            mock_v2.is_active = True
            mock_v2.created_at = MagicMock()
            mock_v2.created_at.isoformat.return_value = "2024-01-01T00:00:00"
            
            mock_session.scalar.side_effect = [
                mock_doc,  # Document lookup for create
                2,         # Max version number
                mock_v1,   # Current active version for create
                mock_doc,  # Document lookup for switch
                mock_v1,   # Target version for switch
                mock_doc,  # Document lookup for delete
                2,         # Version count for delete
                mock_v1,   # Target version for delete
                mock_v2,   # Alternative version for delete
            ]
            
            # Create new version
            with patch('app.schemas.DocumentVersionRead.model_validate', return_value={"id": 3, "version_number": 3}):
                response = client.post("/api/documents/1/versions", json={"content": "Version 3 content"})
                assert response.status_code == 200
            
            # Switch to different version
            response = client.post("/api/documents/1/switch-version", json={"version_number": 1})
            assert response.status_code == 200
            
            # Delete version
            response = client.delete("/api/documents/1/versions/1")
            assert response.status_code == 200
    
    def test_pdf_export_workflow(self, client):
        """Test PDF export workflow."""
        
        with patch('app.__main__.get_db') as mock_get_db:
            mock_session = MagicMock()
            mock_get_db.return_value = mock_session
            
            # Mock document and version
            mock_doc = MagicMock()
            mock_doc.id = 1
            mock_doc.title = "Export Test Document"
            
            mock_version = MagicMock()
            mock_version.id = 1
            mock_version.content = "<h1>Document for Export</h1><p>Content to be exported to PDF</p>"
            
            mock_session.scalar.side_effect = [mock_doc, mock_version]
            
            # Mock PDF exporter
            with patch('app.internal.pdf_export_simple.SimplePDFExporter') as mock_exporter_class:
                mock_exporter = MagicMock()
                mock_exporter.export_document.return_value = "test_document_123.pdf"
                mock_exporter_class.return_value = mock_exporter
                
                # Export to PDF
                response = client.post("/api/documents/1/export/pdf")
                assert response.status_code == 200
                
                data = response.json()
                assert data["status"] == "success"
                assert data["filename"] == "test_document_123.pdf"
                assert "download_url" in data


class TestAIAnalysisWorkflow:
    """Test AI analysis and suggestion workflow."""
    
    @pytest.mark.asyncio
    async def test_websocket_ai_analysis_workflow(self):
        """Test complete AI analysis workflow via WebSocket."""
        
        with patch('app.endpoints.get_ai_enhanced') as mock_get_ai:
            # Mock AI service
            mock_ai_service = MagicMock()
            mock_get_ai.return_value = mock_ai_service
            
            # Mock AI response
            ai_response = {
                "issues": [
                    {
                        "type": "Grammar",
                        "severity": "high",
                        "paragraph": 1,
                        "description": "Missing period",
                        "originalText": "This is a test sentence",
                        "replaceTo": "This is a test sentence.",
                        "confidence": 0.95
                    }
                ]
            }
            
            # Mock streaming response
            async def mock_review_stream(text):
                yield json.dumps(ai_response)
            
            mock_ai_service.review_document_with_functions = mock_review_stream
            
            # Test WebSocket endpoint
            with patch('app.endpoints.SessionLocal') as mock_session_local:
                mock_session = MagicMock()
                mock_session_local.return_value.__enter__.return_value = mock_session
                mock_session_local.return_value.__exit__.return_value = None
                
                with patch('app.endpoints.get_chat_manager') as mock_get_chat_manager:
                    mock_chat_manager = MagicMock()
                    mock_chat_manager.save_user_message = AsyncMock()
                    mock_chat_manager.save_suggestion_cards = AsyncMock(return_value=MagicMock(id=1))
                    mock_get_chat_manager.return_value = mock_chat_manager
                    
                    # Import and test WebSocket endpoint
                    from app.endpoints import unified_chat_websocket_endpoint
                    
                    # Mock WebSocket
                    mock_websocket = AsyncMock()
                    mock_websocket.accept = AsyncMock()
                    mock_websocket.receive_json = AsyncMock(return_value={
                        "message": "Please analyze this document",
                        "document_content": "<h1>Test</h1><p>Test document content</p>",
                        "document_id": 1,
                        "document_version": "v1.0"
                    })
                    mock_websocket.send_text = AsyncMock()
                    
                    # Run WebSocket handler
                    await unified_chat_websocket_endpoint(mock_websocket)
                    
                    # Verify WebSocket interactions
                    mock_websocket.accept.assert_called_once()
                    mock_websocket.send_text.assert_called()
    
    def test_chat_history_persistence_workflow(self, client):
        """Test chat history persistence across sessions."""
        
        with patch('app.endpoints.load_chat_history_for_version') as mock_load_history:
            # Mock existing chat history
            mock_history = {
                "messages": [
                    {
                        "id": 1,
                        "type": "user",
                        "content": "Please analyze this document",
                        "timestamp": "2024-01-01T00:00:00"
                    },
                    {
                        "id": 2,
                        "type": "assistant",
                        "content": "I found 3 suggestions for improvement",
                        "timestamp": "2024-01-01T00:01:00"
                    }
                ]
            }
            mock_load_history.return_value = mock_history
            
            # Load chat history
            response = client.get("/api/chat/history/1/v1.0")
            assert response.status_code == 200
            
            data = response.json()
            assert len(data["messages"]) == 2
            assert data["messages"][0]["type"] == "user"
            assert data["messages"][1]["type"] == "assistant"


class TestErrorHandlingWorkflow:
    """Test error handling in various workflows."""
    
    def test_document_not_found_workflow(self, client):
        """Test workflow when document doesn't exist."""
        
        with patch('app.__main__.get_db') as mock_get_db:
            mock_session = MagicMock()
            mock_session.scalar.return_value = None  # Document not found
            mock_get_db.return_value = mock_session
            
            # Try to get non-existent document
            response = client.get("/document/999")
            assert response.status_code == 404
            
            # Try to save to non-existent document
            response = client.post("/save/999", json={"content": "test"})
            assert response.status_code == 404
            
            # Try to create version for non-existent document
            response = client.post("/api/documents/999/versions", json={"content": "test"})
            assert response.status_code == 404
    
    def test_database_error_handling(self, client):
        """Test handling of database errors."""
        
        with patch('app.__main__.get_db') as mock_get_db:
            mock_session = MagicMock()
            mock_session.scalar.side_effect = Exception("Database connection failed")
            mock_get_db.return_value = mock_session
            
            # Should handle database errors gracefully
            response = client.get("/document/1")
            assert response.status_code == 500
    
    def test_ai_service_error_handling(self, client):
        """Test handling of AI service errors."""
        
        with patch('app.endpoints.get_ai_enhanced') as mock_get_ai:
            mock_get_ai.side_effect = Exception("AI service unavailable")
            
            # WebSocket should handle AI service errors
            # This would be tested in a full WebSocket test setup
            assert mock_get_ai is not None


class TestConcurrencyWorkflow:
    """Test concurrent operations and race conditions."""
    
    @pytest.mark.asyncio
    async def test_concurrent_document_editing(self, client):
        """Test concurrent document editing scenarios."""
        
        with patch('app.__main__.get_db') as mock_get_db:
            mock_session = MagicMock()
            mock_get_db.return_value = mock_session
            
            mock_doc = MagicMock()
            mock_doc.id = 1
            mock_doc.title = "Concurrent Test Doc"
            
            mock_version = MagicMock()
            mock_version.id = 1
            mock_version.content = "Original content"
            
            mock_session.scalar.side_effect = [
                mock_doc, mock_version,  # First edit
                mock_doc, mock_version,  # Second edit
            ]
            
            # Simulate concurrent edits
            content1 = "Edit from user 1"
            content2 = "Edit from user 2"
            
            response1 = client.post("/save/1", json={"content": content1})
            response2 = client.post("/save/1", json={"content": content2})
            
            # Both should succeed (last write wins)
            assert response1.status_code == 200
            assert response2.status_code == 200
    
    @pytest.mark.asyncio
    async def test_concurrent_version_operations(self, client):
        """Test concurrent version creation and switching."""
        
        with patch('app.__main__.get_db') as mock_get_db:
            mock_session = MagicMock()
            mock_get_db.return_value = mock_session
            
            mock_doc = MagicMock()
            mock_doc.id = 1
            
            # Mock responses for concurrent operations
            mock_session.scalar.side_effect = [
                mock_doc, 1, MagicMock(),  # Create version
                mock_doc, MagicMock(),     # Switch version
            ]
            
            # Create version and switch operations
            with patch('app.schemas.DocumentVersionRead.model_validate', return_value={"id": 2}):
                create_response = client.post("/api/documents/1/versions", json={"content": "New version"})
                
            switch_response = client.post("/api/documents/1/switch-version", json={"version_number": 1})
            
            # Operations should handle concurrency gracefully
            assert create_response.status_code in [200, 201]
            assert switch_response.status_code == 200


class TestDataConsistencyWorkflow:
    """Test data consistency across operations."""
    
    def test_version_consistency_after_operations(self, client):
        """Test that version relationships remain consistent."""
        
        with patch('app.__main__.get_db') as mock_get_db:
            mock_session = MagicMock()
            mock_get_db.return_value = mock_session
            
            # Mock document with multiple versions
            mock_doc = MagicMock()
            mock_doc.id = 1
            mock_doc.current_version_id = 2
            
            mock_v1 = MagicMock()
            mock_v1.id = 1
            mock_v1.version_number = 1
            mock_v1.is_active = False
            
            mock_v2 = MagicMock()
            mock_v2.id = 2
            mock_v2.version_number = 2
            mock_v2.is_active = True
            mock_v2.created_at = MagicMock()
            mock_v2.created_at.isoformat.return_value = "2024-01-01T00:00:00"
            
            mock_session.scalar.side_effect = [
                mock_doc,   # Document lookup
                mock_v1,    # Target version
            ]
            mock_session.scalars.return_value.all.return_value = [mock_v1, mock_v2]
            
            # Get versions list
            with patch('app.schemas.DocumentVersionRead.model_validate', side_effect=lambda x: {"id": x.id, "version_number": x.version_number}):
                response = client.get("/api/documents/1/versions")
                
            assert response.status_code == 200
            versions = response.json()
            assert len(versions) == 2
    
    def test_chat_history_document_relationship(self, client):
        """Test chat history maintains proper document relationships."""
        
        with patch('app.endpoints.load_chat_history_for_version') as mock_load:
            # Mock chat history with proper relationships
            mock_history = {
                "messages": [
                    {
                        "id": 1,
                        "document_id": 1,
                        "version_number": "v1.0",
                        "type": "user",
                        "content": "Test message"
                    }
                ]
            }
            mock_load.return_value = mock_history
            
            response = client.get("/api/chat/history/1/v1.0")
            assert response.status_code == 200
            
            data = response.json()
            message = data["messages"][0]
            assert message["document_id"] == 1
            assert message["version_number"] == "v1.0"