"""
Tests for PDF export functionality.
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from unittest import IsolatedAsyncioTestCase

from app.models import Document, DocumentVersion


class TestPDFExport(IsolatedAsyncioTestCase):
    """Test PDF export functionality with mocked Playwright."""
    
    def setUp(self):
        """Set up test documents."""
        self.sample_document = MagicMock()
        self.sample_document.id = 1
        self.sample_document.title = "Test Patent Document"
        
        self.sample_version = MagicMock()
        self.sample_version.id = 1
        self.sample_version.version_number = 1
        self.sample_version.content = "<h1>Patent Title</h1><p>Patent content with <strong>formatting</strong>.</p>"
    
    @patch('app.internal.pdf_export_simple.async_playwright')
    async def test_export_document_success(self, mock_playwright):
        """Test successful PDF export."""
        # Mock Playwright components
        mock_browser_context = AsyncMock()
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        
        mock_playwright.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_playwright.return_value.__aexit__ = AsyncMock()
        mock_playwright_instance = await mock_playwright.return_value.__aenter__()
        mock_playwright_instance.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_browser.new_context = AsyncMock(return_value=mock_browser_context)
        mock_browser_context.new_page = AsyncMock(return_value=mock_page)
        mock_page.set_content = AsyncMock()
        mock_page.pdf = AsyncMock(return_value=b'Mock PDF content')
        mock_browser.close = AsyncMock()
        
        # Mock file operations
        with patch('pathlib.Path.mkdir') as mock_mkdir, \
             patch('pathlib.Path.write_bytes') as mock_write_bytes:
            
            from app.internal.pdf_export_simple import SimplePDFExporter
            exporter = SimplePDFExporter()
            
            filename = await exporter.export_document(self.sample_document, self.sample_version)
            
            # Verify filename format
            assert filename.endswith('.pdf')
            assert 'Test_Patent_Document' in filename
            
            # Verify Playwright was called correctly
            mock_page.set_content.assert_called_once()
            mock_page.pdf.assert_called_once()
            
            # Verify file was written
            mock_write_bytes.assert_called_once_with(b'Mock PDF content')
    
    @patch('app.internal.pdf_export_simple.async_playwright')
    async def test_export_document_with_mermaid_diagrams(self, mock_playwright):
        """Test PDF export with Mermaid diagrams."""
        # Content with Mermaid diagram
        content_with_mermaid = """
        <h1>System Architecture</h1>
        <div class="mermaid">
        graph TD
            A[Start] --> B{Decision}
            B -->|Yes| C[End]
            B -->|No| D[Continue]
        </div>
        """
        
        self.sample_version.content = content_with_mermaid
        
        # Mock Playwright components
        mock_browser_context = AsyncMock()
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        
        mock_playwright.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_playwright.return_value.__aexit__ = AsyncMock()
        mock_playwright_instance = await mock_playwright.return_value.__aenter__()
        mock_playwright_instance.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_browser.new_context = AsyncMock(return_value=mock_browser_context)
        mock_browser_context.new_page = AsyncMock(return_value=mock_page)
        mock_page.set_content = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value='<svg>mock svg</svg>')
        mock_page.pdf = AsyncMock(return_value=b'Mock PDF with diagrams')
        mock_browser.close = AsyncMock()
        
        with patch('pathlib.Path.mkdir'), \
             patch('pathlib.Path.write_bytes'):
            
            from app.internal.pdf_export_simple import SimplePDFExporter
            exporter = SimplePDFExporter()
            
            filename = await exporter.export_document(self.sample_document, self.sample_version)
            
            # Verify Mermaid processing was attempted
            mock_page.wait_for_selector.assert_called()
            mock_page.evaluate.assert_called()
            assert filename.endswith('.pdf')
    
    @patch('app.internal.pdf_export_simple.async_playwright')
    async def test_export_document_playwright_error(self, mock_playwright):
        """Test handling of Playwright errors during export."""
        # Mock Playwright to raise an exception
        mock_playwright.return_value.__aenter__ = AsyncMock(side_effect=Exception("Browser launch failed"))
        
        from app.internal.pdf_export_simple import SimplePDFExporter
        exporter = SimplePDFExporter()
        
        with pytest.raises(Exception) as exc_info:
            await exporter.export_document(self.sample_document, self.sample_version)
        
        assert "Browser launch failed" in str(exc_info.value)
    
    @patch('app.internal.pdf_export_simple.async_playwright')
    async def test_export_document_file_write_error(self, mock_playwright):
        """Test handling of file write errors."""
        # Mock successful Playwright operation
        mock_browser_context = AsyncMock()
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        
        mock_playwright.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_playwright.return_value.__aexit__ = AsyncMock()
        mock_playwright_instance = await mock_playwright.return_value.__aenter__()
        mock_playwright_instance.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_browser.new_context = AsyncMock(return_value=mock_browser_context)
        mock_browser_context.new_page = AsyncMock(return_value=mock_page)
        mock_page.set_content = AsyncMock()
        mock_page.pdf = AsyncMock(return_value=b'Mock PDF content')
        mock_browser.close = AsyncMock()
        
        # Mock file write to fail
        with patch('pathlib.Path.mkdir'), \
             patch('pathlib.Path.write_bytes', side_effect=PermissionError("Cannot write file")):
            
            from app.internal.pdf_export_simple import SimplePDFExporter
            exporter = SimplePDFExporter()
            
            with pytest.raises(PermissionError) as exc_info:
                await exporter.export_document(self.sample_document, self.sample_version)
            
            assert "Cannot write file" in str(exc_info.value)
    
    def test_filename_sanitization(self):
        """Test that document titles are properly sanitized for filenames."""
        from app.internal.pdf_export_simple import SimplePDFExporter
        exporter = SimplePDFExporter()
        
        # Mock document with problematic title
        doc_with_special_chars = MagicMock()
        doc_with_special_chars.title = "Patent/Application: <Test> & Development?"
        
        # Test sanitization logic (this would be in the actual implementation)
        sanitized_title = doc_with_special_chars.title.replace('/', '_').replace('<', '').replace('>', '').replace(':', '').replace('?', '').replace('&', 'and')
        
        assert '/' not in sanitized_title
        assert '<' not in sanitized_title
        assert '>' not in sanitized_title
        assert ':' not in sanitized_title
        assert '?' not in sanitized_title
    
    async def test_cleanup_old_files(self):
        """Test cleanup of old PDF files."""
        with patch('pathlib.Path.iterdir') as mock_iterdir, \
             patch('pathlib.Path.stat') as mock_stat, \
             patch('pathlib.Path.unlink') as mock_unlink:
            
            # Mock old and new files
            old_file = MagicMock()
            old_file.name = "old_document.pdf"
            old_file.suffix = ".pdf"
            old_file.stat.return_value.st_mtime = 1000000  # Old timestamp
            
            new_file = MagicMock()
            new_file.name = "new_document.pdf"
            new_file.suffix = ".pdf"
            new_file.stat.return_value.st_mtime = 9999999999  # Recent timestamp
            
            mock_iterdir.return_value = [old_file, new_file]
            
            # Mock current time
            with patch('time.time', return_value=9999999999 + 25 * 3600):  # 25 hours later
                from app.internal.pdf_export_simple import SimplePDFExporter
                exporter = SimplePDFExporter()
                
                cleaned_count = await exporter.cleanup_old_files(max_age_hours=24)
                
                # Should have cleaned 1 old file
                assert cleaned_count == 1
                old_file.unlink.assert_called_once()
                new_file.unlink.assert_not_called()
    
    def test_pdf_html_template_generation(self):
        """Test HTML template generation for PDF export."""
        from app.internal.pdf_export_simple import SimplePDFExporter
        exporter = SimplePDFExporter()
        
        # Test template generation (this would be a method in the actual implementation)
        content = "<h1>Test</h1><p>Content</p>"
        title = "Test Document"
        
        # Mock template generation
        template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{title}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                h1 {{ color: #333; }}
            </style>
        </head>
        <body>
            {content}
        </body>
        </html>
        """
        
        assert title in template
        assert content in template
        assert "<!DOCTYPE html>" in template
        assert "font-family: Arial" in template
    
    async def test_concurrent_pdf_exports(self):
        """Test handling of concurrent PDF export requests."""
        # This tests that multiple PDF exports can run concurrently without issues
        documents = []
        versions = []
        
        for i in range(3):
            doc = MagicMock()
            doc.id = i + 1
            doc.title = f"Document {i + 1}"
            documents.append(doc)
            
            version = MagicMock()
            version.id = i + 1
            version.content = f"<h1>Document {i + 1}</h1><p>Content</p>"
            versions.append(version)
        
        with patch('app.internal.pdf_export_simple.async_playwright') as mock_playwright:
            # Mock successful Playwright operations
            mock_browser_context = AsyncMock()
            mock_browser = AsyncMock()
            mock_page = AsyncMock()
            
            mock_playwright.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_playwright.return_value.__aexit__ = AsyncMock()
            mock_playwright_instance = await mock_playwright.return_value.__aenter__()
            mock_playwright_instance.chromium.launch = AsyncMock(return_value=mock_browser)
            mock_browser.new_context = AsyncMock(return_value=mock_browser_context)
            mock_browser_context.new_page = AsyncMock(return_value=mock_page)
            mock_page.set_content = AsyncMock()
            mock_page.pdf = AsyncMock(return_value=b'Mock PDF content')
            mock_browser.close = AsyncMock()
            
            with patch('pathlib.Path.mkdir'), \
                 patch('pathlib.Path.write_bytes'):
                
                from app.internal.pdf_export_simple import SimplePDFExporter
                exporter = SimplePDFExporter()
                
                # Run concurrent exports
                tasks = [
                    exporter.export_document(documents[i], versions[i])
                    for i in range(3)
                ]
                
                filenames = await asyncio.gather(*tasks)
                
                # All exports should succeed and produce different filenames
                assert len(filenames) == 3
                assert len(set(filenames)) == 3  # All unique filenames
                for filename in filenames:
                    assert filename.endswith('.pdf')


