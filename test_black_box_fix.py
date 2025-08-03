#!/usr/bin/env python3
"""
Test script to validate the black box issue fix
"""

import asyncio
import sys
from pathlib import Path

# Add server directory to path
sys.path.append(str(Path(__file__).parent / 'server'))

from server.app.internal.mermaid_render import MermaidRenderer

async def test_black_box_fix():
    """Test the specific diagram that was showing black boxes"""
    
    print("🔧 Testing Black Box Issue Fix")
    print("=" * 40)
    
    # The exact problematic diagram from the user's example
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
        print("🎨 Rendering problematic diagram...")
        svg_result = await renderer._render_mermaid_to_svg(problematic_syntax)
        
        if svg_result:
            print(f"✅ SVG rendering successful (length: {len(svg_result)} chars)")
            
            # Check for foreignObject elements (should be 0 after fix)
            foreign_object_count = svg_result.count('<foreignObject')
            print(f"🏷️  ForeignObject elements: {foreign_object_count}")
            
            if foreign_object_count == 0:
                print("✅ No foreignObject elements - PDF should render correctly!")
            else:
                print(f"⚠️  Still has {foreign_object_count} foreignObject elements")
            
            # Check for SVG text elements (should have them)
            text_element_count = svg_result.count('<text')
            print(f"📝 SVG text elements: {text_element_count}")
            
            if text_element_count > 0:
                print("✅ Has SVG text elements - labels should display correctly!")
            else:
                print("❌ No SVG text elements found - labels may not display")
            
            # Check for HTML content (should be minimal)
            html_indicators = ['<div', '<span', 'xmlns="http://www.w3.org/1999/xhtml"']
            html_found = []
            for indicator in html_indicators:
                if indicator in svg_result:
                    html_found.append(indicator)
            
            if html_found:
                print(f"⚠️  HTML content found: {html_found}")
            else:
                print("✅ No problematic HTML content detected!")
            
            # Save for inspection
            with open("debug_fixed_diagram.svg", "w", encoding="utf-8") as f:
                f.write(svg_result)
            print("💾 Fixed SVG saved as: debug_fixed_diagram.svg")
            
            # Test complete processing pipeline
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
                
                # Check processed HTML for foreignObject
                processed_foreign_objects = processed_html.count('<foreignObject')
                print(f"📋 ForeignObjects in final HTML: {processed_foreign_objects}")
                
                if processed_foreign_objects == 0:
                    print("🎉 SUCCESS: No foreignObject elements in final output!")
                else:
                    print(f"⚠️  Still has {processed_foreign_objects} foreignObject in final output")
            else:
                print("❌ Complete processing failed")
                
        else:
            print("❌ SVG rendering failed")
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

async def test_various_diagram_types():
    """Test various diagram types to ensure fix doesn't break anything"""
    
    print(f"\n🧪 Testing Various Diagram Types")
    print("=" * 40)
    
    test_diagrams = [
        {
            "name": "Simple Flowchart",
            "syntax": "flowchart LR; A[Start] --> B[End]"
        },
        {
            "name": "Sequence Diagram",
            "syntax": "sequenceDiagram; A->>B: Hello; B->>A: World"
        },
        {
            "name": "Complex Flowchart",
            "syntax": """flowchart TD
            A[Input] --> B{Decision}
            B -->|Yes| C[Process A]
            B -->|No| D[Process B]
            C --> E[Output]
            D --> E"""
        }
    ]
    
    renderer = MermaidRenderer()
    
    for test in test_diagrams:
        print(f"\n📋 Testing: {test['name']}")
        try:
            svg_result = await renderer._render_mermaid_to_svg(test['syntax'])
            
            if svg_result:
                foreign_objects = svg_result.count('<foreignObject')
                text_elements = svg_result.count('<text')
                
                print(f"   ForeignObjects: {foreign_objects}")
                print(f"   Text elements: {text_elements}")
                
                if foreign_objects == 0 and text_elements > 0:
                    print("   ✅ PASS: Clean SVG output")
                else:
                    print("   ⚠️  May have issues")
            else:
                print("   ❌ Rendering failed")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_black_box_fix())
    asyncio.run(test_various_diagram_types())