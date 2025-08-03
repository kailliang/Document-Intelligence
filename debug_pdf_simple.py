#!/usr/bin/env python3
"""
Simple test to check if PDF export works at all
"""

import requests
import time

def test_pdf_export_simple():
    """Test PDF export with timeout"""
    print("🧪 SIMPLE PDF EXPORT TEST")
    print("=" * 40)
    
    try:
        print("📊 Starting PDF export...")
        
        # Set a short timeout to avoid hanging
        response = requests.post(
            "http://localhost:8000/api/documents/1/export/pdf",
            json={},
            timeout=30  # 30 second timeout
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ PDF export successful!")
            print(f"📄 Filename: {data.get('filename', 'Unknown')}")
            print(f"📏 Status: {data.get('status', 'Unknown')}")
            return True
        else:
            print(f"❌ PDF export failed with status: {response.status_code}")
            print(f"📄 Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("⏰ PDF export timed out (30 seconds)")
        print("💡 This suggests the backend is hanging during processing")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend")
        return False
    except Exception as e:
        print(f"❌ PDF export failed: {str(e)}")
        return False

def check_backend_health():
    """Check if backend is responsive"""
    print("\n🔍 BACKEND HEALTH CHECK")
    print("=" * 40)
    
    try:
        # Simple health check
        response = requests.get("http://localhost:8000/document/1", timeout=5)
        
        if response.status_code == 200:
            print("✅ Backend is responsive")
            data = response.json()
            has_mermaid = 'data-type="mermaid-diagram"' in data.get('content', '')
            print(f"📊 Document has Mermaid: {has_mermaid}")
            return True
        else:
            print(f"❌ Backend returned status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Backend health check failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("🔬 PDF EXPORT DIAGNOSIS")
    print("=" * 50)
    
    health_ok = check_backend_health()
    
    if health_ok:
        pdf_ok = test_pdf_export_simple()
        
        print("\n" + "=" * 50)
        print("🎯 DIAGNOSIS:")
        
        if pdf_ok:
            print("✅ PDF export is working!")
            print("🎉 The Mermaid diagram should appear in the PDF")
        else:
            print("❌ PDF export is failing or hanging")
            print("💡 Possible causes:")
            print("  - WeasyPrint dependency issues")
            print("  - Playwright browser timeout")
            print("  - Large SVG causing memory issues")
            print("  - Backend processing timeout")
    else:
        print("\n❌ Backend is not healthy - fix backend first")