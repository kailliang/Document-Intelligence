#!/usr/bin/env python3
"""
Test the MermaidRenderer fix in isolation
"""

import asyncio
import sys
import os

# Add server directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

# The exact syntax from the document
REAL_MERMAID_SYNTAX = """flowchart TD
    A[Wireless Optogenetic Device] --> B[Body with Light Transducing Materials]
    A --> C[Multiple Optical Windows]
    D[Radiation System] --> E[Radiation Probe]
    D --> F[Movement Mechanism]
    D --> G[Detector]
    D --> H[Controller]
    D -->|Activates| A
    B -->|Up-converts Radiation| C"""

async def test_mermaid_renderer_fix():
    """Test the fixed MermaidRenderer"""
    print("🔧 Testing MermaidRenderer Fix")
    print("=" * 40)
    
    try:
        from app.internal.mermaid_render import MermaidRenderer
        
        renderer = MermaidRenderer()
        
        print("📊 Testing SVG rendering with fixed method...")
        svg_result = await renderer._render_mermaid_to_svg(REAL_MERMAID_SYNTAX)
        
        if svg_result:
            print(f"✅ SVG generation successful!")
            print(f"📏 SVG length: {len(svg_result)}")
            print(f"🔍 SVG preview: {svg_result[:200]}...")
            
            # Verify it's valid SVG
            if svg_result.startswith('<svg') and svg_result.endswith('</svg>'):
                print("✅ Valid SVG structure")
                return True
            else:
                print("❌ Invalid SVG structure")
                return False
        else:
            print("❌ SVG generation failed")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_full_html_processing():
    """Test processing HTML with the Mermaid diagram"""
    print("\n🔧 Testing Full HTML Processing")
    print("=" * 40)
    
    # Simple HTML with Mermaid
    test_html = f'''<div data-type="mermaid-diagram" class="mermaid-node" data-syntax="{REAL_MERMAID_SYNTAX}"></div>'''
    
    try:
        from app.internal.mermaid_render import MermaidRenderer
        
        renderer = MermaidRenderer()
        
        print("📊 Processing HTML with Mermaid...")
        processed_html = await renderer.process_html(test_html)
        
        svg_count = processed_html.count('<svg')
        
        print(f"📏 Processed HTML length: {len(processed_html)}")
        print(f"📊 SVG elements found: {svg_count}")
        
        if svg_count > 0:
            print("✅ HTML processing successful!")
            print(f"🔍 Processed HTML preview: {processed_html[:300]}...")
            return True
        else:
            print("❌ No SVG elements in processed HTML")
            print(f"🔍 Processed HTML: {processed_html}")
            return False
            
    except Exception as e:
        print(f"❌ HTML processing failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 TESTING MERMAIDRENDERER FIX")
    print("=" * 50)
    
    result1 = asyncio.run(test_mermaid_renderer_fix())
    result2 = asyncio.run(test_full_html_processing())
    
    print("\n" + "=" * 50)
    if result1 and result2:
        print("🎉 SUCCESS: MermaidRenderer fix works perfectly!")
        print("💡 The PDF export issue might be elsewhere now.")
    elif result1:
        print("⚠️ SVG generation works, but HTML processing fails")
    else:
        print("❌ FAILURE: SVG generation still broken")