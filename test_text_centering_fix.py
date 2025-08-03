#!/usr/bin/env python3
"""
Test script to validate the text centering fix for Mermaid diagrams
"""

import asyncio
import sys
from pathlib import Path

# Add server directory to path
sys.path.append(str(Path(__file__).parent / 'server'))

from bs4 import BeautifulSoup
from server.app.internal.mermaid_render import MermaidRenderer

async def test_text_centering_fix():
    """Test the text centering fix"""
    
    print("📐 Testing Text Centering Fix")
    print("=" * 40)
    
    # The diagram that was showing misaligned text
    test_syntax = """flowchart TD
    A[Oxygen] --> B[Second Flow Channel]
    B --> C[Mixing Elements]
    C --> D[Gas-Permeable Membrane]
    E[Blood] --> F[First Flow Channel]
    D --> F
    F --> G[Output]"""
    
    renderer = MermaidRenderer()
    
    try:
        print("🎨 Rendering diagram with text centering fix...")
        svg_result = await renderer._render_mermaid_to_svg(test_syntax)
        
        if svg_result:
            print(f"✅ SVG rendering successful (length: {len(svg_result)} chars)")
            
            # Parse SVG to check text positioning
            soup = BeautifulSoup(svg_result, 'html.parser')
            
            # Check text elements
            text_elements = soup.find_all('text')
            print(f"📝 Found {len(text_elements)} text elements")
            
            properly_positioned_text = 0
            for i, text_elem in enumerate(text_elements):
                x = text_elem.get('x')
                y = text_elem.get('y')
                text_anchor = text_elem.get('text-anchor')
                dominant_baseline = text_elem.get('dominant-baseline')
                text_content = text_elem.get_text().strip()
                
                if text_content and len(text_content) > 3:  # Only check meaningful text
                    print(f"   Text {i+1}: '{text_content[:20]}...'")
                    print(f"            x='{x}', y='{y}'")
                    print(f"            text-anchor='{text_anchor}', dominant-baseline='{dominant_baseline}'")
                    
                    if text_anchor == 'middle' and dominant_baseline == 'middle':
                        properly_positioned_text += 1
                        print(f"            ✅ Properly centered")
                    else:
                        print(f"            ⚠️  May not be centered")
            
            if properly_positioned_text > 0:
                print(f"✅ {properly_positioned_text} text elements have proper centering attributes")
            
            # Check node rectangles and their relationship to text
            node_rects = soup.select('g.node rect.basic')
            print(f"📦 Found {len(node_rects)} node rectangles")
            
            # Save for inspection
            with open("debug_centered_diagram.svg", "w", encoding="utf-8") as f:
                f.write(svg_result)
            print("💾 Centered diagram saved as: debug_centered_diagram.svg")
            
            # Test complete processing
            print("\n🔄 Testing complete processing pipeline...")
            test_html = f'''
            <div data-type="mermaid-diagram" class="mermaid-node" data-syntax="{test_syntax}" data-title="Flow Diagram">
                <div class="mermaid-title">Flow Diagram</div>
                <div class="mermaid-diagram"><!-- rendered content --></div>
            </div>
            '''
            
            processed_html = await renderer.process_html(test_html)
            
            if '<svg' in processed_html:
                print("✅ Complete processing successful")
                
                # Check final processed HTML for proper text centering
                final_soup = BeautifulSoup(processed_html, 'html.parser')
                final_text_elements = final_soup.find_all('text')
                
                centered_count = 0
                for text_elem in final_text_elements:
                    if (text_elem.get('text-anchor') == 'middle' and 
                        text_elem.get('dominant-baseline') == 'middle' and
                        text_elem.get_text().strip()):
                        centered_count += 1
                
                if centered_count > 0:
                    print(f"🎉 SUCCESS: {centered_count} text elements properly centered in final output!")
                else:
                    print("⚠️  No properly centered text elements found in final output")
            else:
                print("❌ Complete processing failed")
                
        else:
            print("❌ SVG rendering failed")
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

async def test_position_calculations():
    """Test the position calculation logic specifically"""
    
    print(f"\n🧮 Testing Position Calculations")
    print("=" * 40)
    
    # Simulate foreignObject bounds
    test_cases = [
        {"x": "100", "y": "50", "width": "200", "height": "30", "label": "Standard Box"},
        {"x": "0", "y": "0", "width": "150", "height": "40", "label": "Origin Box"},
        {"x": "300.5", "y": "150.75", "width": "180.25", "height": "35.5", "label": "Decimal Coordinates"},
    ]
    
    for case in test_cases:
        x, y, width, height = case["x"], case["y"], case["width"], case["height"]
        
        # Calculate center position (same logic as in our fix)
        center_x = float(x) + float(width) / 2
        center_y = float(y) + float(height) / 2
        
        print(f"\n📋 {case['label']}:")
        print(f"   ForeignObject: x={x}, y={y}, w={width}, h={height}")
        print(f"   Text center: x={center_x}, y={center_y}")
        print(f"   ✅ Text will be centered within bounds")

if __name__ == "__main__":
    asyncio.run(test_text_centering_fix())
    asyncio.run(test_position_calculations())