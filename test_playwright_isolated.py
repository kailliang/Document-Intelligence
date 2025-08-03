#!/usr/bin/env python3
"""
Test Playwright Mermaid rendering in isolation
"""

import asyncio
import sys
import os

# Add server directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

# The EXACT syntax from the document 
REAL_MERMAID_SYNTAX = """flowchart TD
    A[Wireless Optogenetic Device] --> B[Body with Light Transducing Materials]
    A --> C[Multiple Optical Windows]
    D[Radiation System] --> E[Radiation Probe]
    D --> F[Movement Mechanism]
    D --> G[Detector]
    D --> H[Controller]
    D -->|Activates| A
    B -->|Up-converts Radiation| C"""

async def test_playwright_mermaid():
    """Test Playwright Mermaid rendering with the exact syntax from the document"""
    print("🎭 Testing Playwright Mermaid Rendering")
    print("=" * 50)
    
    try:
        from playwright.async_api import async_playwright
        
        print("📊 Testing with real document Mermaid syntax...")
        print(f"Syntax length: {len(REAL_MERMAID_SYNTAX)}")
        print(f"Syntax preview: {REAL_MERMAID_SYNTAX[:100]}...")
        
        async with async_playwright() as p:
            print("🚀 Launching browser...")
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Create HTML with Mermaid
            html_template = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
                <style>
                    body {{ 
                        margin: 20px; 
                        font-family: 'Arial', sans-serif;
                        background: white;
                    }}
                    .mermaid {{ 
                        text-align: center;
                        background: white;
                    }}
                </style>
            </head>
            <body>
                <div class="mermaid" id="mermaid-diagram">
                    {REAL_MERMAID_SYNTAX}
                </div>
                <script>
                    mermaid.initialize({{
                        startOnLoad: true,
                        theme: 'default',
                        securityLevel: 'loose',
                        fontFamily: 'Arial, sans-serif'
                    }});
                </script>
            </body>
            </html>
            """
            
            print("📄 Loading HTML content...")
            await page.set_content(html_template)
            
            print("⏳ Waiting for Mermaid to render (5 seconds)...")
            await page.wait_for_timeout(5000)  # Increased timeout
            
            # Check if page loaded
            title = await page.title()
            print(f"Page title: {title}")
            
            # Check for errors
            print("🔍 Checking for JavaScript errors...")
            
            # Look for SVG element
            svg_element = await page.query_selector('svg')
            if svg_element:
                print("✅ SVG element found!")
                
                # Try different methods to get SVG content
                try:
                    svg_content = await svg_element.get_attribute('outerHTML')
                    if svg_content:
                        print(f"SVG content length: {len(svg_content)}")
                        print(f"SVG preview: {svg_content[:200]}...")
                    else:
                        print("⚠️ outerHTML is None, trying innerHTML...")
                        svg_content = await svg_element.inner_html()
                        if svg_content:
                            print(f"SVG innerHTML length: {len(svg_content)}")
                        else:
                            print("❌ Both outerHTML and innerHTML are None")
                            
                            # Check if there's an error in the SVG
                            error_elem = await page.query_selector('.mermaid-error, .error')
                            if error_elem:
                                error_text = await error_elem.inner_text()
                                print(f"🚨 Mermaid error found: {error_text}")
                            
                            # Get the mermaid div content to see what happened
                            mermaid_div = await page.query_selector('.mermaid')
                            if mermaid_div:
                                mermaid_html = await mermaid_div.inner_html()
                                print(f"🔍 Mermaid div content: {mermaid_html[:300]}...")
                
                except Exception as e:
                    print(f"❌ Error getting SVG content: {e}")
                
                await browser.close()
                return True
            else:
                print("❌ No SVG element found!")
                
                # Debug: Check what's actually in the page
                page_content = await page.content()
                print("🔍 Page content preview:")
                print(page_content[:1000])
                
                # Check for Mermaid errors
                mermaid_div = await page.query_selector('.mermaid')
                if mermaid_div:
                    mermaid_content = await mermaid_div.inner_html()
                    print(f"🔍 Mermaid div content: {mermaid_content}")
                
                await browser.close()
                return False
                
    except Exception as e:
        print(f"❌ Playwright test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_simple_mermaid():
    """Test with a very simple Mermaid syntax to isolate the issue"""
    print("\n🧪 Testing with simple Mermaid syntax...")
    
    simple_syntax = "graph TD\n    A --> B"
    
    try:
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            html_template = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
            </head>
            <body>
                <div class="mermaid">{simple_syntax}</div>
                <script>
                    mermaid.initialize({{ startOnLoad: true, theme: 'default' }});
                </script>
            </body>
            </html>
            """
            
            await page.set_content(html_template)
            await page.wait_for_timeout(3000)
            
            svg_element = await page.query_selector('svg')
            if svg_element:
                print("✅ Simple syntax works!")
                await browser.close()
                return True
            else:
                print("❌ Simple syntax also fails!")
                await browser.close()
                return False
                
    except Exception as e:
        print(f"❌ Simple test failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("🔬 ISOLATED PLAYWRIGHT MERMAID TEST")
    print("=" * 60)
    
    result1 = asyncio.run(test_playwright_mermaid())
    result2 = asyncio.run(test_simple_mermaid())
    
    print("\n" + "=" * 60)
    if result1 and result2:
        print("✅ Playwright Mermaid rendering works!")
    elif result2:
        print("⚠️ Simple syntax works, but complex syntax fails")
    else:
        print("❌ Playwright Mermaid rendering completely broken")