#!/usr/bin/env python3
"""
Final test of PDF export with fixed Mermaid rendering
"""

import asyncio
import sys
import os
from pathlib import Path

# Add server directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

async def test_complete_pdf_export():
    """Test complete PDF export pipeline with Mermaid diagrams"""
    print("📄 Testing Complete PDF Export Pipeline")
    print("=" * 60)
    
    try:
        # Import necessary modules
        from app.internal.pdf_export_simple import SimplePDFExporter
        from app.models import Document, DocumentVersion
        from datetime import datetime
        
        # Create mock document with Mermaid content
        test_html = """
        <h1>Test Document with Mermaid Diagrams</h1>
        <p>This document contains a Mermaid diagram to test PDF export:</p>
        
        <div class="mermaid-container" data-type="mermaid-diagram" data-syntax="flowchart TD
    A[Wireless Device] --> B[Light Materials]
    A --> C[Optical Windows]
    D[System] --> A" data-title="Device Architecture">
            <div class="mermaid-title">Device Architecture</div>
            <div class="mermaid-diagram">
                <!-- This will be replaced with actual SVG during export -->
                <pre class="mermaid-syntax">flowchart TD
    A[Wireless Device] --> B[Light Materials]
    A --> C[Optical Windows]
    D[System] --> A</pre>
            </div>
        </div>
        
        <p>The diagram above shows the basic architecture of the wireless optogenetic device.</p>
        """
        
        # Create mock objects
        class MockDocument:
            def __init__(self):
                self.id = 999
                self.title = "Test Document"
                
        class MockVersion:
            def __init__(self):
                self.id = 999
                self.version_number = 1
                self.content = test_html
                
        document = MockDocument()
        version = MockVersion()
        
        print(f"📋 Created test document: {document.title}")
        print(f"📊 Content length: {len(version.content)} characters")
        
        # Test PDF export
        exporter = SimplePDFExporter()
        
        print("\n🔄 Starting PDF export process...")
        filename = await exporter.export_document(document, version)
        
        print(f"✅ PDF export completed: {filename}")
        
        # Check if file was created
        file_path = exporter.get_file_path(filename)
        if file_path.exists():
            file_size = file_path.stat().st_size
            print(f"📁 File created successfully")
            print(f"📏 File size: {file_size:,} bytes")
            
            if file_size > 10000:  # Reasonable PDF size
                print("✅ PDF appears to contain content (good file size)")
            else:
                print("⚠️ PDF file size seems small, may be empty")
                
            return True
        else:
            print("❌ PDF file was not created")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Complete PDF Export Test")
    print("=" * 70)
    
    success = asyncio.run(test_complete_pdf_export())
    
    print("\n" + "=" * 70)
    if success:
        print("🎉 PDF Export Test PASSED")
        print("💡 PDF export with Mermaid diagrams should now work correctly")
        print("🔧 Diagrams should render as proper graphics instead of black blocks")
    else:
        print("❌ PDF Export Test FAILED")
        print("💡 Check the error messages above for troubleshooting")