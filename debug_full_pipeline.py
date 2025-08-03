#!/usr/bin/env python3
"""
Ultra-comprehensive test that traces the EXACT PDF export pipeline
"""

import asyncio
import sys
import os
import logging

# Add server directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

# Configure logging to see everything
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')

async def test_full_pdf_pipeline():
    """Test the complete PDF export pipeline step by step"""
    print("🔬 ULTRA-DEEP PDF PIPELINE INVESTIGATION")
    print("=" * 60)
    
    try:
        # Step 1: Get the EXACT document content from database
        print("📊 Step 1: Getting document content from database...")
        
        import requests
        response = requests.get("http://localhost:8000/document/1")
        doc_data = response.json()
        
        print(f"✅ Document ID: {doc_data['id']}")
        print(f"✅ Document title: {doc_data['title']}")
        print(f"✅ Content length: {len(doc_data['content'])}")
        
        # Check for Mermaid content
        content = doc_data['content']
        mermaid_count = content.count('data-type="mermaid-diagram"')
        print(f"📊 Mermaid diagrams found: {mermaid_count}")
        
        if mermaid_count == 0:
            print("❌ CRITICAL: No Mermaid diagrams in database content!")
            print("🔍 Content preview:")
            print(content[-500:])  # Show end of content where diagram might be
            return False
        
        # Step 2: Test HTML cleaning (as used in PDF export)
        print("\n🧹 Step 2: Testing HTML cleaning...")
        
        from app.internal.pdf_export import PDFExporter
        exporter = PDFExporter()
        
        cleaned_html = exporter._clean_html_content(content)
        
        mermaid_after_clean = cleaned_html.count('data-type="mermaid-diagram"')
        syntax_after_clean = cleaned_html.count('data-syntax=')
        
        print(f"📊 Mermaid diagrams after cleaning: {mermaid_after_clean}")
        print(f"📊 data-syntax attributes after cleaning: {syntax_after_clean}")
        
        if mermaid_after_clean == 0:
            print("❌ CRITICAL: HTML cleaning removes Mermaid elements!")
            print("🔍 Cleaned content preview:")
            print(cleaned_html[-500:])
            return False
        
        # Step 3: Test MermaidRenderer finding elements
        print("\n🔍 Step 3: Testing MermaidRenderer element detection...")
        
        from app.internal.mermaid_render import MermaidRenderer
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(cleaned_html, 'html.parser')
        
        # Exact same logic as MermaidRenderer
        mermaid_nodes = soup.find_all(['mermaid-node', 'div'], class_='mermaid-node')
        mermaid_diagrams = soup.find_all(['div'], attrs={'data-type': 'mermaid-diagram'})
        all_mermaid_elements = list(set(mermaid_nodes + mermaid_diagrams))
        
        print(f"📊 Elements with class='mermaid-node': {len(mermaid_nodes)}")
        print(f"📊 Elements with data-type='mermaid-diagram': {len(mermaid_diagrams)}")
        print(f"📊 Total unique elements: {len(all_mermaid_elements)}")
        
        if len(all_mermaid_elements) == 0:
            print("❌ CRITICAL: MermaidRenderer cannot find elements!")
            return False
        
        # Step 4: Test syntax extraction
        print("\n📝 Step 4: Testing syntax extraction...")
        
        renderer = MermaidRenderer()
        
        for i, element in enumerate(all_mermaid_elements):
            print(f"\n🔍 Element {i+1}:")
            print(f"  Tag: {element.name}")
            print(f"  Classes: {element.get('class', [])}")
            print(f"  data-type: {element.get('data-type', 'None')}")
            
            # Test syntax extraction
            syntax = renderer._extract_mermaid_syntax(element)
            print(f"  Extracted syntax length: {len(syntax) if syntax else 0}")
            
            if syntax:
                print(f"  Syntax preview: {syntax[:100]}...")
                
                # Check if syntax looks valid
                if 'flowchart' in syntax or 'graph' in syntax:
                    print("  ✅ Syntax appears valid")
                else:
                    print("  ❌ Syntax might be invalid")
                    
                # Step 5: Test Playwright rendering (the critical step)
                print(f"\n🎭 Step 5: Testing Playwright rendering for element {i+1}...")
                
                try:
                    svg_content = await renderer._render_mermaid_to_svg(syntax)
                    
                    if svg_content:
                        print(f"  ✅ SVG generated successfully - length: {len(svg_content)}")
                        print(f"  SVG preview: {svg_content[:100]}...")
                        
                        # Check if it's actually valid SVG
                        if '<svg' in svg_content and '</svg>' in svg_content:
                            print("  ✅ Valid SVG structure")
                        else:
                            print("  ❌ Invalid SVG structure")
                            
                    else:
                        print("  ❌ CRITICAL: Playwright returned empty SVG")
                        return False
                        
                except Exception as e:
                    print(f"  ❌ CRITICAL: Playwright rendering failed: {str(e)}")
                    return False
            else:
                print("  ❌ CRITICAL: No syntax extracted")
                return False
        
        # Step 6: Test full MermaidRenderer processing
        print("\n🎨 Step 6: Testing full MermaidRenderer processing...")
        
        try:
            processed_html = await renderer.process_html(cleaned_html)
            
            svg_count = processed_html.count('<svg')
            mermaid_container_count = processed_html.count('mermaid-container')
            
            print(f"📊 SVG elements in processed HTML: {svg_count}")
            print(f"📊 Mermaid containers in processed HTML: {mermaid_container_count}")
            
            if svg_count == 0:
                print("❌ CRITICAL: No SVG elements in final processed HTML")
                return False
            else:
                print("✅ SVG elements successfully added to HTML")
                
        except Exception as e:
            print(f"❌ CRITICAL: MermaidRenderer.process_html failed: {str(e)}")
            return False
        
        # Step 7: Test PDF HTML generation
        print("\n📄 Step 7: Testing PDF HTML generation...")
        
        try:
            final_pdf_html = exporter._create_pdf_html(processed_html, doc_data['title'], 1)
            
            final_svg_count = final_pdf_html.count('<svg')
            
            print(f"📊 SVG elements in final PDF HTML: {final_svg_count}")
            
            if final_svg_count == 0:
                print("❌ CRITICAL: No SVG elements in final PDF HTML")
                return False
            else:
                print("✅ SVG elements preserved in final PDF HTML")
                
        except Exception as e:
            print(f"❌ CRITICAL: PDF HTML generation failed: {str(e)}")
            return False
        
        print("\n🎉 PIPELINE TEST COMPLETE!")
        print("✅ All steps passed - Mermaid rendering should work")
        return True
        
    except Exception as e:
        print(f"❌ PIPELINE TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_full_pdf_pipeline())
    
    print("\n" + "=" * 60)
    if success:
        print("🎯 CONCLUSION: Pipeline works - issue might be elsewhere")
    else:
        print("🚨 CONCLUSION: Found critical issue in pipeline")