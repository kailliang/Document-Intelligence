#!/usr/bin/env python3
"""
Test with the actual document content that has Mermaid diagram
"""

import asyncio
import sys
import os

# Add server directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

# Real HTML content from the document (with Mermaid)
REAL_HTML_CONTENT = '''<h1>Claims</h1><p>1. A wireless optogenetic device for remotely controlling neural activities, the device comprising:</p><p>a body holding light transducing materials capable of up-converting infrared or near-infrared electromagnetic radiation to visible light, wherein the body is made of biocompatible materials and is transparent and lightweight;</p><p>the light transducing materials being lanthanide-doped nanoparticles or similar, capable of up-converting infrared or near-infrared to visible light;</p><p>a device being designed to be placed near a neural cell of a subject, and having a tapered design for concentrated light emission;</p><p>the device further comprising multiple optical windows for complex neural activity control, and being sealed to enclose the light transducing materials.</p><p>2. The wireless optogenetic device of claim 1, wherein the biocompatible materials are glass or polydimethylsiloxane.</p><p>3. The wireless optogenetic device of claim 1, wherein the device is adaptable for both human and non-human subjects.</p><p>4. A radiation system for remotely activating the wireless optogenetic device of claim 1, the radiation system comprising:</p><p>a radiation probe, a movement mechanism, a detector, and a controller;</p><p>the radiation system being capable of tracking and irradiating the wireless device with infrared or near-infrared radiation, enabling real-time adjustment and precise targeting;</p><p>the radiation system being capable of altering properties of radiation including wavelength, intensity, and pulse duration, and being adaptable to various subject movement ranges.</p><p>5. The radiation system of claim 4, wherein the system's versatility allows for various experimental settings and subject conditions.</p><p>6. A method for remotely controlling neural activities, the method having the steps of:</p><p>placing the wireless optogenetic device of claim 1 near a neural cell of a subject;</p><p>activating the wireless optogenetic device using the radiation system of claim 4;</p><p>up-converting infrared or near-infrared electromagnetic radiation to visible light using the light transducing materials in the wireless optogenetic device;</p><p>controlling complex neural activity through the multiple optical windows in the wireless optogenetic device.</p><p>7. The method of claim 5, wherein the step of activating the wireless optogenetic device includes tracking and irradiating the wireless device with infrared or near-infrared radiation, enabling real-time adjustment and precise targeting.</p><p>8. The method of claim 6, wherein the step of activating the wireless optogenetic device includes altering properties of radiation including wavelength, intensity, and pulse duration.</p><div data-type="mermaid-diagram" class="mermaid-node" data-syntax="flowchart TD
    A[Wireless Optogenetic Device] --&gt; B[Body with Light Transducing Materials]
    A --&gt; C[Multiple Optical Windows]
    D[Radiation System] --&gt; E[Radiation Probe]
    D --&gt; F[Movement Mechanism]
    D --&gt; G[Detector]
    D --&gt; H[Controller]
    D --&gt;|Activates| A
    B --&gt;|Up-converts Radiation| C"></div>'''

def test_html_cleaning_real():
    """Test HTML cleaning with real content"""
    from bs4 import BeautifulSoup
    
    print("🧪 Testing HTML Cleaning with Real Document Content")
    print("=" * 60)
    
    print("📄 Real document content contains:")
    if 'data-type="mermaid-diagram"' in REAL_HTML_CONTENT:
        print("✅ data-type='mermaid-diagram' found")
    else:
        print("❌ data-type='mermaid-diagram' NOT found")
        
    if 'data-syntax=' in REAL_HTML_CONTENT:
        print("✅ data-syntax found")
    else:
        print("❌ data-syntax NOT found")
        
    if 'class="mermaid-node"' in REAL_HTML_CONTENT:
        print("✅ class='mermaid-node' found")
    else:
        print("❌ class='mermaid-node' NOT found")
    
    print()
    
    # Test HTML cleaning
    print("🧹 Testing HTML cleaning...")
    soup = BeautifulSoup(REAL_HTML_CONTENT, 'html.parser')
    
    # Apply the NEW cleaning logic
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
        
        # Clean classes
        if 'class' in elem.attrs:
            classes = elem.attrs['class']
            if isinstance(classes, list):
                # Preserve useful classes including Mermaid-related
                useful_classes = [cls for cls in classes if cls in [
                    'mermaid-container', 'mermaid-title', 'mermaid-diagram', 
                    'mermaid-node', 'mermaid-node-wrapper'
                ]]
                if useful_classes:
                    elem.attrs['class'] = useful_classes
                else:
                    del elem.attrs['class']
    
    cleaned_html = str(soup)
    
    print("After cleaning:")
    if 'data-type="mermaid-diagram"' in cleaned_html:
        print("✅ data-type='mermaid-diagram' preserved")
    else:
        print("❌ data-type='mermaid-diagram' REMOVED")
        
    if 'data-syntax=' in cleaned_html:
        print("✅ data-syntax preserved")
    else:
        print("❌ data-syntax REMOVED")
        
    if 'class="mermaid-node"' in cleaned_html:
        print("✅ class='mermaid-node' preserved")
    else:
        print("❌ class='mermaid-node' REMOVED")
    
    print()
    print("🔍 Mermaid section:")
    mermaid_start = cleaned_html.find('<div data-type="mermaid-diagram"')
    if mermaid_start != -1:
        mermaid_section = cleaned_html[mermaid_start:mermaid_start+200]
        print(mermaid_section + "...")
    else:
        print("❌ No Mermaid section found!")
    
    return cleaned_html

async def test_mermaid_finder():
    """Test if MermaidRenderer can find the elements"""
    print("\n🔍 Testing Mermaid Element Finding...")
    
    try:
        from app.internal.mermaid_render import MermaidRenderer
        from bs4 import BeautifulSoup
        
        cleaned_html = test_html_cleaning_real()
        
        # Simulate what MermaidRenderer does
        soup = BeautifulSoup(cleaned_html, 'html.parser')
        
        # Find mermaid-node elements
        mermaid_nodes = soup.find_all(['mermaid-node', 'div'], class_='mermaid-node')
        print(f"Found {len(mermaid_nodes)} elements with class='mermaid-node'")
        
        # Find data-type="mermaid-diagram" elements  
        mermaid_diagrams = soup.find_all(['div'], attrs={'data-type': 'mermaid-diagram'})
        print(f"Found {len(mermaid_diagrams)} elements with data-type='mermaid-diagram'")
        
        # Combined results
        all_mermaid_elements = list(set(mermaid_nodes + mermaid_diagrams))
        print(f"Total unique Mermaid elements: {len(all_mermaid_elements)}")
        
        if all_mermaid_elements:
            for i, elem in enumerate(all_mermaid_elements):
                print(f"\nElement {i+1}:")
                print(f"  Tag: {elem.name}")
                print(f"  Classes: {elem.get('class', [])}")
                print(f"  data-type: {elem.get('data-type', 'None')}")
                print(f"  data-syntax: {elem.get('data-syntax', 'None')[:50]}...")
        else:
            print("❌ NO MERMAID ELEMENTS FOUND!")
            
    except ImportError as e:
        print(f"⚠️ Cannot test MermaidRenderer: {e}")

if __name__ == "__main__":
    asyncio.run(test_mermaid_finder())