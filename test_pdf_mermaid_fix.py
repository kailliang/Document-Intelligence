#!/usr/bin/env python3
"""
Test script to verify that Mermaid diagrams are correctly included in PDF exports.
"""

import asyncio
import sys
import os

# Add server directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

from app.internal.pdf_export import PDFExporter

# Sample HTML content with a Mermaid diagram
TEST_HTML_WITH_MERMAID = '''
<h1>Test Document with Mermaid Diagram</h1>
<p>This document contains a Mermaid diagram that should appear in the PDF export.</p>

<div class="mermaid-node-wrapper mermaid-node" data-syntax="flowchart TD
    A[Wireless Optogenetic Device] --> B[Light Transducing Materials]
    A --> C[Biocompatible Body]
    B --> D[Lanthanide-doped Nanoparticles]
    C --> E[Glass/PDMS Material]
    A --> F[Radiation System]
    F --> G[Radiation Probe]
    F --> H[Movement Mechanism]
    F --> I[Detector & Controller]" data-title="Device Architecture" data-type="mermaid-diagram">
    <div class="mermaid-title">Device Architecture</div>
    <div class="mermaid-diagram">
        <!-- This would contain the rendered SVG in the actual editor -->
        <div>Mermaid diagram placeholder</div>
    </div>
</div>

<p>The above diagram shows the architecture of the wireless optogenetic device.</p>
'''

async def test_pdf_export_with_mermaid():
    """Test PDF export with Mermaid diagram"""
    print("🧪 Testing PDF export with Mermaid diagram...")
    
    try:
        # Create mock document and version objects
        class MockDocument:
            def __init__(self):
                self.id = 1
                self.title = "Test Document with Mermaid"
        
        class MockDocumentVersion:
            def __init__(self):
                self.version_number = 1
                self.content = TEST_HTML_WITH_MERMAID
        
        document = MockDocument()
        version = MockDocumentVersion()
        
        # Initialize PDF exporter
        exporter = PDFExporter()
        
        print("📊 Processing HTML content...")
        
        # Step 1: Test HTML cleaning - should preserve Mermaid attributes
        cleaned_html = exporter._clean_html_content(version.content)
        print("✅ HTML cleaning completed")
        
        # Check if Mermaid attributes are preserved
        if 'data-syntax' in cleaned_html:
            print("✅ data-syntax attribute preserved")
        else:
            print("❌ data-syntax attribute REMOVED - this is the bug!")
            
        if 'data-title' in cleaned_html:
            print("✅ data-title attribute preserved")
        else:
            print("❌ data-title attribute removed")
            
        if 'data-type="mermaid-diagram"' in cleaned_html:
            print("✅ data-type='mermaid-diagram' attribute preserved")
        else:
            print("❌ data-type='mermaid-diagram' attribute removed")
        
        print("\n📝 Cleaned HTML preview:")
        print(cleaned_html[:500] + "...")
        
        # Step 2: Test Mermaid processing
        print("\n🎨 Testing Mermaid rendering...")
        
        try:
            from app.internal.mermaid_render import MermaidRenderer
            mermaid_renderer = MermaidRenderer()
            
            processed_html = await mermaid_renderer.process_html(cleaned_html)
            
            if '<svg' in processed_html:
                print("✅ Mermaid diagram successfully rendered to SVG")
            else:
                print("❌ Mermaid diagram NOT rendered - check mermaid_render.py")
                
            print("\n📊 Processed HTML preview:")
            print(processed_html[:500] + "...")
        except Exception as e:
            print(f"⚠️ Mermaid rendering test skipped (missing dependencies): {e}")
            processed_html = cleaned_html
        
        # Step 3: Test PDF generation (without actually creating file)
        print("\n📄 Testing PDF HTML generation...")
        pdf_html = exporter._create_pdf_html(processed_html, document.title, version.version_number)
        
        if 'mermaid' in pdf_html.lower():
            print("✅ Mermaid content included in PDF HTML")
        else:
            print("❌ Mermaid content missing from PDF HTML")
            
        print("\n🎉 Test completed!")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function"""
    print("🚀 Starting Mermaid PDF Export Test")
    print("=" * 50)
    
    success = await test_pdf_export_with_mermaid()
    
    print("=" * 50)
    if success:
        print("✅ Test completed - check output above for results")
    else:
        print("❌ Test failed - check error messages above")

if __name__ == "__main__":
    asyncio.run(main())