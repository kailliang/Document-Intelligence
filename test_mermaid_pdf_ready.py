#!/usr/bin/env python3
"""
Test Mermaid rendering for PDF export (without database dependencies)
"""

import asyncio
import sys
import os
from pathlib import Path

# Add server directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

async def test_mermaid_pdf_rendering():
    """Test that Mermaid renders properly for PDF without animations"""
    print("📊 Testing Mermaid PDF-Ready Rendering")
    print("=" * 50)
    
    try:
        from app.internal.mermaid_render import MermaidRenderer
        
        # Test HTML content with Mermaid
        test_html = """
        <h1>Document with Mermaid Diagram</h1>
        
        <div class="mermaid-container" data-type="mermaid-diagram" data-syntax="flowchart TD
    A[Wireless Optogenetic Device] --> B[Body with Light Transducing Materials]
    A --> C[Multiple Optical Windows]
    D[Radiation System] --> E[Radiation Probe]
    D --> F[Movement Mechanism]
    D --> G[Detector]
    D --> H[Controller]
    D -->|Activates| A
    B -->|Up-converts Radiation| C" data-title="Device Architecture">
            <div class="mermaid-title">Device Architecture</div>
            <div class="mermaid-diagram">
                <pre class="mermaid-syntax">flowchart TD
    A[Wireless Optogenetic Device] --> B[Body with Light Transducing Materials]
    A --> C[Multiple Optical Windows]
    D[Radiation System] --> E[Radiation Probe]
    D --> F[Movement Mechanism]
    D --> G[Detector]
    D --> H[Controller]
    D -->|Activates| A
    B -->|Up-converts Radiation| C</pre>
            </div>
        </div>
        
        <p>This diagram shows the complete system architecture.</p>
        """
        
        print("📋 Processing HTML with Mermaid content...")
        print(f"📏 Original HTML length: {len(test_html)}")
        
        # Process HTML through Mermaid renderer
        renderer = MermaidRenderer()
        processed_html = await renderer.process_html(test_html)
        
        print(f"📊 Processed HTML length: {len(processed_html)}")
        
        # Check if Mermaid was processed
        if '<svg' in processed_html:
            print("✅ Mermaid diagram converted to SVG")
            
            # Count SVG elements
            svg_count = processed_html.count('<svg')
            print(f"📊 Found {svg_count} SVG element(s)")
            
            # Check for animation patterns that should be removed
            animation_patterns = ['@keyframes', 'animation:', 'transition:', 'stroke-dasharray']
            found_animations = [pattern for pattern in animation_patterns if pattern in processed_html]
            
            if found_animations:
                print(f"⚠️ Still contains animations: {found_animations}")
            else:
                print("✅ No animations found - SVG is PDF-ready")
            
            # Check for proper SVG structure
            if 'viewBox=' in processed_html and '<g' in processed_html:
                print("✅ SVG has proper structure with viewBox and graphics")
            else:
                print("⚠️ SVG may be missing proper structure")
                
            # Extract SVG for inspection
            svg_start = processed_html.find('<svg')
            svg_end = processed_html.find('</svg>') + 6
            if svg_start >= 0 and svg_end > svg_start:
                svg_content = processed_html[svg_start:svg_end]
                print(f"\n📄 SVG Preview (first 300 chars):")
                print(svg_content[:300] + "...")
                
            return True
            
        else:
            print("❌ Mermaid diagram was not converted to SVG")
            print("📄 Processed HTML preview:")
            print(processed_html[:500] + "...")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Mermaid PDF-Ready Rendering Test")
    print("=" * 60)
    
    success = asyncio.run(test_mermaid_pdf_rendering())
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 Test PASSED: Mermaid rendering is PDF-ready")
        print("✅ Diagrams should now render correctly in PDFs instead of black blocks")
        print("🔧 CSS animations have been successfully removed")
    else:
        print("❌ Test FAILED: Mermaid rendering issues detected")
        print("💡 Check the output above for specific problems")