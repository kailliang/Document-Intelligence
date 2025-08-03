"""
PDF导出器

负责将HTML内容转换为高质量的PDF文件，支持中文字符和Mermaid图表。
"""

import logging
import uuid
import asyncio
from pathlib import Path
from typing import Optional
from datetime import datetime

from weasyprint import HTML, CSS
from bs4 import BeautifulSoup

from app.models import Document, DocumentVersion
from app.internal.mermaid_render import MermaidRenderer

logger = logging.getLogger(__name__)


class PDFExporter:
    """PDF导出器类"""
    
    def __init__(self):
        # 确保导出目录存在
        self.export_dir = Path("app/static/exports")
        self.export_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化Mermaid渲染器
        self.mermaid_renderer = MermaidRenderer()
        
        # PDF样式配置
        self.pdf_css = """
        @page {
            size: A4;
            margin: 2cm;
            @bottom-center {
                content: counter(page) " / " counter(pages);
                font-size: 10px;
                color: #666;
            }
        }
        
        body {
            font-family: 'Noto Sans CJK SC', 'Microsoft YaHei', Arial, sans-serif;
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
            page-break-after: avoid;
        }
        
        h2 {
            font-size: 16pt;
            font-weight: bold;
            margin-top: 25px;
            margin-bottom: 15px;
            page-break-after: avoid;
        }
        
        h3 {
            font-size: 14pt;
            font-weight: bold;
            margin-top: 20px;
            margin-bottom: 10px;
            page-break-after: avoid;
        }
        
        p {
            margin-bottom: 12px;
            text-align: justify;
            orphans: 2;
            widows: 2;
        }
        
        .mermaid-container {
            text-align: center;
            margin: 25px 0;
            page-break-inside: avoid;
        }
        
        .mermaid-title {
            font-weight: bold;
            margin-bottom: 10px;
            font-size: 11pt;
            color: #555;
        }
        
        .mermaid-diagram {
            display: inline-block;
            max-width: 100%;
        }
        
        .mermaid-diagram svg {
            max-width: 100%;
            height: auto;
        }
        
        /* 确保列表正确显示 */
        ul, ol {
            margin: 10px 0;
            padding-left: 20px;
        }
        
        li {
            margin-bottom: 5px;
        }
        
        /* 表格样式 */
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
        
        /* 代码块样式 */
        pre, code {
            font-family: 'Courier New', monospace;
            background-color: #f8f8f8;
            border: 1px solid #e0e0e0;
            border-radius: 3px;
        }
        
        pre {
            padding: 10px;
            overflow-x: auto;
            page-break-inside: avoid;
        }
        
        code {
            padding: 2px 4px;
            font-size: 11pt;
        }
        """
    
    async def export_document(self, document: Document, version: DocumentVersion) -> str:
        """
        导出文档版本为PDF
        
        Args:
            document: 文档对象
            version: 文档版本对象
            
        Returns:
            生成的PDF文件名
        """
        try:
            logger.info(f"开始导出文档: {document.title} v{version.version_number}")
            
            # 1. 处理Mermaid图表
            logger.info("处理Mermaid图表...")
            processed_html = await self.mermaid_renderer.process_html(version.content)
            
            # 2. 清理和预处理HTML
            logger.info("预处理HTML内容...")
            cleaned_html = self._clean_html_content(processed_html)
            
            # 3. 应用PDF样式
            logger.info("应用PDF样式...")
            styled_html = self._create_pdf_html(cleaned_html, document.title, version.version_number)
            
            # 4. 生成PDF文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_title = self._safe_filename(document.title)
            filename = f"{safe_title}_v{version.version_number}_{timestamp}.pdf"
            file_path = self.export_dir / filename
            
            # 5. 生成PDF
            logger.info(f"生成PDF文件: {filename}")
            self._generate_pdf(styled_html, file_path)
            
            logger.info(f"PDF导出成功: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"PDF导出失败: {str(e)}")
            raise Exception(f"PDF导出失败: {str(e)}")
    
    def _clean_html_content(self, html_content: str) -> str:
        """
        清理HTML内容，移除不必要的属性和样式
        
        Args:
            html_content: 原始HTML内容
            
        Returns:
            清理后的HTML内容
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 移除TipTap特有的属性
            for elem in soup.find_all():
                # 移除data-*属性，但保留Mermaid相关的data属性
                attrs_to_remove = []
                for attr in elem.attrs.keys():
                    if attr.startswith('data-'):
                        # 保留Mermaid相关的data属性
                        if attr not in ['data-syntax', 'data-title', 'data-type']:
                            attrs_to_remove.append(attr)
                        elif attr == 'data-type' and elem.attrs[attr] != 'mermaid-diagram':
                            # 只保留data-type="mermaid-diagram"
                            attrs_to_remove.append(attr)
                
                for attr in attrs_to_remove:
                    del elem.attrs[attr]
                
                # 移除contenteditable属性
                if 'contenteditable' in elem.attrs:
                    del elem.attrs['contenteditable']
                
                # 移除spellcheck属性  
                if 'spellcheck' in elem.attrs:
                    del elem.attrs['spellcheck']
                
                # 清理class属性，只保留必要的
                if 'class' in elem.attrs:
                    classes = elem.attrs['class']
                    if isinstance(classes, list):
                        # 保留有用的class，包括Mermaid相关的
                        useful_classes = [cls for cls in classes if cls in [
                            'mermaid-container', 'mermaid-title', 'mermaid-diagram', 
                            'mermaid-node', 'mermaid-node-wrapper'
                        ]]
                        if useful_classes:
                            elem.attrs['class'] = useful_classes
                        else:
                            del elem.attrs['class']
            
            return str(soup)
            
        except Exception as e:
            logger.warning(f"HTML清理失败，使用原始内容: {str(e)}")
            return html_content
    
    def _create_pdf_html(self, content: str, title: str, version_number: int) -> str:
        """
        创建用于PDF生成的完整HTML文档
        
        Args:
            content: 文档内容HTML
            title: 文档标题
            version_number: 版本号
            
        Returns:
            完整的HTML文档
        """
        # 提取body内容
        soup = BeautifulSoup(content, 'html.parser')
        body_content = soup.find('body')
        if body_content:
            content_html = str(body_content)
            # 移除<body>标签，只保留内容
            content_html = content_html.replace('<body>', '').replace('</body>', '')
        else:
            content_html = content
        
        return f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
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
                    版本: v{version_number} | 导出时间: {datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")}
                </div>
            </header>
            
            <main class="document-content">
                {content_html}
            </main>
        </body>
        </html>
        """
    
    def _generate_pdf(self, html_content: str, output_path: Path) -> None:
        """
        生成PDF文件
        
        Args:
            html_content: HTML内容
            output_path: 输出文件路径
        """
        try:
            # 使用WeasyPrint生成PDF
            html_doc = HTML(string=html_content)
            html_doc.write_pdf(output_path)
            
            logger.info(f"PDF文件生成成功: {output_path}")
            
        except Exception as e:
            logger.error(f"PDF生成失败: {str(e)}")
            raise Exception(f"PDF生成失败: {str(e)}")
    
    def _safe_filename(self, filename: str) -> str:
        """
        生成安全的文件名
        
        Args:
            filename: 原始文件名
            
        Returns:
            安全的文件名
        """
        # 移除或替换不安全的字符
        import re
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
        safe_name = safe_name.strip()
        
        # 限制长度
        if len(safe_name) > 50:
            safe_name = safe_name[:50]
        
        # 如果为空，使用默认名称
        if not safe_name:
            safe_name = "document"
        
        return safe_name
    
    def get_file_path(self, filename: str) -> Path:
        """
        获取文件的完整路径
        
        Args:
            filename: 文件名
            
        Returns:
            文件完整路径
        """
        return self.export_dir / filename
    
    async def cleanup_old_files(self, max_age_hours: int = 24) -> int:
        """
        清理旧的PDF文件
        
        Args:
            max_age_hours: 最大保留时间（小时）
            
        Returns:
            清理的文件数量
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
                        logger.info(f"清理旧文件: {file_path.name}")
            
            logger.info(f"清理完成，共清理 {cleaned_count} 个文件")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"清理文件失败: {str(e)}")
            return 0