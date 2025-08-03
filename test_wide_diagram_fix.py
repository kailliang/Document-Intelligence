#!/usr/bin/env python3
"""
Test script to validate wide Mermaid diagram fixes in PDF export
"""

import asyncio
import sys
from pathlib import Path

# Add server directory to path
sys.path.append(str(Path(__file__).parent / 'server'))

from bs4 import BeautifulSoup
from server.app.internal.mermaid_render import MermaidRenderer

async def test_wide_diagram_rendering():
    """Test wide Mermaid diagrams that would cause issues in PDF"""
    
    print("🧪 Testing Wide Mermaid Diagram Rendering")
    print("=" * 50)
    
    # Test cases with wide diagrams
    wide_diagram_tests = [
        {
            "name": "Wide Flowchart with Many Nodes",
            "syntax": """flowchart LR
    A[Start Process] --> B[Input Validation]
    B --> C[Data Processing]
    C --> D[Business Logic]
    D --> E[Database Operations]
    E --> F[Response Generation]
    F --> G[Output Formatting]
    G --> H[Quality Assurance]
    H --> I[Performance Check]
    I --> J[Logging]
    J --> K[End Process]""",
            "title": "Wide Processing Pipeline"
        },
        
        {
            "name": "Complex Decision Tree",
            "syntax": """flowchart TD
    A[Patent Application] --> B{Prior Art Search}
    B -->|Found| C[Analyze Similarities]
    B -->|Not Found| D[Proceed to Examination]
    C --> E{Significant Overlap?}
    E -->|Yes| F[Detailed Comparison]
    E -->|No| G[Document Differences]
    F --> H{Patentable?}
    H -->|Yes| I[Grant Patent with Conditions]
    H -->|No| J[Reject Application]
    G --> K[Proceed to Examination]
    D --> L[Technical Review]
    K --> L
    L --> M[Patent Grant]""",
            "title": "Patent Examination Decision Tree"
        },
        
        {
            "name": "Wide Sequence Diagram",
            "syntax": """sequenceDiagram
    participant I as Inventor
    participant A as Attorney
    participant PO as Patent Office
    participant E as Examiner
    participant DB as Database
    participant P as Public
    
    I->>A: Submit Invention Disclosure
    A->>A: Prepare Application
    A->>PO: File Patent Application
    PO->>DB: Store Application
    PO->>E: Assign Examiner
    E->>DB: Search Prior Art
    E->>A: First Office Action
    A->>I: Review Comments
    I->>A: Provide Response
    A->>PO: Submit Response
    E->>E: Review Response
    E->>A: Final Office Action
    A->>PO: Submit Final Response
    E->>PO: Recommend Grant
    PO->>DB: Update Status
    PO->>P: Publish Patent""",
            "title": "Patent Application Sequence"
        }
    ]
    
    renderer = MermaidRenderer()
    
    for i, test_case in enumerate(wide_diagram_tests, 1):
        print(f"\n📋 Test {i}: {test_case['name']}")
        print("-" * 40)
        
        # Create test HTML with the wide diagram
        test_html = f'''
        <div data-type="mermaid-diagram" class="mermaid-node" data-syntax="{test_case['syntax']}" data-title="{test_case.get('title', '')}">
            <div class="mermaid-title">{test_case.get('title', '')}</div>
            <div class="mermaid-diagram"><!-- rendered content --></div>
        </div>
        '''
        
        try:
            print("🎨 Rendering SVG...")
            svg_result = await renderer._render_mermaid_to_svg(test_case['syntax'])
            
            if svg_result:
                print(f"✅ SVG rendering successful (length: {len(svg_result)} chars)")
                
                # Check if SVG has proper attributes for width handling
                if 'width=' in svg_result:
                    print("📏 SVG contains width attributes")
                if 'viewBox=' in svg_result:
                    print("📐 SVG contains viewBox (good for scaling)")
                    
                # Test complete HTML processing
                print("🔄 Testing complete HTML processing...")
                processed_html = await renderer.process_html(test_html)
                
                if '<svg' in processed_html:
                    print("✅ Complete processing successful - SVG found")
                    
                    # Check for proper container styling
                    soup = BeautifulSoup(processed_html, 'html.parser')
                    container = soup.find('div', class_='mermaid-container')
                    if container:
                        style = container.get('style', '')
                        if 'overflow: visible' in style:
                            print("✅ Container has proper overflow handling")
                        if 'width: 100%' in style:
                            print("✅ Container has full width")
                        
                        diagram_div = container.find('div', class_='mermaid-diagram')
                        if diagram_div:
                            diagram_style = diagram_div.get('style', '')
                            if 'overflow: visible' in diagram_style:
                                print("✅ Diagram div has proper overflow handling")
                            if 'display: block' in diagram_style:
                                print("✅ Diagram div uses block display")
                    
                    # Check SVG attributes in processed HTML
                    svg_element = soup.find('svg')
                    if svg_element:
                        print("🔍 SVG analysis:")
                        width = svg_element.get('width')
                        height = svg_element.get('height')
                        viewbox = svg_element.get('viewBox')
                        
                        print(f"   Width: {width}")
                        print(f"   Height: {height}")
                        print(f"   ViewBox: {viewbox}")
                        
                        if viewbox:
                            print("✅ ViewBox present - will scale properly")
                        else:
                            print("⚠️  No ViewBox - may have scaling issues")
                else:
                    print("❌ Complete processing failed - no SVG in output")
            else:
                print("❌ SVG rendering failed")
                
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
    
    print(f"\n🏁 Wide diagram testing completed")
    print("=" * 50)

async def test_css_improvements():
    """Test that CSS improvements are properly applied"""
    
    print("\n🎨 Testing CSS Improvements")
    print("=" * 30)
    
    renderer = MermaidRenderer()
    
    # Test simple diagram
    simple_syntax = "graph LR; A[Start] --> B[End]"
    svg_result = await renderer._render_mermaid_to_svg(simple_syntax)
    
    if svg_result:
        print("✅ Basic SVG generation working")
        
        # Check for problematic CSS that was removed
        problematic_patterns = [
            'width: 100% !important',
            'min-width: 400px !important',
            'max-width: 100% !important'
        ]
        
        issues_found = []
        for pattern in problematic_patterns:
            if pattern in svg_result:
                issues_found.append(pattern)
        
        if issues_found:
            print(f"⚠️  Found problematic CSS patterns: {issues_found}")
        else:
            print("✅ No problematic CSS patterns found")
            
        # Check for improved patterns
        good_patterns = [
            'width: auto !important',
            'margin: 0 auto !important'
        ]
        
        good_found = []
        for pattern in good_patterns:
            if pattern in svg_result:
                good_found.append(pattern)
                
        if good_found:
            print(f"✅ Found improved CSS patterns: {good_found}")
        else:
            print("ℹ️  CSS improvements may be applied at container level")
    
    else:
        print("❌ Basic SVG generation failed")

if __name__ == "__main__":
    asyncio.run(test_wide_diagram_rendering())
    asyncio.run(test_css_improvements())