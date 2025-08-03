#!/usr/bin/env python3
"""
检查生成的SVG内容，看看为什么显示为黑色块
"""

import asyncio
import sys
import os

# Add server directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

async def debug_svg_content():
    """检查SVG内容是否正确"""
    print("🔍 DEBUGGING SVG CONTENT")
    print("=" * 50)
    
    try:
        from app.internal.mermaid_render import MermaidRenderer
        
        # 使用文档中的真实语法
        document_syntax = """flowchart TD
    A[Wireless Optogenetic Device] --> B[Body with Light Transducing Materials]
    A --> C[Multiple Optical Windows]
    D[Radiation System] --> E[Radiation Probe]
    D --> F[Movement Mechanism]
    D --> G[Detector]
    D --> H[Controller]
    D -->|Activates| A
    B -->|Up-converts Radiation| C"""
        
        renderer = MermaidRenderer()
        
        print("📊 生成SVG内容...")
        svg_result = await renderer._render_mermaid_to_svg(document_syntax)
        
        if svg_result:
            print(f"✅ SVG生成成功，长度: {len(svg_result)}")
            
            # 检查SVG内容的关键部分
            print("\n🔍 SVG内容分析:")
            
            # 检查SVG标签
            if svg_result.startswith('<svg'):
                print("✅ SVG开始标签正确")
            else:
                print("❌ SVG开始标签错误")
                
            # 检查是否包含实际图形元素
            graphic_elements = ['<g', '<rect', '<path', '<text', '<circle', '<polygon']
            found_elements = [elem for elem in graphic_elements if elem in svg_result]
            
            print(f"📊 找到的图形元素: {found_elements}")
            
            # 检查文本内容
            if 'Wireless' in svg_result:
                print("✅ 包含节点文本")
            else:
                print("❌ 缺少节点文本")
                
            # 检查错误信息
            error_indicators = ['error', 'Error', 'failed', 'Failed', 'undefined']
            found_errors = [err for err in error_indicators if err in svg_result]
            
            if found_errors:
                print(f"🚨 发现错误指示: {found_errors}")
            else:
                print("✅ 无明显错误指示")
                
            # 显示SVG的前500字符和后200字符
            print(f"\n📄 SVG前500字符:")
            print(svg_result[:500])
            print(f"\n📄 SVG后200字符:")
            print(svg_result[-200:])
            
            # 检查viewBox
            if 'viewBox=' in svg_result:
                viewbox_start = svg_result.find('viewBox="') + 9
                viewbox_end = svg_result.find('"', viewbox_start)
                viewbox = svg_result[viewbox_start:viewbox_end]
                print(f"\n📐 ViewBox: {viewbox}")
                
            # 检查是否为空白SVG
            content_size = len(svg_result.replace('<svg', '').replace('</svg>', '').replace(' ', '').replace('\n', ''))
            if content_size < 100:
                print("⚠️ SVG内容可能过于简单或为空")
            else:
                print(f"✅ SVG内容充实 ({content_size} 有效字符)")
                
        else:
            print("❌ SVG生成失败")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ 调试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_simple_vs_complex():
    """对比简单和复杂语法的渲染结果"""
    print("\n🧪 对比简单vs复杂语法")
    print("=" * 50)
    
    test_cases = [
        ("简单", "graph TD\n    A --> B\n    B --> C"),
        ("复杂", """flowchart TD
    A[Wireless Optogenetic Device] --> B[Body with Light Transducing Materials]
    A --> C[Multiple Optical Windows]
    D[Radiation System] --> E[Radiation Probe]
    D --> F[Movement Mechanism]
    D --> G[Detector]
    D --> H[Controller]
    D -->|Activates| A
    B -->|Up-converts Radiation| C""")
    ]
    
    try:
        from app.internal.mermaid_render import MermaidRenderer
        renderer = MermaidRenderer()
        
        for name, syntax in test_cases:
            print(f"\n📊 测试{name}语法:")
            
            svg = await renderer._render_mermaid_to_svg(syntax)
            
            if svg:
                # 检查是否包含文本
                has_text = any(word in svg for word in ['A', 'B', 'Wireless', 'Device'])
                graphic_count = svg.count('<g') + svg.count('<rect') + svg.count('<path')
                
                print(f"  长度: {len(svg)}")
                print(f"  包含文本: {has_text}")
                print(f"  图形元素: {graphic_count}")
                
                if not has_text or graphic_count < 3:
                    print(f"  ⚠️ {name}语法可能渲染异常")
                else:
                    print(f"  ✅ {name}语法渲染正常")
            else:
                print(f"  ❌ {name}语法渲染失败")
                
    except Exception as e:
        print(f"❌ 对比测试失败: {str(e)}")

if __name__ == "__main__":
    print("🔬 SVG渲染调试")
    print("=" * 60)
    
    result1 = asyncio.run(debug_svg_content())
    result2 = asyncio.run(test_simple_vs_complex())
    
    print("\n" + "=" * 60)
    print("🎯 调试结论:")
    
    if result1:
        print("📊 SVG生成过程正常")
        print("💡 问题可能在于:")
        print("  1. Mermaid CDN加载失败")
        print("  2. 复杂语法解析错误")
        print("  3. 网络超时导致不完整渲染")
        print("  4. PDF生成时SVG处理问题")
    else:
        print("❌ SVG生成过程异常，需要检查Playwright设置")