#!/usr/bin/env python3
"""
Simple test to verify HTML cleaning preserves Mermaid attributes
"""

from bs4 import BeautifulSoup

# Sample HTML content with a Mermaid diagram
TEST_HTML_WITH_MERMAID = '''
<h1>Test Document with Mermaid Diagram</h1>
<p>This document contains a Mermaid diagram.</p>

<div class="mermaid-node-wrapper mermaid-node" data-syntax="flowchart TD
    A[Wireless Device] --> B[Components]" data-title="Device Architecture" data-type="mermaid-diagram">
    <div class="mermaid-title">Device Architecture</div>
    <div class="mermaid-diagram">Mermaid diagram placeholder</div>
</div>

<p>More content here.</p>
'''

def clean_html_content_OLD(html_content):
    """Original cleaning function that removes ALL data-* attributes"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    for elem in soup.find_all():
        # Remove ALL data-* attributes (OLD VERSION)
        attrs_to_remove = [attr for attr in elem.attrs.keys() if attr.startswith('data-')]
        for attr in attrs_to_remove:
            del elem.attrs[attr]
    
    return str(soup)

def clean_html_content_NEW(html_content):
    """New cleaning function that preserves Mermaid data-* attributes"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    for elem in soup.find_all():
        # Remove data-* attributes, but preserve Mermaid-related ones
        attrs_to_remove = []
        for attr in elem.attrs.keys():
            if attr.startswith('data-'):
                # Preserve Mermaid-related data attributes
                if attr not in ['data-syntax', 'data-title', 'data-type']:
                    attrs_to_remove.append(attr)
                elif attr == 'data-type' and elem.attrs[attr] != 'mermaid-diagram':
                    # Only preserve data-type="mermaid-diagram"
                    attrs_to_remove.append(attr)
        
        for attr in attrs_to_remove:
            del elem.attrs[attr]
    
    return str(soup)

def test_html_cleaning():
    """Test both versions of HTML cleaning"""
    print("🧪 Testing HTML Cleaning Functions")
    print("=" * 50)
    
    print("📄 Original HTML:")
    print(TEST_HTML_WITH_MERMAID)
    print()
    
    # Test OLD version
    print("❌ OLD VERSION (removes ALL data-* attributes):")
    old_result = clean_html_content_OLD(TEST_HTML_WITH_MERMAID)
    
    if 'data-syntax' in old_result:
        print("✅ data-syntax preserved")
    else:
        print("❌ data-syntax REMOVED")
        
    if 'data-title' in old_result:
        print("✅ data-title preserved")
    else:
        print("❌ data-title REMOVED")
        
    if 'data-type="mermaid-diagram"' in old_result:
        print("✅ data-type preserved")
    else:
        print("❌ data-type REMOVED")
    
    print()
    print("OLD RESULT:")
    print(old_result[:400] + "...")
    print()
    
    # Test NEW version
    print("✅ NEW VERSION (preserves Mermaid data-* attributes):")
    new_result = clean_html_content_NEW(TEST_HTML_WITH_MERMAID)
    
    if 'data-syntax' in new_result:
        print("✅ data-syntax preserved")
    else:
        print("❌ data-syntax REMOVED")
        
    if 'data-title' in new_result:
        print("✅ data-title preserved")
    else:
        print("❌ data-title REMOVED")
        
    if 'data-type="mermaid-diagram"' in new_result:
        print("✅ data-type preserved")
    else:
        print("❌ data-type REMOVED")
    
    print()
    print("NEW RESULT:")
    print(new_result[:400] + "...")
    print()
    
    print("=" * 50)
    print("🎯 CONCLUSION:")
    if all(attr in new_result for attr in ['data-syntax', 'data-title', 'data-type="mermaid-diagram"']):
        print("✅ Fix is working! Mermaid attributes are preserved.")
    else:
        print("❌ Fix is NOT working! Some attributes are still missing.")

if __name__ == "__main__":
    test_html_cleaning()