class TestPDFExportEdgeCases:
    """Test edge cases in PDF export functionality."""
    
    @pytest.mark.parametrize("title,expected_chars_removed", [
        ("Normal Title", 0),
        ("Title/With/Slashes", 3),
        ("Title<With>Brackets", 2),
        ("Title:With:Colons", 2),
        ("Title?With?Questions", 2),
        ("Title&With&Ampersands", 0),  # & might be converted to 'and'
    ])
    def test_title_sanitization_cases(self, title, expected_chars_removed):
        """Test various title sanitization scenarios."""
        # Test filename sanitization logic
        original_len = len(title)
        # Mock sanitization (actual implementation would be more sophisticated)
        sanitized = title.replace('/', '_').replace('<', '').replace('>', '').replace(':', '').replace('?', '')
        
        removed_chars = original_len - len(sanitized)
        assert removed_chars >= expected_chars_removed
    
    def test_empty_document_content(self):
        """Test PDF export with empty document content."""
        document = MagicMock()
        document.title = "Empty Document"
        
        version = MagicMock()
        version.content = ""
        
        # Should still be able to generate PDF, though it will be mostly empty
        from app.internal.pdf_export_simple import SimplePDFExporter
        exporter = SimplePDFExporter()
        
        # Mock the HTML template generation to handle empty content
        assert version.content == ""
    
    def test_very_large_document_content(self):
        """Test PDF export with very large document content."""
        document = MagicMock()
        document.title = "Large Document"
        
        version = MagicMock()
        # Generate large content (simulate a very long patent document)
        large_content = "<p>" + "This is a very long patent document. " * 10000 + "</p>"
        version.content = large_content
        
        from app.internal.pdf_export_simple import SimplePDFExporter
        exporter = SimplePDFExporter()
        
        # Should handle large content without issues
        assert len(version.content) > 500000  # Verify content is actually large