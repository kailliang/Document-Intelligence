#!/usr/bin/env python3
"""
Test script to validate the text overlap fix for Mermaid diagrams
"""

import asyncio
import sys
from pathlib import Path

# Add server directory to path
sys.path.append(str(Path(__file__).parent / 'server'))

from bs4 import BeautifulSoup
from server.app.internal.mermaid_render import MermaidRenderer

async def test_text_overlap_fix():
    """Test the text overlap fix with the problematic diagram"""
    
    print("🔀 Testing Text Overlap Fix")
    print("=" * 40)
    
    # The diagram that was showing overlapping text
    problematic_syntax = """flowchart TD
    A[Substrate] --> B[First Channel]
    C[Eluent] --> D[Second Channel]
    A --> D
    C --> B
    B --> E[Gas-Permeable Membrane]
    D --> E"""
    
    renderer = MermaidRenderer()
    
    try:
        print("🎨 Rendering diagram with overlap fix...")
        svg_result = await renderer._render_mermaid_to_svg(problematic_syntax)
        
        if svg_result:
            print(f"✅ SVG rendering successful (length: {len(svg_result)} chars)")
            
            # Parse SVG to check text structure
            soup = BeautifulSoup(svg_result, 'html.parser')
            
            # Check text elements
            text_elements = soup.find_all('text')
            print(f"📝 Found {len(text_elements)} text elements")
            
            overlapping_issues = 0
            for i, text_elem in enumerate(text_elements):
                text_anchor = text_elem.get('text-anchor')
                dominant_baseline = text_elem.get('dominant-baseline')
                text_content = text_elem.get_text().strip()
                
                if text_content and len(text_content) > 3:  # Only check meaningful text
                    print(f"   Text {i+1}: '{text_content}'")
                    print(f"            text-anchor='{text_anchor}', dominant-baseline='{dominant_baseline}'")
                    
                    # Check tspan elements within this text
                    tspans = text_elem.find_all('tspan')
                    print(f"            Contains {len(tspans)} tspan elements")
                    
                    for j, tspan in enumerate(tspans):
                        tspan_anchor = tspan.get('text-anchor')
                        tspan_x = tspan.get('x')
                        tspan_content = tspan.get_text().strip()
                        
                        print(f"               Tspan {j+1}: '{tspan_content}' text-anchor='{tspan_anchor}' x='{tspan_x}'")
                        
                        # Check for problematic tspan text-anchor that could cause overlap
                        if tspan_anchor == 'middle' and text_anchor == 'middle':
                            overlapping_issues += 1
                            print(f"               ⚠️  POTENTIAL OVERLAP: Both parent and tspan have text-anchor='middle'")
                        elif tspan_anchor is None:
                            print(f"               ✅ Good: tspan inherits from parent")
            
            if overlapping_issues == 0:
                print("✅ No text overlap issues detected!")
            else:
                print(f"⚠️  Found {overlapping_issues} potential overlap issues")
            
            # Save for inspection
            with open("debug_overlap_fixed_diagram.svg", "w", encoding="utf-8") as f:
                f.write(svg_result)
            print("💾 Overlap-fixed diagram saved as: debug_overlap_fixed_diagram.svg")
            
            # Test complete processing
            print("\n🔄 Testing complete processing pipeline...")
            test_html = f'''
            <div data-type="mermaid-diagram" class="mermaid-node" data-syntax="{problematic_syntax}" data-title="Flow System">
                <div class="mermaid-title">Flow System</div>
                <div class="mermaid-diagram"><!-- rendered content --></div>
            </div>
            '''
            
            processed_html = await renderer.process_html(test_html)
            
            if '<svg' in processed_html:
                print("✅ Complete processing successful")
                
                # Check final processed HTML for text overlap issues
                final_soup = BeautifulSoup(processed_html, 'html.parser')
                final_text_elements = final_soup.find_all('text')
                
                final_overlap_issues = 0
                for text_elem in final_text_elements:
                    if text_elem.get('text-anchor') == 'middle':
                        tspans_with_anchor = text_elem.find_all('tspan', attrs={'text-anchor': 'middle'})
                        if tspans_with_anchor:
                            final_overlap_issues += len(tspans_with_anchor)
                
                if final_overlap_issues == 0:
                    print("🎉 SUCCESS: No text overlap issues in final output!")
                else:
                    print(f"⚠️  Still has {final_overlap_issues} potential overlap issues in final output")
            else:
                print("❌ Complete processing failed")
                
        else:
            print("❌ SVG rendering failed")
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

async def test_simple_case():
    """Test a simple case to ensure basic functionality still works"""
    
    print(f"\n🧪 Testing Simple Case")
    print("=" * 40)
    
    simple_syntax = "flowchart LR; A[Start] --> B[End]"
    
    renderer = MermaidRenderer()
    
    try:
        svg_result = await renderer._render_mermaid_to_svg(simple_syntax)
        
        if svg_result:
            soup = BeautifulSoup(svg_result, 'html.parser')
            text_elements = soup.find_all('text')
            
            for text_elem in text_elements:
                text_content = text_elem.get_text().strip()
                if text_content in ['Start', 'End']:
                    text_anchor = text_elem.get('text-anchor')
                    tspans = text_elem.find_all('tspan')
                    tspan_anchors = [t.get('text-anchor') for t in tspans]
                    
                    print(f"   '{text_content}': text-anchor='{text_anchor}'")
                    print(f"                   tspan anchors: {tspan_anchors}")
                    
                    if text_anchor == 'middle' and all(a is None for a in tspan_anchors):
                        print(f"                   ✅ Properly configured")
                    else:
                        print(f"                   ⚠️  May have issues")
            
            print("✅ Simple case completed")
        else:
            print("❌ Simple case failed")
            
    except Exception as e:
        print(f"❌ Simple case error: {e}")

if __name__ == "__main__":
    asyncio.run(test_text_overlap_fix())
    asyncio.run(test_simple_case())