"""
Tests for API endpoints.
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from fastapi import status

from app.models import Document, DocumentVersion


class TestDocumentEndpoints:
    """Test document-related API endpoints."""
    
    def test_get_document_success(self, client, sample_document):
        """Test successful document retrieval."""
        with patch('app.__main__.get_db') as mock_get_db:
            mock_session = MagicMock()
            mock_session.scalar.return_value = sample_document
            mock_get_db.return_value = mock_session
            
            response = client.get(f"/document/{sample_document.id}")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == sample_document.id
            assert data["title"] == sample_document.title
            assert "content" in data
    
    def test_get_document_not_found(self, client):
        """Test document retrieval with non-existent ID."""
        with patch('app.__main__.get_db') as mock_get_db:
            mock_session = MagicMock()
            mock_session.scalar.return_value = None
            mock_get_db.return_value = mock_session
            
            response = client.get("/document/999")
            
            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "Document not found" in response.json()["detail"]
    
    def test_save_document_success(self, client, sample_document):
        """Test successful document saving."""
        new_content = "<h1>Updated Content</h1><p>This has been updated.</p>"
        
        with patch('app.__main__.get_db') as mock_get_db:
            mock_session = MagicMock()
            mock_session.scalar.side_effect = [
                sample_document,  # Document lookup
                sample_document.versions[0]  # Current version lookup
            ]
            mock_get_db.return_value = mock_session
            
            response = client.post(
                f"/save/{sample_document.id}",
                json={"content": new_content}
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["document_id"] == sample_document.id
            assert data["content"] == new_content
    
    def test_save_document_not_found(self, client):
        """Test saving to non-existent document."""
        with patch('app.__main__.get_db') as mock_get_db:
            mock_session = MagicMock()
            mock_session.scalar.return_value = None
            mock_get_db.return_value = mock_session
            
            response = client.post(
                "/save/999",
                json={"content": "Updated content"}
            )
            
            assert response.status_code == status.HTTP_404_NOT_FOUND


class TestVersionManagement:
    """Test version management endpoints."""
    
    def test_get_all_documents(self, client):
        """Test retrieving all documents list."""
        mock_docs = [
            MagicMock(id=1, title="Doc 1", created_at=MagicMock(), updated_at=MagicMock()),
            MagicMock(id=2, title="Doc 2", created_at=MagicMock(), updated_at=MagicMock())
        ]
        
        # Mock datetime isoformat methods
        for doc in mock_docs:
            doc.created_at.isoformat.return_value = "2024-01-01T00:00:00"
            doc.updated_at.isoformat.return_value = "2024-01-01T00:00:00"
        
        with patch('app.__main__.get_db') as mock_get_db:
            mock_session = MagicMock()
            mock_session.scalars.return_value.all.return_value = mock_docs
            mock_get_db.return_value = mock_session
            
            response = client.get("/api/documents")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 2
            assert data[0]["id"] == 1
            assert data[1]["id"] == 2
    
    def test_create_version_success(self, client, sample_document):
        """Test creating new version."""
        with patch('app.__main__.get_db') as mock_get_db:
            mock_session = MagicMock()
            mock_session.scalar.side_effect = [
                sample_document,  # Document lookup
                2,  # Max version number
                sample_document.versions[0]  # Current active version
            ]
            mock_new_version = MagicMock(id=2, version_number=3, content="New content")
            mock_session.add.return_value = None
            mock_session.flush.return_value = None
            mock_session.commit.return_value = None
            mock_session.refresh.return_value = None
            mock_get_db.return_value = mock_session
            
            with patch('app.schemas.DocumentVersionRead.model_validate', return_value={"id": 2, "version_number": 3}):
                response = client.post(
                    f"/api/documents/{sample_document.id}/versions",
                    json={"content": "New version content"}
                )
                
                assert response.status_code == status.HTTP_200_OK
    
    def test_create_version_document_not_found(self, client):
        """Test creating version for non-existent document."""
        with patch('app.__main__.get_db') as mock_get_db:
            mock_session = MagicMock()
            mock_session.scalar.return_value = None
            mock_get_db.return_value = mock_session
            
            response = client.post(
                "/api/documents/999/versions",
                json={"content": "New content"}
            )
            
            assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_switch_version_success(self, client, sample_document):
        """Test switching to existing version."""
        target_version = MagicMock(id=2, version_number=2, content="Version 2", created_at=MagicMock())
        target_version.created_at.isoformat.return_value = "2024-01-01T00:00:00"
        
        with patch('app.__main__.get_db') as mock_get_db:
            mock_session = MagicMock()
            mock_session.scalar.side_effect = [
                sample_document,  # Document lookup
                target_version   # Target version lookup
            ]
            mock_get_db.return_value = mock_session
            
            response = client.post(
                f"/api/documents/{sample_document.id}/switch-version",
                json={"version_number": 2}
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["version_number"] == 2
    
    def test_switch_version_not_found(self, client, sample_document):
        """Test switching to non-existent version."""
        with patch('app.__main__.get_db') as mock_get_db:
            mock_session = MagicMock()
            mock_session.scalar.side_effect = [
                sample_document,  # Document lookup
                None  # Version not found
            ]
            mock_get_db.return_value = mock_session
            
            response = client.post(
                f"/api/documents/{sample_document.id}/switch-version",
                json={"version_number": 99}
            )
            
            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "Version 99 not found" in response.json()["detail"]
    
    def test_delete_version_success(self, client, sample_document):
        """Test successful version deletion."""
        target_version = MagicMock(id=2, is_active=False)
        alternative_version = MagicMock(id=1, is_active=True)
        
        with patch('app.__main__.get_db') as mock_get_db:
            mock_session = MagicMock()
            mock_session.scalar.side_effect = [
                sample_document,  # Document lookup
                2,  # Version count
                target_version,  # Target version
            ]
            mock_get_db.return_value = mock_session
            
            response = client.delete(f"/api/documents/{sample_document.id}/versions/2")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "Version 2 deleted successfully" in data["message"]
    
    def test_delete_last_version_fails(self, client, sample_document):
        """Test that deleting last remaining version fails."""
        with patch('app.__main__.get_db') as mock_get_db:
            mock_session = MagicMock()
            mock_session.scalar.side_effect = [
                sample_document,  # Document lookup
                1,  # Only 1 version remains
            ]
            mock_get_db.return_value = mock_session
            
            response = client.delete(f"/api/documents/{sample_document.id}/versions/1")
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "Cannot delete the last remaining version" in response.json()["detail"]
    
    def test_get_versions_list(self, client, sample_document):
        """Test getting list of all versions for document."""
        mock_versions = [
            MagicMock(id=1, version_number=1, created_at=MagicMock()),
            MagicMock(id=2, version_number=2, created_at=MagicMock())
        ]
        
        with patch('app.__main__.get_db') as mock_get_db:
            mock_session = MagicMock()
            mock_session.scalar.return_value = sample_document  # Document exists
            mock_session.scalars.return_value.all.return_value = mock_versions
            mock_get_db.return_value = mock_session
            
            with patch('app.schemas.DocumentVersionRead.model_validate', side_effect=lambda x: {"id": x.id, "version_number": x.version_number}):
                response = client.get(f"/api/documents/{sample_document.id}/versions")
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert len(data) == 2


class TestPDFExport:
    """Test PDF export endpoints."""
    
    def test_export_pdf_success(self, client, sample_document):
        """Test successful PDF export."""
        mock_current_version = MagicMock(id=1, content="<h1>Test</h1>")
        
        with patch('app.__main__.get_db') as mock_get_db:
            mock_session = MagicMock()
            mock_session.scalar.side_effect = [
                sample_document,  # Document lookup
                mock_current_version  # Current version lookup
            ]
            mock_get_db.return_value = mock_session
            
            with patch('app.internal.pdf_export_simple.SimplePDFExporter') as mock_exporter_class:
                mock_exporter = MagicMock()
                mock_exporter.export_document.return_value = "test_document.pdf"
                mock_exporter_class.return_value = mock_exporter
                
                response = client.post(f"/api/documents/{sample_document.id}/export/pdf")
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["status"] == "success"
                assert data["filename"] == "test_document.pdf"
                assert "download_url" in data
    
    def test_export_pdf_document_not_found(self, client):
        """Test PDF export with non-existent document."""
        with patch('app.__main__.get_db') as mock_get_db:
            mock_session = MagicMock()
            mock_session.scalar.return_value = None
            mock_get_db.return_value = mock_session
            
            response = client.post("/api/documents/999/export/pdf")
            
            assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_export_pdf_no_active_version(self, client, sample_document):
        """Test PDF export with no active version."""
        with patch('app.__main__.get_db') as mock_get_db:
            mock_session = MagicMock()
            mock_session.scalar.side_effect = [
                sample_document,  # Document lookup
                None  # No active version
            ]
            mock_get_db.return_value = mock_session
            
            response = client.post(f"/api/documents/{sample_document.id}/export/pdf")
            
            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "No active version found" in response.json()["detail"]
    
    def test_download_pdf_success(self, client, temp_export_dir):
        """Test successful PDF file download."""
        # Create test PDF file
        test_pdf_path = temp_export_dir / "test.pdf"
        test_pdf_path.write_text("Mock PDF content")
        
        with patch('pathlib.Path') as mock_path:
            mock_path.return_value = test_pdf_path
            mock_path.return_value.exists.return_value = True
            mock_path.return_value.is_file.return_value = True
            
            with patch('app.__main__.FileResponse') as mock_file_response:
                mock_file_response.return_value = MagicMock()
                
                response = client.get("/api/downloads/test.pdf")
                
                # We can't easily test the actual file response in unit tests,
                # but we can verify FileResponse was called correctly
                mock_file_response.assert_called_once()
    
    def test_download_pdf_invalid_filename(self, client):
        """Test download with invalid filename (path traversal)."""
        response = client.get("/api/downloads/../../../etc/passwd")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid filename" in response.json()["detail"]
    
    def test_download_pdf_non_pdf_file(self, client):
        """Test download of non-PDF file."""
        response = client.get("/api/downloads/malicious.exe")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Only PDF files are allowed" in response.json()["detail"]
    
    def test_download_pdf_file_not_found(self, client):
        """Test download of non-existent file."""
        with patch('pathlib.Path') as mock_path:
            mock_path.return_value.exists.return_value = False
            
            response = client.get("/api/downloads/nonexistent.pdf")
            
            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "File not found" in response.json()["detail"]


class TestChatHistoryEndpoints:
    """Test chat history related endpoints."""
    
    @pytest.mark.asyncio
    async def test_load_chat_history_success(self, client):
        """Test loading chat history for document version."""
        mock_chat_manager = MagicMock()
        mock_messages = [
            {"id": 1, "type": "user", "content": "Test message"},
            {"id": 2, "type": "assistant", "content": "Test response"}
        ]
        mock_chat_manager.load_chat_history.return_value = mock_messages
        
        with patch('app.endpoints.get_chat_manager', return_value=mock_chat_manager):
            with patch('app.endpoints.load_chat_history_for_version') as mock_endpoint:
                mock_endpoint.return_value = {"messages": mock_messages}
                
                response = client.get("/api/chat/history/1/v1.0")
                
                assert response.status_code == status.HTTP_200_OK
    
    @pytest.mark.asyncio
    async def test_clear_chat_history_success(self, client):
        """Test clearing chat history for document version."""
        with patch('app.endpoints.clear_chat_history_for_version') as mock_endpoint:
            mock_endpoint.return_value = {"status": "success", "cleared_count": 5}
            
            response = client.delete("/api/chat/history/1/v1.0")
            
            assert response.status_code == status.HTTP_200_OK
    
    @pytest.mark.asyncio
    async def test_suggestion_card_action(self, client):
        """Test handling suggestion card actions."""
        with patch('app.endpoints.handle_suggestion_card_action') as mock_endpoint:
            mock_endpoint.return_value = {"status": "success"}
            
            response = client.post("/api/chat/suggestion-action/1/v1.0/123?card_id=card_1&action=accepted")
            
            assert response.status_code == status.HTTP_200_OK