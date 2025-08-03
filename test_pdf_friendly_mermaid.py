#!/usr/bin/env python3
"""
测试PDF友好的Mermaid渲染
"""

import asyncio
import sys
import os

# Add server directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

async def test_pdf_friendly_mermaid():
    """测试专门为PDF优化的Mermaid渲染"""
    print("🧪 测试PDF友好的Mermaid渲染")
    print("=" * 50)
    
    try:
        from playwright.async_api import async_playwright
        
        # 简化的语法，避免复杂元素
        simple_syntax = """graph TD
    A[Device] --> B[Materials]
    A --> C[Windows]
    D[System] --> A"""
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # 创建专门为PDF优化的HTML
            html_template = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
                <style>
                    body {{ 
                        margin: 20px; 
                        font-family: Arial, sans-serif;
                        background: white;
                    }}
                    .mermaid {{ 
                        text-align: center;
                        background: white;
                    }}
                    /* 移除所有动画 */
                    * {{
                        animation: none !important;
                        transition: none !important;
                    }}
                </style>
            </head>
            <body>
                <div class="mermaid" id="mermaid-diagram">
                    {simple_syntax}
                </div>
                <script>
                    mermaid.initialize({{
                        startOnLoad: true,
                        theme: 'base',
                        securityLevel: 'loose',
                        fontFamily: 'Arial',
                        flowchart: {{
                            htmlLabels: false,
                            curve: 'linear',
                            useMaxWidth: false,
                            nodeSpacing: 60,
                            rankSpacing: 60
                        }},
                        themeVariables: {{
                            primaryColor: '#ffffff',
                            primaryTextColor: '#000000',
                            primaryBorderColor: '#000000',
                            lineColor: '#000000',
                            background: '#ffffff',
                            secondaryColor: '#ffffff'
                        }}
                    }});
                </script>
            </body>
            </html>
            """
            
            print("📄 加载HTML内容...")
            await page.set_content(html_template)
            
            print("⏳ 等待Mermaid渲染...")
            await page.wait_for_timeout(3000)
            
            # 检查渲染结果
            svg_element = await page.query_selector('svg')
            if svg_element:
                print("✅ 找到SVG元素")
                
                # 获取SVG内容
                svg_html = await svg_element.get_attribute('outerHTML')
                if not svg_html:
                    # 备用方法
                    svg_html = f'<svg>{await svg_element.inner_html()}</svg>'
                
                print(f"📏 SVG长度: {len(svg_html)}")
                
                # 检查内容
                has_text = 'Device' in svg_html
                has_graphics = '<rect' in svg_html or '<path' in svg_html
                has_animations = '@keyframes' in svg_html or 'animation' in svg_html
                
                print(f"✅ 包含文本: {has_text}")
                print(f"✅ 包含图形: {has_graphics}")
                print(f"🎭 包含动画: {has_animations}")
                
                if has_animations:
                    print("⚠️ 检测到动画，这可能导致PDF渲染问题")
                
                # 显示SVG片段
                print(f"\n📄 SVG前200字符:")
                print(svg_html[:200])
                
                await browser.close()
                return svg_html
            else:
                print("❌ 未找到SVG元素")
                await browser.close()
                return None
                
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        return None

async def test_minimal_mermaid():
    """测试最小化的Mermaid配置"""
    print("\n🔧 测试最小化Mermaid配置")
    print("=" * 50)
    
    try:
        from playwright.async_api import async_playwright
        
        minimal_syntax = "graph LR\n    A --> B"
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # 最简配置
            html_template = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
            </head>
            <body>
                <div class="mermaid">{minimal_syntax}</div>
                <script>
                    mermaid.initialize({{
                        startOnLoad: true,
                        theme: 'base',
                        securityLevel: 'loose'
                    }});
                </script>
            </body>
            </html>
            """
            
            await page.set_content(html_template)
            await page.wait_for_timeout(2000)
            
            svg_element = await page.query_selector('svg')
            if svg_element:
                svg_html = await svg_element.get_attribute('outerHTML') or f'<svg>{await svg_element.inner_html()}</svg>'
                
                print(f"✅ 最小配置成功，SVG长度: {len(svg_html)}")
                print(f"📄 最小SVG预览: {svg_html[:150]}...")
                
                await browser.close()
                return True
            else:
                print("❌ 最小配置也失败")
                await browser.close()
                return False
                
    except Exception as e:
        print(f"❌ 最小配置测试失败: {str(e)}")
        return False

if __name__ == "__main__":
    print("🔬 PDF友好的Mermaid测试")
    print("=" * 60)
    
    result1 = asyncio.run(test_pdf_friendly_mermaid())
    result2 = asyncio.run(test_minimal_mermaid())
    
    print("\n" + "=" * 60)
    print("🎯 测试结论:")
    
    if result1 and result2:
        print("✅ Mermaid渲染正常")
        print("💡 问题可能在PDF生成阶段，尝试:")
        print("  1. 重启开发服务器")
        print("  2. 清除浏览器缓存")
        print("  3. 检查网络连接")
    else:
        print("❌ Mermaid渲染存在问题，需要进一步调试")