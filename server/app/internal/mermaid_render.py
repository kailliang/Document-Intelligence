"""
Mermaid Diagram Renderer

Responsible for rendering Mermaid code blocks within HTML into high-quality SVG images for PDF export.
"""

import asyncio
import logging
import re
from typing import Dict, List, Tuple
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class MermaidRenderer:
    """Mermaid diagram renderer class"""
    
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
        Process HTML content, rendering Mermaid nodes within it as SVG
        
        Args:
            html_content: HTML content containing Mermaid nodes
            
        Returns:
            Processed HTML content with Mermaid code replaced by SVG
        """
        try:
            logger.info("Beginning Mermaid diagram processing...")
            
            # Parse HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find all mermaid-node elements
            mermaid_nodes = soup.find_all(['mermaid-node', 'div'], class_='mermaid-node')
            
            # Additional debugging: find all elements containing data-type="mermaid-diagram"
            mermaid_diagrams = soup.find_all(['div'], attrs={'data-type': 'mermaid-diagram'})
            logger.info(f"🔍 Found {len(mermaid_diagrams)} elements with data-type='mermaid-diagram'")
            
            # Merge results from both search methods
            all_mermaid_elements = list(set(mermaid_nodes + mermaid_diagrams))
            
            if not all_mermaid_elements:
                logger.info("❌ No Mermaid nodes found, returning original HTML")
                logger.info(f"🔍 HTML preview: {html_content[:500]}...")
                logger.info(f"🔍 Searching for mermaid-node class: {html_content.count('mermaid-node')}")
                search_term = 'data-type="mermaid-diagram"'
                logger.info(f"🔍 Searching for data-type=mermaid-diagram: {html_content.count(search_term)}")
                return html_content
            
            logger.info(f"✅ Found {len(all_mermaid_elements)} Mermaid nodes")
            
            # Render each Mermaid node
            for i, node in enumerate(all_mermaid_elements):
                try:
                    # Extract Mermaid syntax and title
                    syntax = self._extract_mermaid_syntax(node)
                    title = self._extract_mermaid_title(node)
                    
                    if syntax:
                        logger.info(f"Rendering Mermaid diagram {i+1}...")
                        logger.info(f"📊 Using syntax: {syntax[:100]}...")
                        svg_content = await self._render_mermaid_to_svg(syntax)
                        
                        if svg_content:
                            # Create new SVG container
                            svg_container = self._create_svg_container(svg_content, title)
                            node.replace_with(BeautifulSoup(svg_container, 'html.parser'))
                            logger.info(f"Mermaid diagram {i+1} rendered successfully - SVG length: {len(svg_content)}")
                        else:
                            logger.warning(f"Mermaid diagram {i+1} rendering failed, keeping original content")
                    else:
                        logger.warning(f"Mermaid node {i+1} has no syntax content found")
                        logger.warning(f"📋 Node details: tag={node.name}, attrs={node.attrs}")
                        
                except Exception as e:
                    logger.error(f"Error processing Mermaid node {i+1}: {str(e)}")
                    continue
            
            result_html = str(soup)
            logger.info("Mermaid diagram processing completed")
            return result_html
            
        except Exception as e:
            logger.error(f"Error processing Mermaid diagrams: {str(e)}")
            return html_content  # Return original content on error
    
    def _extract_mermaid_syntax(self, node) -> str:
        """Extract Mermaid syntax from node"""
        logger.info(f"🔍 Extracting mermaid syntax from node: {node.name if hasattr(node, 'name') else 'unknown'}")
        logger.info(f"🔍 Node attributes: {node.attrs if hasattr(node, 'attrs') else 'none'}")
        
        # Try to extract from attributes
        syntax = node.get('syntax') or node.get('data-syntax')
        
        if syntax:
            logger.info(f"✅ Found syntax in attributes: {syntax[:50]}...")
            return syntax
        
        # Try to find in child elements
        syntax_elem = node.find(['pre', 'code'], class_='mermaid-syntax')
        if syntax_elem:
            logger.info(f"✅ Found syntax in child element: {syntax_elem.get_text()[:50]}...")
            return syntax_elem.get_text().strip()
        
        # Try to extract from text content
        text_content = node.get_text().strip()
        logger.info(f"🔍 Node text content: {text_content[:100]}...")
        
        if text_content and ('graph' in text_content or 'flowchart' in text_content or 'sequenceDiagram' in text_content):
            return text_content
        
        return ""
    
    def _extract_mermaid_title(self, node) -> str:
        """Extract Mermaid title from node"""
        # Try to extract from attributes
        title = node.get('title') or node.get('data-title')
        
        if title:
            return title
        
        # Try to find in child elements
        title_elem = node.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div'], class_='mermaid-title')
        if title_elem:
            return title_elem.get_text().strip()
        
        return ""
    
    async def _render_mermaid_to_svg(self, mermaid_syntax: str) -> str:
        """
        Render Mermaid syntax to SVG using Playwright
        
        Args:
            mermaid_syntax: Mermaid syntax string
            
        Returns:
            Rendered SVG string
        """
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Create HTML page containing Mermaid
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
                            width: 100%;
                            overflow: visible;
                        }}
                        svg {{
                            max-width: none !important;
                            width: auto !important;
                            height: auto !important;
                            display: block !important;
                            margin: 0 auto !important;
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
                            htmlLabels: false,
                            flowchart: {{
                                htmlLabels: false,
                                curve: 'basis',
                                useMaxWidth: false,
                                nodeSpacing: 30,
                                rankSpacing: 40,
                                padding: 10,
                                wrapping: false
                            }},
                            sequence: {{
                                htmlLabels: false
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
                
                # Wait for Mermaid rendering to complete
                await page.wait_for_timeout(2000)
                
                # Get rendered SVG
                svg_element = await page.query_selector('svg')
                if svg_element:
                    # Get the complete SVG element including opening/closing tags
                    svg_outer = await svg_element.evaluate('el => el.outerHTML')
                    
                    if svg_outer:
                        # Remove CSS animations that break PDF rendering
                        clean_svg = self._remove_css_animations(svg_outer)
                        # Remove foreignObject elements that cause PDF issues
                        pdf_compatible_svg = self._remove_foreign_objects(clean_svg)
                        # Apply explicit styling for PDF compatibility
                        styled_svg = self._apply_explicit_styling(pdf_compatible_svg)
                        # Ensure proper ViewBox for scaling
                        improved_svg = self._improve_svg_scaling(styled_svg)
                        await browser.close()
                        return improved_svg
                    else:
                        # Fallback: construct SVG from innerHTML and attributes
                        svg_content = await svg_element.inner_html()
                        svg_attrs = await svg_element.evaluate('el => el.getAttributeNames().map(name => `${name}="${el.getAttribute(name)}"`).join(" ")')
                        
                        complete_svg = f'<svg {svg_attrs}>{svg_content}</svg>'
                        clean_svg = self._remove_css_animations(complete_svg)
                        pdf_compatible_svg = self._remove_foreign_objects(clean_svg)
                        styled_svg = self._apply_explicit_styling(pdf_compatible_svg)
                        improved_svg = self._improve_svg_scaling(styled_svg)
                        await browser.close()
                        return improved_svg
                else:
                    logger.error("No rendered SVG element found")
                    await browser.close()
                    return ""
                    
        except Exception as e:
            logger.error(f"Mermaid rendering failed: {str(e)}")
            return ""
    
    def _create_svg_container(self, svg_content: str, title: str = "") -> str:
        """
        Create SVG container HTML
        
        Args:
            svg_content: SVG content
            title: Diagram title
            
        Returns:
            Wrapped HTML container
        """
        title_html = ""
        if title:
            title_html = f'<div class="mermaid-title" style="text-align: center; font-weight: bold; margin-bottom: 10px; font-size: 14px;">{title}</div>'
        
        return f'''
        <div class="mermaid-container" style="text-align: center; margin: 20px 0; page-break-inside: avoid; width: 100%; overflow: visible;">
            {title_html}
            <div class="mermaid-diagram" style="display: block; width: 100%; overflow: visible; text-align: center;">
                {svg_content}
            </div>
        </div>
        '''
    
    def _remove_css_animations(self, svg_content: str) -> str:
        """
        Remove CSS animations from SVG to resolve PDF rendering issues
        
        Args:
            svg_content: SVG content containing animations
            
        Returns:
            SVG content with animations removed
        """
        import re
        
        # Remove @keyframes animation definitions (comprehensive pattern)
        svg_content = re.sub(r'@keyframes[^}]*\{[^}]*\}', '', svg_content, flags=re.DOTALL)
        svg_content = re.sub(r'@-webkit-keyframes[^}]*\{[^}]*\}', '', svg_content, flags=re.DOTALL)
        
        # Remove all animation-related CSS properties
        svg_content = re.sub(r'animation[^;:]*:[^;]*;', '', svg_content)
        svg_content = re.sub(r'animation[^;:]*\s*:[^;]*;', '', svg_content)
        svg_content = re.sub(r'-webkit-animation[^;:]*:[^;]*;', '', svg_content)
        
        # Remove transition properties
        svg_content = re.sub(r'transition[^;:]*:[^;]*;', '', svg_content)
        svg_content = re.sub(r'-webkit-transition[^;:]*:[^;]*;', '', svg_content)
        
        # Remove stroke-dasharray and stroke-dashoffset animation properties
        svg_content = re.sub(r'stroke-dasharray[^;:]*:[^;]*;', '', svg_content)
        svg_content = re.sub(r'stroke-dashoffset[^;:]*:[^;]*;', '', svg_content)
        
        # Clean up excess whitespace and semicolons
        svg_content = re.sub(r'\s+', ' ', svg_content)
        svg_content = re.sub(r';\s*;', ';', svg_content)
        svg_content = re.sub(r'style\s*=\s*"[^"]*;"', lambda m: m.group(0).replace(';;', ';'), svg_content)
        
        logger.info("✅ Removed CSS animations and related properties from SVG")
        return svg_content
    
    def _remove_foreign_objects(self, svg_content: str) -> str:
        """
        Remove foreignObject elements from SVG to resolve PDF text rendering issues
        
        Args:
            svg_content: SVG content containing foreignObject elements
            
        Returns:
            SVG content with foreignObject elements removed
        """
        import re
        from bs4 import BeautifulSoup
        
        try:
            soup = BeautifulSoup(svg_content, 'html.parser')
            
            # Find all foreignObject elements
            foreign_objects = soup.find_all('foreignObject')
            
            if foreign_objects:
                logger.info(f"🔧 Found {len(foreign_objects)} foreignObject elements to remove")
                
                for foreign_obj in foreign_objects:
                    # Extract text content from HTML inside foreignObject
                    text_content = foreign_obj.get_text().strip()
                    
                    if text_content:
                        # Get position and size attributes
                        x = foreign_obj.get('x', '0')
                        y = foreign_obj.get('y', '0')
                        width = foreign_obj.get('width', '100')
                        height = foreign_obj.get('height', '20')
                        
                        # Create SVG text element to replace foreignObject
                        text_element = soup.new_tag('text')
                        # Center the text horizontally and vertically within the foreignObject bounds
                        text_element['x'] = str(float(x) + float(width) / 2)  # Center horizontally
                        text_element['y'] = str(float(y) + float(height) / 2)  # Center vertically
                        text_element['text-anchor'] = 'middle'
                        text_element['dominant-baseline'] = 'middle'
                        text_element['font-family'] = 'Arial, sans-serif'
                        text_element['font-size'] = '12px'
                        text_element['fill'] = '#000000'
                        text_element.string = text_content
                        
                        # Replace foreignObject with text element
                        foreign_obj.replace_with(text_element)
                        
                        logger.info(f"📝 Replaced foreignObject with text: '{text_content}'")
                    else:
                        # Remove empty foreignObject
                        foreign_obj.decompose()
                
                logger.info("✅ All foreignObject elements processed")
            else:
                logger.info("ℹ️  No foreignObject elements found")
            
            return str(soup)
            
        except Exception as e:
            logger.warning(f"foreignObject removal failed: {e}")
            return svg_content
    
    def _apply_explicit_styling(self, svg_content: str) -> str:
        """
        Apply explicit style attributes to SVG elements to ensure proper PDF rendering
        
        Args:
            svg_content: SVG content
            
        Returns:
            SVG content with explicit styling applied
        """
        from bs4 import BeautifulSoup
        
        try:
            soup = BeautifulSoup(svg_content, 'html.parser')
            
            # Find all rect elements in nodes (boxes)
            node_rects = soup.select('g.node rect.basic')
            
            if node_rects:
                logger.info(f"🎨 Applying explicit styling to {len(node_rects)} node rectangles")
                
                for rect in node_rects:
                    # Apply explicit fill and stroke for node boxes
                    rect['fill'] = '#ECECFF'  # Light blue background
                    rect['stroke'] = '#9370DB'  # Purple border
                    rect['stroke-width'] = '1px'
                    
                    logger.info(f"✅ Applied styling to rect: fill={rect.get('fill')}, stroke={rect.get('stroke')}")
            
            # Find all text elements and ensure they have proper styling
            text_elements = soup.find_all('text')
            
            if text_elements:
                logger.info(f"📝 Ensuring proper text styling for {len(text_elements)} text elements")
                
                for text_elem in text_elements:
                    # Ensure text has proper color and font
                    if not text_elem.get('fill'):
                        text_elem['fill'] = '#333333'  # Dark gray text
                    if not text_elem.get('font-family'):
                        text_elem['font-family'] = 'Arial, sans-serif'
                    if not text_elem.get('font-size'):
                        text_elem['font-size'] = '14px'
                    
                    # Ensure proper text centering for node labels
                    # Check if this text is inside a node label
                    node_label = text_elem.find_parent('g', class_='label')
                    if node_label and node_label.find_parent('g', class_='node'):
                        # This is a node label text - ensure it's centered
                        if not text_elem.get('text-anchor'):
                            text_elem['text-anchor'] = 'middle'
                        if not text_elem.get('dominant-baseline'):
                            text_elem['dominant-baseline'] = 'middle'
                        logger.info(f"📐 Applied centering to node label: '{text_elem.get_text()[:20]}...'")
                    
                    # Remove conflicting text-anchor from tspan elements
                    # Tspan elements should inherit centering from parent text element
                    tspans = text_elem.find_all('tspan')
                    for tspan in tspans:
                        # Remove text-anchor from tspan to prevent conflicts with parent
                        if tspan.get('text-anchor'):
                            del tspan['text-anchor']
                        # Don't force x position on tspan elements - let them position naturally
            
            # Find all arrow markers and ensure they're visible
            markers = soup.find_all('path', class_='arrowMarkerPath')
            
            if markers:
                logger.info(f"➤ Ensuring arrow visibility for {len(markers)} markers")
                
                for marker in markers:
                    if not marker.get('fill'):
                        marker['fill'] = '#000000'
                    if not marker.get('stroke'):
                        marker['stroke'] = '#000000'
            
            # Find all edge paths and ensure they're visible
            edges = soup.find_all('path', class_='flowchart-link')
            
            if edges:
                logger.info(f"↔ Ensuring edge visibility for {len(edges)} edges")
                
                for edge in edges:
                    if not edge.get('stroke'):
                        edge['stroke'] = '#000000'
                    if not edge.get('stroke-width'):
                        edge['stroke-width'] = '2px'
                    edge['fill'] = 'none'  # Ensure edges are not filled
            
            logger.info("✅ Explicit styling application completed")
            return str(soup)
            
        except Exception as e:
            logger.warning(f"Explicit styling application failed: {e}")
            return svg_content
    
    def _improve_svg_scaling(self, svg_content: str) -> str:
        """
        Improve SVG scaling support to ensure proper display in PDF
        
        Args:
            svg_content: SVG content
            
        Returns:
            Improved SVG content
        """
        import re
        from bs4 import BeautifulSoup
        
        try:
            soup = BeautifulSoup(svg_content, 'xml')
            svg_element = soup.find('svg')
            
            if svg_element:
                width = svg_element.get('width')
                height = svg_element.get('height')
                viewbox = svg_element.get('viewBox')
                
                # Convert width/height to numbers if they exist
                width_num = None
                height_num = None
                
                if width:
                    # Extract numeric value (remove px, %, etc.)
                    width_match = re.search(r'([\d.]+)', str(width))
                    if width_match:
                        width_num = float(width_match.group(1))
                        
                if height:
                    height_match = re.search(r'([\d.]+)', str(height))
                    if height_match:
                        height_num = float(height_match.group(1))
                
                # If no viewBox but we have width and height, create one
                if not viewbox and width_num and height_num:
                    viewbox = f"0 0 {width_num} {height_num}"
                    svg_element['viewBox'] = viewbox
                    logger.info(f"📐 Added viewBox: {viewbox}")
                
                # Ensure proper attributes for PDF scaling
                svg_element['preserveAspectRatio'] = 'xMidYMid meet'
                
                # Remove fixed width/height to allow responsive scaling
                if svg_element.get('width'):
                    del svg_element['width']
                if svg_element.get('height'):
                    del svg_element['height']
                
                # Add CSS for proper scaling
                style_tag = soup.find('style')
                if not style_tag:
                    style_tag = soup.new_tag('style')
                    svg_element.insert(0, style_tag)
                
                # Ensure style content exists
                current_style = style_tag.string or ""
                scaling_css = """
                svg { 
                    width: 100%; 
                    height: auto; 
                    max-width: 100%; 
                    display: block; 
                }
                """
                
                if scaling_css not in current_style:
                    style_tag.string = current_style + scaling_css
                
                logger.info("✅ SVG scaling improvements applied")
                return str(soup)
            
        except Exception as e:
            logger.warning(f"SVG scaling improvement failed: {e}")
        
        return svg_content