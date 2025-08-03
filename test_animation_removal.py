#!/usr/bin/env python3
"""
Test CSS animation removal specifically
"""

import asyncio
import sys
import os

# Add server directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

async def test_animation_removal():
    """Test that CSS animations are properly removed from SVG"""
    print("🎭 Testing CSS Animation Removal")
    print("=" * 50)
    
    try:
        from app.internal.mermaid_render import MermaidRenderer
        
        # Simple syntax for testing
        test_syntax = """graph TD
    A[Device] --> B[Materials]
    A --> C[Windows]"""
        
        renderer = MermaidRenderer()
        
        print("📊 Generating SVG with potential animations...")
        svg_result = await renderer._render_mermaid_to_svg(test_syntax)
        
        if svg_result:
            print(f"✅ SVG Generated, length: {len(svg_result)}")
            
            # Check for animation indicators
            animation_patterns = [
                '@keyframes',
                '@-webkit-keyframes', 
                'animation:',
                'animation-',
                '-webkit-animation',
                'transition:',
                'stroke-dasharray',
                'stroke-dashoffset'
            ]
            
            found_animations = []
            for pattern in animation_patterns:
                if pattern in svg_result:
                    found_animations.append(pattern)
            
            print(f"\n🔍 Animation Check Results:")
            if found_animations:
                print(f"❌ Found animation patterns: {found_animations}")
                
                # Show some context around animations
                for pattern in found_animations[:2]:  # Show first 2
                    idx = svg_result.find(pattern)
                    if idx >= 0:
                        start = max(0, idx - 50)
                        end = min(len(svg_result), idx + 100)
                        context = svg_result[start:end]
                        print(f"📄 Context for '{pattern}': ...{context}...")
            else:
                print("✅ No animation patterns found - animations successfully removed!")
            
            # Check for minimal required SVG elements
            required_elements = ['<svg', '<g', '<rect', '</svg>']
            missing_elements = [elem for elem in required_elements if elem not in svg_result]
            
            if missing_elements:
                print(f"⚠️ Missing required SVG elements: {missing_elements}")
            else:
                print("✅ All required SVG elements present")
                
            return len(found_animations) == 0
            
        else:
            print("❌ SVG generation failed")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 CSS Animation Removal Test")
    print("=" * 60)
    
    success = asyncio.run(test_animation_removal())
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 Test PASSED: Animations successfully removed from SVG")
        print("💡 PDF export should now render diagrams correctly instead of black blocks")
    else:
        print("❌ Test FAILED: Animations still present in SVG")
        print("💡 PDF export may still show diagrams as black blocks")