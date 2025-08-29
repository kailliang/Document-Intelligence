"""
Integration tests for Mermaid diagram generation workflow.

This module tests the complete flow from user request to validated Mermaid output,
simulating the real-world scenario where AI generates diagrams that might have syntax errors.
"""

import pytest
from app.internal.mermaid_render import validate_mermaid_syntax, fix_common_mermaid_errors, create_fallback_diagram


class TestMermaidIntegrationWorkflow:
    """Test the complete Mermaid generation and error handling workflow."""
    
    def test_handles_console_error_scenario(self):
        """Test handling of the exact error scenario from user console logs."""
        # This is the exact problematic code that caused parsing failures
        ai_generated_code = '''flowchart TD
    A[camera to focus on lens (S1)] --> B[Continuo'''
        
        # Step 1: Validation should detect issues
        validation_errors = validate_mermaid_syntax(ai_generated_code)
        assert len(validation_errors) >= 1, "Should detect syntax issues"
        
        # Step 2: Apply automatic fixes
        fixed_code = fix_common_mermaid_errors(ai_generated_code)
        
        # Step 3: Verify specific fixes were applied
        assert '(S1)' not in fixed_code, "Should remove parentheses from labels"
        assert '-S1-' in fixed_code, "Should replace parentheses with dashes"
        assert 'Continuous' in fixed_code, "Should complete truncated word 'Continuo'"
        assert 'camera to focus on lens -S1-' in fixed_code, "Should preserve label content"
        
        # Step 4: Final validation should pass
        final_errors = validate_mermaid_syntax(fixed_code)
        assert final_errors == [], f"Fixed code should be valid, got: {final_errors}"
        
        print(f"✅ Successfully fixed: {ai_generated_code.strip()}")
        print(f"✅ Result: {fixed_code.strip()}")
    
    def test_handles_multiple_syntax_issues(self):
        """Test handling diagram with multiple syntax problems."""
        problematic_ai_output = '''flowchart
    A[Setup Process (V1)] --> B[Continuo
    B --
    C[Analysi Results (Final Version)] --> D[Comple'''
        
        # Apply the complete fix workflow
        validation_errors = validate_mermaid_syntax(problematic_ai_output)
        fixed_code = fix_common_mermaid_errors(problematic_ai_output)
        final_errors = validate_mermaid_syntax(fixed_code)
        
        # Verify all major issues were fixed
        assert 'flowchart TD' in fixed_code, "Should add missing direction"
        assert '(V1)' not in fixed_code, "Should fix parentheses"
        assert 'Continuous' in fixed_code, "Should fix truncation"
        assert 'Analysis' in fixed_code, "Should fix truncation"
        assert 'Complete' in fixed_code, "Should fix truncation"
        assert not any(line.strip().endswith('--') for line in fixed_code.split('\n')), \
            "Should fix incomplete arrows"
        
        # Should be valid after fixes
        assert final_errors == [], f"Should be valid after fixes, got: {final_errors}"
    
    def test_fallback_system_integration(self):
        """Test the fallback diagram system for severely broken syntax."""
        # Simulate a case where AI generates completely broken syntax
        broken_code = '''not-a-diagram
    ]][[ invalid syntax everywhere ((()))
    broken arrows -> -> ->'''
        
        # Validation should fail
        errors = validate_mermaid_syntax(broken_code)
        assert len(errors) > 0, "Should detect multiple errors"
        
        # Even after fixes, it might still be broken
        attempted_fix = fix_common_mermaid_errors(broken_code)
        remaining_errors = validate_mermaid_syntax(attempted_fix)
        
        # If still broken, use fallback
        if remaining_errors:
            fallback_code = create_fallback_diagram("create diagram for camera system")
            fallback_errors = validate_mermaid_syntax(fallback_code)
            assert fallback_errors == [], "Fallback should always be valid"
            assert 'flowchart TD' in fallback_code, "Fallback should be proper flowchart"
            
            print(f"✅ Fallback system working: {fallback_code}")
    
    def test_preserves_already_valid_diagrams(self):
        """Test that valid diagrams are not unnecessarily modified."""
        valid_diagram = '''flowchart TD
    A["Start"] --> B{"Decision"}
    B --> C["Action One"]
    B --> D["Action Two"]
    C --> E["End"]
    D --> E'''
        
        # Should pass validation
        errors = validate_mermaid_syntax(valid_diagram)
        assert errors == [], "Valid diagram should not have errors"
        
        # Fixes should not break valid syntax
        processed = fix_common_mermaid_errors(valid_diagram)
        final_errors = validate_mermaid_syntax(processed)
        assert final_errors == [], "Processing should not break valid diagrams"
        
        # Core structure should be preserved
        assert 'flowchart TD' in processed
        assert 'Start' in processed
        assert 'Decision' in processed


if __name__ == "__main__":
    # Allow running integration tests directly
    pytest.main([__file__, "-v"])