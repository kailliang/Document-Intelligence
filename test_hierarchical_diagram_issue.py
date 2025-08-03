#!/usr/bin/env python3
"""
Test script to investigate hierarchical diagram rendering issue
where text labels show as black boxes in PDF export
"""

import asyncio
import sys
from pathlib import Path

# Add server directory to path
sys.path.append(str(Path(__file__).parent / 'server'))

from bs4 import BeautifulSoup
from server.app.internal.mermaid_render import MermaidRenderer

async def test_hierarchical_vs_sequence():
    """Compare hierarchical flowchart vs sequence diagram rendering"""
    
    print("🔍 Investigating Hierarchical Diagram Text Rendering Issue")
    print("=" * 60)
    
    test_cases = [
        {
            "name": "Sequence Diagram (Working)",
            "syntax": """sequenceDiagram
    participant A as Applicant
    participant PA as PatentAttorney
    participant PO as PatentOffice
    A->>PA: Submit Invention Disclosure
    PA->>PO: File Patent Application
    PO->>PA: Acknowledge Receipt""",
            "type": "sequence"
        },
        
        {
            "name": "Hierarchical Flowchart (Problematic)",
            "syntax": """flowchart TD
    A[Wireless Optogenetic Device] --> B[Body]
    A --> C[Device Configuration]
    A --> D[Sealed Enclosure]
    B --> E[Light Transducing Materials]
    C --> F[Tapered Design]
    C --> G[Multiple Optical Windows]
    E --> H[Lanthanide-doped Nanoparticles]""",
            "type": "flowchart"
        }
    ]
    
    renderer = MermaidRenderer()
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Test {i}: {test_case['name']}")
        print("-" * 40)
        
        try:
            print("🎨 Rendering SVG...")
            svg_result = await renderer._render_mermaid_to_svg(test_case['syntax'])
            
            if svg_result:
                print(f"✅ SVG rendering successful (length: {len(svg_result)} chars)")
                
                # Analyze SVG content for text-related issues
                print("\n🔍 Analyzing SVG content...")
                
                # Check for text elements
                text_count = svg_result.count('<text')
                print(f"📝 Text elements found: {text_count}")
                
                # Check for foreignObject (can cause PDF issues)
                foreign_object_count = svg_result.count('<foreignObject')
                print(f"🏷️  ForeignObject elements: {foreign_object_count}")
                
                # Check for HTML labels
                html_label_indicators = [
                    'xmlns="http://www.w3.org/1999/xhtml"',
                    '<div',
                    '<span',
                    'text-anchor',
                    'dominant-baseline'
                ]
                
                html_features = []
                for indicator in html_label_indicators:
                    if indicator in svg_result:
                        html_features.append(indicator)
                
                if html_features:
                    print(f"🔧 HTML features detected: {html_features}")
                
                # Check for CSS that might affect text rendering
                css_issues = [
                    'htmlLabels',
                    'font-family',
                    'fill="transparent"',
                    'opacity="0"',
                    'display:none'
                ]
                
                css_problems = []
                for issue in css_issues:
                    if issue in svg_result:
                        css_problems.append(issue)
                
                if css_problems:
                    print(f"⚠️  Potential CSS issues: {css_problems}")
                
                # Save SVG for manual inspection
                filename = f"debug_{test_case['type']}_diagram.svg"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(svg_result)
                print(f"💾 SVG saved as: {filename}")
                
                # Check specific text content
                soup = BeautifulSoup(svg_result, 'xml')
                text_elements = soup.find_all('text')
                
                print(f"📊 Detailed text analysis:")
                for j, text_elem in enumerate(text_elements[:5]):  # Show first 5
                    text_content = text_elem.get_text().strip()
                    fill = text_elem.get('fill', 'default')
                    font_family = text_elem.get('font-family', 'default')
                    print(f"   Text {j+1}: '{text_content}' (fill: {fill}, font: {font_family})")
                
                if len(text_elements) > 5:
                    print(f"   ... and {len(text_elements) - 5} more text elements")
                    
            else:
                print("❌ SVG rendering failed")
                
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
    
    print(f"\n🏁 Analysis completed")
    print("=" * 60)

async def test_mermaid_config_impact():
    """Test different Mermaid configurations to identify the issue"""
    
    print("\n🔧 Testing Mermaid Configuration Impact")
    print("=" * 40)
    
    # Test the problematic diagram with different configs
    problematic_syntax = """flowchart TD
    A[Wireless Optogenetic Device] --> B[Body]
    A --> C[Device Configuration]
    B --> D[Light Transducing Materials]"""
    
    configs_to_test = [
        {
            "name": "Current Config (htmlLabels: false)",
            "htmlLabels": False
        },
        {
            "name": "Alternative Config (htmlLabels: true)",
            "htmlLabels": True
        }
    ]
    
    renderer = MermaidRenderer()
    
    for config in configs_to_test:
        print(f"\n🧪 Testing: {config['name']}")
        
        # We'll need to temporarily modify the renderer for this test
        # For now, let's analyze what's happening with the current config
        
        try:
            svg_result = await renderer._render_mermaid_to_svg(problematic_syntax)
            
            if svg_result:
                # Check for HTML vs SVG text rendering
                has_foreign_object = '<foreignObject' in svg_result
                has_svg_text = '<text' in svg_result
                has_html_divs = '<div' in svg_result
                
                print(f"   ForeignObject: {has_foreign_object}")
                print(f"   SVG Text: {has_svg_text}")
                print(f"   HTML Divs: {has_html_divs}")
                
                if has_foreign_object and has_html_divs:
                    print("   🚨 Issue: Using HTML labels in foreignObject (PDF incompatible)")
                elif has_svg_text:
                    print("   ✅ Using SVG text elements (PDF compatible)")
        
        except Exception as e:
            print(f"   ❌ Config test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_hierarchical_vs_sequence())
    asyncio.run(test_mermaid_config_impact())