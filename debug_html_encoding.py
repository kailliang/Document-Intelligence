#!/usr/bin/env python3
"""
Debug HTML encoding issues with Mermaid syntax
"""

import html
from bs4 import BeautifulSoup

# The data-syntax content as it appears in the document (HTML encoded)
ENCODED_SYNTAX = '''flowchart TD
    A[Wireless Optogenetic Device] --&gt; B[Body with Light Transducing Materials]
    A --&gt; C[Multiple Optical Windows]
    D[Radiation System] --&gt; E[Radiation Probe]
    D --&gt; F[Movement Mechanism]
    D --&gt; G[Detector]
    D --&gt; H[Controller]
    D --&gt;|Activates| A
    B --&gt;|Up-converts Radiation| C'''

def test_html_decoding():
    """Test HTML decoding of Mermaid syntax"""
    print("🧪 Testing HTML Decoding Issues")
    print("=" * 50)
    
    print("📄 Original encoded syntax:")
    print(ENCODED_SYNTAX)
    print()
    
    print("🔄 After HTML decoding:")
    decoded_syntax = html.unescape(ENCODED_SYNTAX)
    print(decoded_syntax)
    print()
    
    print("✅ Decoding fixed arrows:")
    if '-->' in decoded_syntax:
        print("✅ Arrow '-->' correctly decoded")
    else:
        print("❌ Arrow still encoded as '--&gt;'")
    
    # Test with BeautifulSoup extraction
    print("\n🧹 Testing BeautifulSoup attribute extraction:")
    
    test_html = f'<div data-syntax="{ENCODED_SYNTAX}">content</div>'
    soup = BeautifulSoup(test_html, 'html.parser')
    div = soup.find('div')
    
    extracted_syntax = div.get('data-syntax')
    print("Extracted syntax:")
    print(extracted_syntax[:100] + "...")
    
    if '-->' in extracted_syntax:
        print("✅ BeautifulSoup automatically decoded HTML entities")
    else:
        print("❌ BeautifulSoup did NOT decode HTML entities")
        print("  Manual decoding needed:")
        manual_decoded = html.unescape(extracted_syntax)
        print(manual_decoded[:100] + "...")

if __name__ == "__main__":
    test_html_decoding()