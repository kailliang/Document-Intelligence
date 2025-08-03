#!/usr/bin/env python3
"""
Test script to validate the styling fix for black box backgrounds
"""

import asyncio
import sys
from pathlib import Path

# Add server directory to path
sys.path.append(str(Path(__file__).parent / 'server'))

from bs4 import BeautifulSoup
from server.app.internal.mermaid_render import MermaidRenderer

async def test_styling_fix():
    """Test the explicit styling fix"""
    
    print("🎨 Testing Explicit Styling Fix")
    print("=" * 40)
    
    # The problematic diagram
    problematic_syntax = """flowchart TD
    A[Wireless Optogenetic Device] --> B[Body]
    A --> C[Device Configuration]
    A --> D[Sealed Enclosure]
    B --> E[Light Transducing Materials]
    C --> F[Tapered Design]
    C --> G[Multiple Optical Windows]
    E --> H[Lanthanide-doped Nanoparticles]"""
    
    renderer = MermaidRenderer()
    
    try:
        print("🎨 Rendering with explicit styling...")
        svg_result = await renderer._render_mermaid_to_svg(problematic_syntax)
        
        if svg_result:
            print(f"✅ SVG rendering successful (length: {len(svg_result)} chars)")
            
            # Parse SVG to check explicit styling
            soup = BeautifulSoup(svg_result, 'html.parser')
            
            # Check node rectangles
            node_rects = soup.select('g.node rect.basic')
            print(f"📦 Found {len(node_rects)} node rectangles")
            
            properly_styled_rects = 0
            for i, rect in enumerate(node_rects):
                fill = rect.get('fill')
                stroke = rect.get('stroke')
                stroke_width = rect.get('stroke-width')
                
                print(f"   Rect {i+1}: fill='{fill}', stroke='{stroke}', stroke-width='{stroke_width}'")
                
                if fill == '#ECECFF' and stroke == '#9370DB':
                    properly_styled_rects += 1
            
            if properly_styled_rects == len(node_rects):
                print("✅ All rectangles have explicit styling!")
            else:
                print(f"⚠️  Only {properly_styled_rects}/{len(node_rects)} rectangles properly styled")
            
            # Check text elements
            text_elements = soup.find_all('text')
            print(f"📝 Found {len(text_elements)} text elements")
            
            properly_styled_text = 0
            for i, text_elem in enumerate(text_elements[:5]):  # Check first 5
                fill = text_elem.get('fill')
                font_family = text_elem.get('font-family')
                font_size = text_elem.get('font-size')
                text_content = text_elem.get_text().strip()
                
                print(f"   Text {i+1}: '{text_content[:20]}...' fill='{fill}', font='{font_family}', size='{font_size}'")
                
                if fill and 'Arial' in (font_family or ''):
                    properly_styled_text += 1
            
            if properly_styled_text > 0:
                print(f"✅ {properly_styled_text} text elements have explicit styling")
            
            # Check arrow markers
            markers = soup.find_all('path', class_='arrowMarkerPath')
            print(f"➤ Found {len(markers)} arrow markers")
            
            if markers:
                marker = markers[0]
                fill = marker.get('fill')
                stroke = marker.get('stroke')
                print(f"   Marker styling: fill='{fill}', stroke='{stroke}'")
                
                if fill and stroke:
                    print("✅ Markers have explicit styling")
            
            # Check edges
            edges = soup.find_all('path', class_='flowchart-link')
            print(f"↔ Found {len(edges)} flowchart edges")
            
            if edges:
                edge = edges[0]
                stroke = edge.get('stroke')
                stroke_width = edge.get('stroke-width')
                fill = edge.get('fill')
                print(f"   Edge styling: stroke='{stroke}', width='{stroke_width}', fill='{fill}'")
                
                if stroke and fill == 'none':
                    print("✅ Edges have explicit styling")
            
            # Save styled SVG for inspection
            with open("debug_styled_diagram.svg", "w", encoding="utf-8") as f:
                f.write(svg_result)
            print("💾 Styled SVG saved as: debug_styled_diagram.svg")
            
            # Test complete processing
            print("\n🔄 Testing complete processing pipeline...")
            test_html = f'''
            <div data-type="mermaid-diagram" class="mermaid-node" data-syntax="{problematic_syntax}" data-title="Device Structure">
                <div class="mermaid-title">Device Structure</div>
                <div class="mermaid-diagram"><!-- rendered content --></div>
            </div>
            '''
            
            processed_html = await renderer.process_html(test_html)
            
            if '<svg' in processed_html:
                print("✅ Complete processing successful")
                
                # Check final processed HTML for explicit styling
                final_soup = BeautifulSoup(processed_html, 'html.parser')
                final_rects = final_soup.select('g.node rect.basic')
                
                if final_rects:
                    sample_rect = final_rects[0]
                    final_fill = sample_rect.get('fill')
                    final_stroke = sample_rect.get('stroke')
                    
                    print(f"📋 Final HTML rect styling: fill='{final_fill}', stroke='{final_stroke}'")
                    
                    if final_fill == '#ECECFF':
                        print("🎉 SUCCESS: Rectangles have proper background in final output!")
                    else:
                        print(f"⚠️  Final output still has issues: fill='{final_fill}'")
                else:
                    print("❌ No rectangles found in final output")
            else:
                print("❌ Complete processing failed")
                
        else:
            print("❌ SVG rendering failed")
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_styling_fix())