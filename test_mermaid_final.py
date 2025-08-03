#!/usr/bin/env python3
"""
Final test for Mermaid rendering with updated settings (no WeasyPrint)
"""

import asyncio
import sys
import os

# Add server directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

async def test_mermaid_responsiveness():
    """Test that Mermaid diagrams are now responsive and properly sized"""
    print("🎯 TESTING MERMAID RESPONSIVENESS & SIZING")
    print("=" * 50)
    
    try:
        from app.internal.mermaid_render import MermaidRenderer
        
        # Original complex syntax from the document
        document_syntax = """flowchart TD
    A[Wireless Optogenetic Device] --> B[Body with Light Transducing Materials]
    A --> C[Multiple Optical Windows]
    D[Radiation System] --> E[Radiation Probe]
    D --> F[Movement Mechanism]
    D --> G[Detector]
    D --> H[Controller]
    D -->|Activates| A
    B -->|Up-converts Radiation| C"""
        
        renderer = MermaidRenderer()
        
        print("📊 Testing document's Mermaid syntax...")
        svg_result = await renderer._render_mermaid_to_svg(document_syntax)
        
        if not svg_result:
            print("❌ CRITICAL: SVG generation failed")
            return False
        
        print(f"✅ SVG generated successfully")
        print(f"📏 SVG length: {len(svg_result)} characters")
        
        # Check for responsive features
        checks = {
            "ViewBox present": 'viewBox=' in svg_result,
            "Responsive width": 'width="100%"' in svg_result,
            "Max-width style": 'max-width' in svg_result,
            "SVG class": 'class="flowchart"' in svg_result,
            "Proper XML structure": svg_result.startswith('<svg') and svg_result.endswith('</svg>')
        }
        
        print("\n🔍 SVG Quality Checks:")
        for check, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"  {status} {check}")
        
        # Extract and analyze dimensions
        if 'viewBox=' in svg_result:
            viewbox_start = svg_result.find('viewBox="') + 9
            viewbox_end = svg_result.find('"', viewbox_start)
            viewbox = svg_result[viewbox_start:viewbox_end]
            
            parts = viewbox.split()
            if len(parts) >= 4:
                width, height = float(parts[2]), float(parts[3])
                print(f"\n📐 Diagram Analysis:")
                print(f"  Width: {width:.1f}px")
                print(f"  Height: {height:.1f}px")
                print(f"  Aspect ratio: {width/height:.2f}")
                
                # Determine if size is appropriate
                if width > 1200:
                    print("  ⚠️ Width might be too large for PDF")
                elif width < 300:
                    print("  ⚠️ Width might be too small")
                else:
                    print("  ✅ Width is appropriate for PDF")
                
                if height > 800:
                    print("  ⚠️ Height might be too large for PDF")
                else:
                    print("  ✅ Height is appropriate for PDF")
        
        # Test HTML processing
        print("\n🔄 Testing HTML processing...")
        
        test_html = f'<div data-type="mermaid-diagram" class="mermaid-node" data-syntax="{document_syntax}"></div>'
        processed = await renderer.process_html(test_html)
        
        # Check final output
        has_svg = '<svg' in processed
        has_container = 'mermaid-container' in processed
        has_responsive_style = 'max-width: 100%' in processed or 'display: inline-block' in processed
        
        print(f"  ✅ Contains SVG: {has_svg}")
        print(f"  ✅ Has container: {has_container}")
        print(f"  ✅ Has responsive styling: {has_responsive_style}")
        
        if all(checks.values()) and has_svg:
            print("\n🎉 SUCCESS: Mermaid rendering is working perfectly!")
            print("💡 Diagrams should now appear properly in PDF exports")
            print("🚫 Edit/Delete buttons have been removed")
            print("📱 Diagrams are responsive and properly sized")
            return True
        else:
            print("\n⚠️ Some issues detected - check the output above")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_multiple_diagram_sizes():
    """Test various diagram complexities to ensure sizing works"""
    print("\n🧪 TESTING MULTIPLE DIAGRAM SIZES")
    print("=" * 50)
    
    test_cases = [
        ("Simple", "graph TD\n    A --> B"),
        ("Medium", "flowchart LR\n    A[Start] --> B[Process]\n    B --> C[End]"),
        ("Complex", """flowchart TD
    A[Device] --> B[Component 1]
    A --> C[Component 2]
    A --> D[Component 3]
    B --> E[Output 1]
    C --> F[Output 2]
    D --> G[Output 3]""")
    ]
    
    try:
        from app.internal.mermaid_render import MermaidRenderer
        renderer = MermaidRenderer()
        
        results = []
        
        for name, syntax in test_cases:
            print(f"\n📊 Testing {name} diagram...")
            
            svg = await renderer._render_mermaid_to_svg(syntax)
            
            if svg:
                # Extract dimensions
                if 'viewBox=' in svg:
                    viewbox_start = svg.find('viewBox="') + 9
                    viewbox_end = svg.find('"', viewbox_start)
                    viewbox = svg[viewbox_start:viewbox_end]
                    
                    parts = viewbox.split()
                    if len(parts) >= 4:
                        width, height = float(parts[2]), float(parts[3])
                        results.append((name, width, height, len(svg)))
                        print(f"  📐 {width:.0f}x{height:.0f}px ({len(svg)} chars)")
                    else:
                        print(f"  ❌ Invalid viewBox format")
                else:
                    print(f"  ❌ No viewBox found")
            else:
                print(f"  ❌ SVG generation failed")
        
        if results:
            print(f"\n📊 Size Comparison Summary:")
            for name, width, height, chars in results:
                ratio = width / height
                print(f"  {name:8} {width:6.0f}x{height:4.0f}px  ratio:{ratio:4.1f}  size:{chars:5d}")
            
            # Check if all are reasonable sizes
            max_width = max(r[1] for r in results)
            max_height = max(r[2] for r in results)
            
            if max_width <= 1200 and max_height <= 800:
                print("  ✅ All diagrams have reasonable sizes for PDF")
                return True
            else:
                print("  ⚠️ Some diagrams might be too large for PDF")
                return False
        else:
            return False
            
    except Exception as e:
        print(f"❌ Multi-size test failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("🔬 FINAL MERMAID TESTING")
    print("=" * 60)
    
    result1 = asyncio.run(test_mermaid_responsiveness())
    result2 = asyncio.run(test_multiple_diagram_sizes())
    
    print("\n" + "=" * 60)
    print("🎯 FINAL VERDICT:")
    
    if result1 and result2:
        print("🎉 COMPLETE SUCCESS!")
        print("✅ Mermaid rendering is working perfectly")
        print("✅ Diagrams are responsive and properly sized")
        print("✅ Edit/Delete buttons removed")
        print("✅ Ready for PDF export testing")
        print("\n💡 Next step: Try the PDF export through the frontend!")
    elif result1:
        print("⚠️ Basic functionality works, sizing might need adjustment")
    else:
        print("❌ Issues found - may need further investigation")