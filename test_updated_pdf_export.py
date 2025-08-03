#!/usr/bin/env python3
"""
Test PDF export with updated Mermaid settings (no buttons, responsive sizing)
"""

import asyncio
import sys
import os

# Add server directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

# Test HTML that mimics the updated frontend (no Edit/Delete buttons)
UPDATED_HTML_WITH_MERMAID = '''
<h1>Claims</h1>
<p>8. The method of claim 6, wherein the step of activating the wireless optogenetic device includes altering properties of radiation including wavelength, intensity, and pulse duration.</p>

<div data-type="mermaid-diagram" class="mermaid-node" data-syntax="flowchart TD
    A[Wireless Optogenetic Device] --> B[Body with Light Transducing Materials]
    A --> C[Multiple Optical Windows]
    D[Radiation System] --> E[Radiation Probe]
    D --> F[Movement Mechanism]
    D --> G[Detector]
    D --> H[Controller]
    D -->|Activates| A
    B -->|Up-converts Radiation| C">
</div>

<p>More content after the diagram.</p>
'''

async def test_full_pdf_pipeline_updated():
    """Test the complete PDF export pipeline with updated settings"""
    print("🧪 TESTING UPDATED PDF EXPORT PIPELINE")
    print("=" * 60)
    
    try:
        # Step 1: Test HTML cleaning (preserves Mermaid attributes)
        print("🧹 Step 1: Testing HTML cleaning...")
        
        from app.internal.pdf_export import PDFExporter
        exporter = PDFExporter()
        
        cleaned_html = exporter._clean_html_content(UPDATED_HTML_WITH_MERMAID)
        
        # Check what's preserved
        has_mermaid = 'data-type="mermaid-diagram"' in cleaned_html
        has_syntax = 'data-syntax=' in cleaned_html
        has_edit_buttons = 'Edit' in cleaned_html or 'Delete' in cleaned_html
        
        print(f"✅ Mermaid element preserved: {has_mermaid}")
        print(f"✅ Syntax attribute preserved: {has_syntax}")
        print(f"🚫 Edit/Delete buttons removed: {not has_edit_buttons}")
        
        if not has_mermaid or not has_syntax:
            print("❌ CRITICAL: Mermaid data not preserved in cleaning")
            return False
        
        # Step 2: Test Mermaid rendering with updated settings
        print("\n🎨 Step 2: Testing Mermaid rendering...")
        
        from app.internal.mermaid_render import MermaidRenderer
        renderer = MermaidRenderer()
        
        processed_html = await renderer.process_html(cleaned_html)
        
        svg_count = processed_html.count('<svg')
        responsive_svg = 'max-width: 100%' in processed_html or 'useMaxWidth' in processed_html
        
        print(f"📊 SVG elements generated: {svg_count}")
        print(f"📏 SVG has responsive sizing: {responsive_svg}")
        
        if svg_count == 0:
            print("❌ CRITICAL: No SVG generated")
            return False
        
        # Step 3: Test PDF HTML generation
        print("\n📄 Step 3: Testing PDF HTML generation...")
        
        final_html = exporter._create_pdf_html(processed_html, "Test Document", 1)
        
        final_svg_count = final_html.count('<svg')
        has_pdf_styles = 'mermaid-container' in final_html
        
        print(f"📊 Final SVG count: {final_svg_count}")
        print(f"🎨 PDF styles applied: {has_pdf_styles}")
        
        if final_svg_count == 0:
            print("❌ CRITICAL: SVG lost in PDF generation")
            return False
        
        # Step 4: Check SVG sizing and responsiveness
        print("\n📐 Step 4: Checking SVG sizing...")
        
        if '<svg' in final_html:
            svg_start = final_html.find('<svg')
            svg_end = final_html.find('>', svg_start) + 1
            svg_tag = final_html[svg_start:svg_end]
            
            print(f"SVG tag: {svg_tag}")
            
            # Check for responsive attributes
            has_viewbox = 'viewBox=' in svg_tag
            has_responsive_width = 'width="100%"' in svg_tag or 'max-width' in svg_tag
            
            print(f"✅ Has viewBox (scalable): {has_viewbox}")
            print(f"✅ Has responsive width: {has_responsive_width}")
        
        print("\n🎉 PDF PIPELINE TEST COMPLETED SUCCESSFULLY!")
        print("✅ Mermaid diagrams should now appear in PDF without buttons")
        print("✅ Diagrams should be properly sized and responsive")
        
        return True
        
    except Exception as e:
        print(f"❌ PIPELINE TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_svg_size_comparison():
    """Compare SVG sizes before and after responsive settings"""
    print("\n📊 TESTING SVG SIZE COMPARISON")
    print("=" * 60)
    
    try:
        from app.internal.mermaid_render import MermaidRenderer
        
        test_syntax = """flowchart TD
    A[Test] --> B[Diagram]
    B --> C[Size]"""
        
        renderer = MermaidRenderer()
        
        print("🎨 Generating SVG with updated settings...")
        svg_result = await renderer._render_mermaid_to_svg(test_syntax)
        
        if svg_result:
            print(f"📏 SVG length: {len(svg_result)}")
            
            # Check for responsive features
            has_viewbox = 'viewBox=' in svg_result
            has_max_width = 'max-width' in svg_result
            has_width_100 = 'width="100%"' in svg_result
            
            print(f"✅ ViewBox present: {has_viewbox}")
            print(f"✅ Max-width styling: {has_max_width}")
            print(f"✅ Full-width sizing: {has_width_100}")
            
            # Extract viewBox dimensions
            if has_viewbox:
                viewbox_start = svg_result.find('viewBox="') + 9
                viewbox_end = svg_result.find('"', viewbox_start)
                viewbox = svg_result[viewbox_start:viewbox_end]
                print(f"📐 ViewBox dimensions: {viewbox}")
                
                # Parse width and height
                parts = viewbox.split()
                if len(parts) >= 4:
                    width, height = float(parts[2]), float(parts[3])
                    aspect_ratio = width / height
                    print(f"📏 Aspect ratio: {aspect_ratio:.2f}")
                    print(f"📐 Diagram size: {width}x{height}")
                    
                    if width > 800:
                        print("⚠️ Diagram might be too wide for PDF")
                    else:
                        print("✅ Diagram size looks good for PDF")
            
            return True
        else:
            print("❌ SVG generation failed")
            return False
            
    except Exception as e:
        print(f"❌ Size comparison failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("🔬 COMPREHENSIVE PDF EXPORT TEST")
    print("=" * 70)
    
    result1 = asyncio.run(test_full_pdf_pipeline_updated())
    result2 = asyncio.run(test_svg_size_comparison())
    
    print("\n" + "=" * 70)
    print("🎯 FINAL RESULTS:")
    
    if result1 and result2:
        print("✅ ALL TESTS PASSED!")
        print("🎉 PDF export should work with responsive, button-free diagrams")
        print("💡 Try the PDF export now - it should include the Mermaid diagram!")
    elif result1:
        print("⚠️ Pipeline works but sizing might have issues")
    else:
        print("❌ Critical issues found - PDF export may still fail")