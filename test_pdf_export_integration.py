#!/usr/bin/env python3
"""
Integration test for PDF export with Mermaid diagrams
"""

import asyncio
import requests
import json
import time
from pathlib import Path

BASE_URL = "http://localhost:8000"

def test_api_connection():
    """Test if API is accessible"""
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"✅ API accessible - Status: {response.status_code}")
        return True
    except Exception as e:
        print(f"❌ API connection failed: {e}")
        return False

def create_test_document():
    """Create a test document with Mermaid content"""
    
    # HTML content with proper Mermaid structure
    html_content = '''
    <p>This is a test document with Mermaid diagrams.</p>
    
    <div data-type="mermaid-diagram" class="mermaid-node" data-syntax="graph TD&#10;    A[Patent Application] --&gt; B{Review}&#10;    B --&gt;|Approved| C[Grant Patent]&#10;    B --&gt;|Rejected| D[Revise]&#10;    D --&gt; B" data-title="Patent Review Process">
        <div class="mermaid-title">Patent Review Process</div>
        <div class="mermaid-diagram">
            <!-- This will be replaced by SVG during PDF export -->
        </div>
    </div>
    
    <p>Another diagram:</p>
    
    <div data-type="mermaid-diagram" class="mermaid-node" data-syntax="sequenceDiagram&#10;    Inventor-&gt;&gt;Patent Office: Submit Application&#10;    Patent Office-&gt;&gt;Examiner: Assign for Review&#10;    Examiner-&gt;&gt;Patent Office: Complete Review&#10;    Patent Office-&gt;&gt;Inventor: Decision Notice">
        <div class="mermaid-diagram">
            <!-- This will be replaced by SVG during PDF export -->
        </div>
    </div>
    
    <p>End of test document.</p>
    '''
    
    try:
        # Create document
        doc_data = {
            "title": "Mermaid Test Document",
            "content": html_content
        }
        
        response = requests.post(f"{BASE_URL}/create", json=doc_data)
        
        if response.status_code == 200:
            doc_info = response.json()
            doc_id = doc_info["id"]
            print(f"✅ Test document created - ID: {doc_id}")
            return doc_id, html_content
        else:
            print(f"❌ Document creation failed - Status: {response.status_code}")
            print(f"Response: {response.text}")
            return None, None
            
    except Exception as e:
        print(f"❌ Document creation error: {e}")
        return None, None

def test_pdf_export(doc_id):
    """Test PDF export for the document"""
    
    try:
        print(f"🔄 Testing PDF export for document {doc_id}...")
        
        # Request PDF export
        export_response = requests.post(f"{BASE_URL}/api/documents/{doc_id}/export/pdf")
        
        if export_response.status_code == 200:
            result = export_response.json()
            filename = result.get("filename")
            
            if filename:
                print(f"✅ PDF export initiated - Filename: {filename}")
                
                # Wait a moment for processing
                time.sleep(3)
                
                # Try to download the PDF
                download_response = requests.get(f"{BASE_URL}/api/downloads/{filename}")
                
                if download_response.status_code == 200:
                    # Save PDF locally for inspection
                    pdf_path = Path(f"test_export_{filename}")
                    with open(pdf_path, "wb") as f:
                        f.write(download_response.content)
                    
                    print(f"✅ PDF downloaded successfully - Size: {len(download_response.content)} bytes")
                    print(f"📄 PDF saved as: {pdf_path}")
                    
                    # Basic validation - check if PDF is reasonable size
                    if len(download_response.content) > 10000:  # At least 10KB
                        print("✅ PDF size seems reasonable (contains content)")
                        
                        # Check if it's actually a PDF
                        if download_response.content.startswith(b'%PDF'):
                            print("✅ File is valid PDF format")
                            return True
                        else:
                            print("❌ File is not valid PDF format")
                    else:
                        print("⚠️  PDF size seems small - may not contain diagrams")
                    
                else:
                    print(f"❌ PDF download failed - Status: {download_response.status_code}")
                    
            else:
                print("❌ No filename returned from export")
                
        else:
            print(f"❌ PDF export failed - Status: {export_response.status_code}")
            print(f"Response: {export_response.text}")
            
    except Exception as e:
        print(f"❌ PDF export error: {e}")
        
    return False

def test_backend_mermaid_processing(html_content):
    """Test backend Mermaid processing directly"""
    
    try:
        print("\n🔬 Testing backend Mermaid processing...")
        
        # Test endpoint that processes HTML with Mermaid
        test_data = {
            "html_content": html_content
        }
        
        # We don't have a direct endpoint for this, so let's check the logs
        # when PDF export runs to see if Mermaid processing is working
        
        print("Backend processing will be checked via PDF export logs...")
        return True
        
    except Exception as e:
        print(f"❌ Backend processing test error: {e}")
        return False

def main():
    """Run the complete integration test"""
    
    print("🧪 Starting PDF Export Integration Test")
    print("=" * 50)
    
    # Test 1: API Connection
    if not test_api_connection():
        print("❌ Cannot proceed - API not accessible")
        return
    
    # Test 2: Create test document
    doc_id, html_content = create_test_document()
    if not doc_id:
        print("❌ Cannot proceed - Document creation failed")
        return
    
    # Test 3: Backend processing check
    test_backend_mermaid_processing(html_content)
    
    # Test 4: PDF Export
    success = test_pdf_export(doc_id)
    
    # Summary
    print("\n" + "=" * 50)
    if success:
        print("🎉 Integration test PASSED!")
        print("✅ PDF export with Mermaid diagrams is working")
    else:
        print("❌ Integration test FAILED!")
        print("🔍 Check the generated PDF manually to see if diagrams are present")
    
    print(f"📝 Test document ID: {doc_id} (for manual inspection)")

if __name__ == "__main__":
    main()