"""
Simplified PDF Exporter

Uses Playwright to convert HTML directly to PDF, avoiding complex system dependencies.
"""

import logging
import uuid
import asyncio
from pathlib import Path
from typing import Optional
from datetime import datetime

from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

from app.models import Document, DocumentVersion

logger = logging.getLogger(__name__)


class SimplePDFExporter:
    """Simplified PDF exporter class"""
    
    def __init__(self):
        # Ensure export directory exists
        self.export_dir = Path("app/static/exports")
        self.export_dir.mkdir(parents=True, exist_ok=True)
        
        # PDF styling configuration
        self.pdf_css = """
        @page {
            size: A4;
            margin: 2cm;
        }
        
        body {
            font-family: 'Microsoft YaHei', 'SimHei', Arial, sans-serif;
            font-size: 12pt;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 0;
        }
        
        h1 {
            font-size: 18pt;
            font-weight: bold;
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 10px;
            border-bottom: 2px solid #333;
        }
        
        h2 {
            font-size: 16pt;
            font-weight: bold;
            margin-top: 25px;
            margin-bottom: 15px;
        }
        
        h3 {
            font-size: 14pt;
            font-weight: bold;
            margin-top: 20px;
            margin-bottom: 10px;
        }
        
        p {
            margin-bottom: 12px;
            text-align: justify;
        }
        
        .mermaid-container {
            text-align: center;
            margin: 25px 0;
            page-break-inside: avoid;
            width: 100%;
            overflow: visible;
        }
        
        .mermaid-title {
            font-weight: bold;
            margin-bottom: 10px;
            font-size: 11pt;
            color: #555;
        }
        
        .mermaid-diagram {
            display: block;
            width: 100%;
            overflow: visible;
            text-align: center;
        }
        
        .mermaid-diagram svg {
            max-width: 100%;
            width: auto !important;
            height: auto !important;
            display: inline-block;
            margin: 0 auto;
            font-size: 12px !important;
        }
        
        /* Handle very wide diagrams by scaling them down */
        @media print {
            .mermaid-diagram svg {
                max-width: 100%;
                transform-origin: center top;
            }
            .mermaid-container {
                overflow: visible;
            }
        }
        
        /* Ensure lists display correctly */
        ul, ol {
            margin: 10px 0;
            padding-left: 20px;
        }
        
        li {
            margin-bottom: 5px;
        }
        
        /* Table styling */
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }
        
        th, td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        
        th {
            background-color: #f5f5f5;
            font-weight: bold;
        }
        
        /* Code block styling */
        pre, code {
            font-family: 'Courier New', monospace;
            background-color: #f8f8f8;
            border: 1px solid #e0e0e0;
            border-radius: 3px;
        }
        
        pre {
            padding: 10px;
            overflow-x: auto;
        }
        
        code {
            padding: 2px 4px;
            font-size: 11pt;
        }
        """
    
    async def export_document(self, document: Document, version: DocumentVersion) -> str:
        """
        Export document version to PDF
        
        Args:
            document: Document object
            version: Document version object
            
        Returns:
            Generated PDF filename
        """
        try:
            logger.info(f"Beginning document export: {document.title} v{version.version_number}")
            
            # 1. Process Mermaid diagrams
            logger.info("Processing Mermaid diagrams...")
            from app.internal.mermaid_render import MermaidRenderer
            mermaid_renderer = MermaidRenderer()
            processed_html = await mermaid_renderer.process_html(version.content)
            
            # 2. Clean HTML content
            logger.info("Preprocessing HTML content...")
            cleaned_html = self._clean_html_content(processed_html)
            
            # 3. Apply PDF styling
            logger.info("Applying PDF styling...")
            styled_html = self._create_pdf_html(cleaned_html, document.title, version.version_number)
            
            # 4. Generate PDF filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_title = self._safe_filename(document.title)
            filename = f"{safe_title}_v{version.version_number}_{timestamp}.pdf"
            file_path = self.export_dir / filename
            
            # 5. Generate PDF using Playwright
            logger.info(f"Generating PDF file: {filename}")
            await self._generate_pdf_with_playwright(styled_html, file_path)
            
            logger.info(f"PDF export successful: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"PDF export failed: {str(e)}")
            raise Exception(f"PDF export failed: {str(e)}")
    
    def _clean_html_content(self, html_content: str) -> str:
        """
        Clean HTML content, removing unnecessary attributes and styles
        
        Args:
            html_content: Original HTML content
            
        Returns:
            Cleaned HTML content
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove TipTap-specific attributes but preserve Mermaid-related data attributes
            for elem in soup.find_all():
                # Remove data-* attributes but preserve Mermaid-related data attributes
                attrs_to_remove = []
                for attr in elem.attrs.keys():
                    if attr.startswith('data-'):
                        # Preserve Mermaid-related data attributes
                        if attr not in ['data-syntax', 'data-title', 'data-type']:
                            attrs_to_remove.append(attr)
                        elif attr == 'data-type' and elem.attrs[attr] != 'mermaid-diagram':
                            # Only preserve data-type="mermaid-diagram"
                            attrs_to_remove.append(attr)
                
                for attr in attrs_to_remove:
                    del elem.attrs[attr]
                
                # Remove contenteditable attribute
                if 'contenteditable' in elem.attrs:
                    del elem.attrs['contenteditable']
                
                # Remove spellcheck attribute  
                if 'spellcheck' in elem.attrs:
                    del elem.attrs['spellcheck']
                
                # Clean class attributes, keeping only necessary ones
                if 'class' in elem.attrs:
                    classes = elem.attrs['class']
                    if isinstance(classes, list):
                        # Keep useful classes
                        useful_classes = [cls for cls in classes if cls in ['mermaid-container', 'mermaid-title', 'mermaid-diagram']]
                        if useful_classes:
                            elem.attrs['class'] = useful_classes
                        else:
                            del elem.attrs['class']
            
            return str(soup)
            
        except Exception as e:
            logger.warning(f"HTML cleaning failed, using original content: {str(e)}")
            return html_content
    
    def _create_pdf_html(self, content: str, title: str, version_number: int) -> str:
        """
        Create complete HTML document for PDF generation
        
        Args:
            content: Document content HTML
            title: Document title
            version_number: Version number
            
        Returns:
            Complete HTML document
        """
        # Extract body content
        soup = BeautifulSoup(content, 'html.parser')
        body_content = soup.find('body')
        if body_content:
            content_html = str(body_content)
            # Remove <body> tags, keeping only content
            content_html = content_html.replace('<body>', '').replace('</body>', '')
        else:
            content_html = content
        
        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title} v{version_number}</title>
            <style>
                {self.pdf_css}
            </style>
        </head>
        <body>
            <header class="document-header">
                <h1>{title}</h1>
                <div class="version-info" style="text-align: center; color: #666; font-size: 10pt; margin-bottom: 30px;">
                    Version: v{version_number} | Exported: {datetime.now().strftime("%B %d, %Y at %H:%M:%S")}
                </div>
            </header>
            
            <main class="document-content">
                {content_html}
            </main>
        </body>
        </html>
        """
    
    async def _generate_pdf_with_playwright(self, html_content: str, output_path: Path) -> None:
        """
        Generate PDF file using Playwright
        
        Args:
            html_content: HTML content
            output_path: Output file path
        """
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Set page content
                await page.set_content(html_content, wait_until='networkidle')
                
                # Wait for page rendering to complete
                await page.wait_for_timeout(2000)
                
                # Generate PDF
                await page.pdf(
                    path=str(output_path),
                    format='A4',
                    margin={
                        'top': '2cm',
                        'right': '2cm',
                        'bottom': '2cm',
                        'left': '2cm'
                    },
                    print_background=True,
                    display_header_footer=True,
                    header_template='<div style="font-size:10px; text-align:center; width:100%;"></div>',
                    footer_template='<div style="font-size:10px; text-align:center; width:100%; color:#666;"><span class="pageNumber"></span> / <span class="totalPages"></span></div>'
                )
                
                await browser.close()
                logger.info(f"PDF file generated successfully: {output_path}")
                
        except Exception as e:
            logger.error(f"PDF generation failed: {str(e)}")
            raise Exception(f"PDF generation failed: {str(e)}")
    
    def _safe_filename(self, filename: str) -> str:
        """
        Generate safe filename
        
        Args:
            filename: Original filename
            
        Returns:
            Safe filename
        """
        # Remove or replace unsafe characters
        import re
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
        safe_name = safe_name.strip()
        
        # Limit length
        if len(safe_name) > 50:
            safe_name = safe_name[:50]
        
        # If empty, use default name
        if not safe_name:
            safe_name = "document"
        
        return safe_name
    
    def get_file_path(self, filename: str) -> Path:
        """
        Get complete file path
        
        Args:
            filename: Filename
            
        Returns:
            Complete file path
        """
        return self.export_dir / filename
    
    async def cleanup_old_files(self, max_age_hours: int = 24) -> int:
        """
        Clean up old PDF files
        
        Args:
            max_age_hours: Maximum retention time (hours)
            
        Returns:
            Number of files cleaned
        """
        try:
            import time
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            cleaned_count = 0
            
            for file_path in self.export_dir.glob("*.pdf"):
                if file_path.is_file():
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age > max_age_seconds:
                        file_path.unlink()
                        cleaned_count += 1
                        logger.info(f"Cleaning old file: {file_path.name}")
            
            logger.info(f"Cleanup completed, cleaned {cleaned_count} files")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"File cleanup failed: {str(e)}")
            return 0