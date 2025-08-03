"""
Mermaid图表渲染器

负责将HTML中的Mermaid代码块渲染为高质量的SVG图片，用于PDF导出。
"""

import asyncio
import logging
import re
from typing import Dict, List, Tuple
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class MermaidRenderer:
    """Mermaid图表渲染器类"""
    
    def __init__(self):
        self.mermaid_config = {
            'theme': 'default',
            'themeCSS': '.node rect { fill: #fff; stroke: #000; stroke-width: 1px; }',
            'flowchart': {'curve': 'basis'},
            'sequence': {'actorMargin': 50},
            'gantt': {'fontSize': 11},
        }
    
    async def process_html(self, html_content: str) -> str:
        """
        处理HTML内容，将其中的Mermaid节点渲染为SVG
        
        Args:
            html_content: 包含Mermaid节点的HTML内容
            
        Returns:
            处理后的HTML内容，Mermaid代码已替换为SVG
        """
        try:
            logger.info("开始处理Mermaid图表...")
            
            # 解析HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 查找所有的mermaid-node元素
            mermaid_nodes = soup.find_all(['mermaid-node', 'div'], class_='mermaid-node')
            
            # 额外调试：查找所有包含data-type="mermaid-diagram"的元素
            mermaid_diagrams = soup.find_all(['div'], attrs={'data-type': 'mermaid-diagram'})
            logger.info(f"🔍 Found {len(mermaid_diagrams)} elements with data-type='mermaid-diagram'")
            
            # 合并两种查找方式的结果
            all_mermaid_elements = list(set(mermaid_nodes + mermaid_diagrams))
            
            if not all_mermaid_elements:
                logger.info("❌ 未找到Mermaid节点，直接返回原始HTML")
                logger.info(f"🔍 HTML preview: {html_content[:500]}...")
                logger.info(f"🔍 Searching for mermaid-node class: {html_content.count('mermaid-node')}")
                search_term = 'data-type="mermaid-diagram"'
                logger.info(f"🔍 Searching for data-type=mermaid-diagram: {html_content.count(search_term)}")
                return html_content
            
            logger.info(f"✅ 找到 {len(all_mermaid_elements)} 个Mermaid节点")
            
            # 渲染每个Mermaid节点
            for i, node in enumerate(all_mermaid_elements):
                try:
                    # 提取Mermaid语法和标题
                    syntax = self._extract_mermaid_syntax(node)
                    title = self._extract_mermaid_title(node)
                    
                    if syntax:
                        logger.info(f"渲染第 {i+1} 个Mermaid图表...")
                        logger.info(f"📊 Using syntax: {syntax[:100]}...")
                        svg_content = await self._render_mermaid_to_svg(syntax)
                        
                        if svg_content:
                            # 创建新的SVG容器
                            svg_container = self._create_svg_container(svg_content, title)
                            node.replace_with(BeautifulSoup(svg_container, 'html.parser'))
                            logger.info(f"第 {i+1} 个Mermaid图表渲染成功 - SVG length: {len(svg_content)}")
                        else:
                            logger.warning(f"第 {i+1} 个Mermaid图表渲染失败，保留原始内容")
                    else:
                        logger.warning(f"第 {i+1} 个Mermaid节点未找到语法内容")
                        logger.warning(f"📋 Node details: tag={node.name}, attrs={node.attrs}")
                        
                except Exception as e:
                    logger.error(f"处理第 {i+1} 个Mermaid节点时出错: {str(e)}")
                    continue
            
            result_html = str(soup)
            logger.info("Mermaid图表处理完成")
            return result_html
            
        except Exception as e:
            logger.error(f"处理Mermaid图表时出错: {str(e)}")
            return html_content  # 出错时返回原始内容
    
    def _extract_mermaid_syntax(self, node) -> str:
        """从节点中提取Mermaid语法"""
        logger.info(f"🔍 Extracting mermaid syntax from node: {node.name if hasattr(node, 'name') else 'unknown'}")
        logger.info(f"🔍 Node attributes: {node.attrs if hasattr(node, 'attrs') else 'none'}")
        
        # 尝试从属性中获取
        syntax = node.get('syntax') or node.get('data-syntax')
        
        if syntax:
            logger.info(f"✅ Found syntax in attributes: {syntax[:50]}...")
            return syntax
        
        # 尝试从子元素中查找
        syntax_elem = node.find(['pre', 'code'], class_='mermaid-syntax')
        if syntax_elem:
            logger.info(f"✅ Found syntax in child element: {syntax_elem.get_text()[:50]}...")
            return syntax_elem.get_text().strip()
        
        # 尝试从文本内容中提取
        text_content = node.get_text().strip()
        logger.info(f"🔍 Node text content: {text_content[:100]}...")
        
        if text_content and ('graph' in text_content or 'flowchart' in text_content or 'sequenceDiagram' in text_content):
            return text_content
        
        return ""
    
    def _extract_mermaid_title(self, node) -> str:
        """从节点中提取Mermaid标题"""
        # 尝试从属性中获取
        title = node.get('title') or node.get('data-title')
        
        if title:
            return title
        
        # 尝试从子元素中查找
        title_elem = node.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div'], class_='mermaid-title')
        if title_elem:
            return title_elem.get_text().strip()
        
        return ""
    
    async def _render_mermaid_to_svg(self, mermaid_syntax: str) -> str:
        """
        使用Playwright渲染Mermaid语法为SVG
        
        Args:
            mermaid_syntax: Mermaid语法字符串
            
        Returns:
            渲染后的SVG字符串
        """
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # 创建包含Mermaid的HTML页面
                html_template = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
                    <style>
                        body {{ 
                            margin: 20px; 
                            font-family: 'Arial', sans-serif;
                            background: white;
                        }}
                        .mermaid {{ 
                            text-align: center;
                            background: white;
                            max-width: 100%;
                        }}
                        svg {{
                            max-width: 100% !important;
                            width: 100% !important;
                            height: auto !important;
                            min-width: 400px !important;
                        }}
                    </style>
                </head>
                <body>
                    <div class="mermaid" id="mermaid-diagram">
                        {mermaid_syntax}
                    </div>
                    <script>
                        mermaid.initialize({{
                            startOnLoad: true,
                            theme: 'default',
                            securityLevel: 'loose',
                            fontFamily: 'Arial, sans-serif',
                            flowchart: {{
                                htmlLabels: false,
                                curve: 'basis',
                                useMaxWidth: true,
                                nodeSpacing: 50,
                                rankSpacing: 50
                            }},
                            themeVariables: {{
                                fontSize: '14px',
                                fontSizeNode: '12px',
                                primaryColor: '#ffffff',
                                primaryTextColor: '#000000',
                                primaryBorderColor: '#000000',
                                lineColor: '#000000'
                            }}
                        }});
                    </script>
                </body>
                </html>
                """
                
                await page.set_content(html_template)
                
                # 等待Mermaid渲染完成
                await page.wait_for_timeout(2000)
                
                # 获取渲染后的SVG
                svg_element = await page.query_selector('svg')
                if svg_element:
                    # Get the complete SVG element including opening/closing tags
                    svg_outer = await svg_element.evaluate('el => el.outerHTML')
                    
                    if svg_outer:
                        # Remove CSS animations that break PDF rendering
                        clean_svg = self._remove_css_animations(svg_outer)
                        await browser.close()
                        return clean_svg
                    else:
                        # Fallback: construct SVG from innerHTML and attributes
                        svg_content = await svg_element.inner_html()
                        svg_attrs = await svg_element.evaluate('el => el.getAttributeNames().map(name => `${name}="${el.getAttribute(name)}"`).join(" ")')
                        
                        complete_svg = f'<svg {svg_attrs}>{svg_content}</svg>'
                        clean_svg = self._remove_css_animations(complete_svg)
                        await browser.close()
                        return clean_svg
                else:
                    logger.error("未找到渲染后的SVG元素")
                    await browser.close()
                    return ""
                    
        except Exception as e:
            logger.error(f"Mermaid渲染失败: {str(e)}")
            return ""
    
    def _create_svg_container(self, svg_content: str, title: str = "") -> str:
        """
        创建SVG容器HTML
        
        Args:
            svg_content: SVG内容
            title: 图表标题
            
        Returns:
            包装后的HTML容器
        """
        title_html = ""
        if title:
            title_html = f'<div class="mermaid-title" style="text-align: center; font-weight: bold; margin-bottom: 10px; font-size: 14px;">{title}</div>'
        
        return f'''
        <div class="mermaid-container" style="text-align: center; margin: 20px 0; page-break-inside: avoid;">
            {title_html}
            <div class="mermaid-diagram" style="display: inline-block;">
                {svg_content}
            </div>
        </div>
        '''
    
    def _remove_css_animations(self, svg_content: str) -> str:
        """
        移除SVG中的CSS动画，解决PDF渲染问题
        
        Args:
            svg_content: 包含动画的SVG内容
            
        Returns:
            移除动画后的SVG内容
        """
        import re
        
        # 移除 @keyframes 动画定义 (更全面的模式)
        svg_content = re.sub(r'@keyframes[^}]*\{[^}]*\}', '', svg_content, flags=re.DOTALL)
        svg_content = re.sub(r'@-webkit-keyframes[^}]*\{[^}]*\}', '', svg_content, flags=re.DOTALL)
        
        # 移除所有animation相关的CSS属性
        svg_content = re.sub(r'animation[^;:]*:[^;]*;', '', svg_content)
        svg_content = re.sub(r'animation[^;:]*\s*:[^;]*;', '', svg_content)
        svg_content = re.sub(r'-webkit-animation[^;:]*:[^;]*;', '', svg_content)
        
        # 移除 transition 属性
        svg_content = re.sub(r'transition[^;:]*:[^;]*;', '', svg_content)
        svg_content = re.sub(r'-webkit-transition[^;:]*:[^;]*;', '', svg_content)
        
        # 移除stroke-dasharray和stroke-dashoffset相关的动画属性
        svg_content = re.sub(r'stroke-dasharray[^;:]*:[^;]*;', '', svg_content)
        svg_content = re.sub(r'stroke-dashoffset[^;:]*:[^;]*;', '', svg_content)
        
        # 清理多余的空白和分号
        svg_content = re.sub(r'\s+', ' ', svg_content)
        svg_content = re.sub(r';\s*;', ';', svg_content)
        svg_content = re.sub(r'style\s*=\s*"[^"]*;"', lambda m: m.group(0).replace(';;', ';'), svg_content)
        
        logger.info("✅ 已移除SVG中的CSS动画和相关属性")
        return svg_content