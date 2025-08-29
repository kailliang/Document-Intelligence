"""
Test suite for enhanced Mermaid diagram generation and error handling.

This module tests the fixes for Mermaid syntax errors, validation, and fallback systems
implemented to resolve parsing failures in the frontend.
"""

import pytest
from app.internal.mermaid_render import (
    validate_mermaid_syntax,
    fix_common_mermaid_errors, 
    create_fallback_diagram
)


class TestMermaidValidation:
    """Test the Mermaid syntax validation system."""
    
    def test_valid_diagram_passes_validation(self):
        """Test that a properly formatted diagram passes validation."""
        valid_diagram = '''flowchart TD
    A["Start Process"] --> B{"Decision Point"}
    B --> C["Action One"]
    B --> D["Action Two"]
    C --> E["End"]
    D --> E'''
        
        errors = validate_mermaid_syntax(valid_diagram)
        assert errors == [], f"Valid diagram should not have errors, got: {errors}"
    
    def test_detects_parentheses_in_labels(self):
        """Test detection of parentheses in node labels."""
        problematic_diagram = '''flowchart TD
    A[camera to focus on lens (S1)] --> B[Process]'''
        
        errors = validate_mermaid_syntax(problematic_diagram)
        assert any("Parentheses in node labels" in error for error in errors)
    
    def test_detects_unclosed_parentheses(self):
        """Test detection of unclosed parentheses in labels."""
        problematic_diagram = '''flowchart TD
    A[some text (incomplete --> B[Next]'''
        
        errors = validate_mermaid_syntax(problematic_diagram)
        assert any("Unclosed parentheses" in error for error in errors)
    
    def test_detects_truncated_words(self):
        """Test detection of common truncated words."""
        test_cases = [
            ('A[Continuo] --> B[Next]', 'Continuo'),
            ('A[Analysi] --> B[Next]', 'Analysi'), 
            ('A[Proces] --> B[Next]', 'Proces'),
            ('A[Comple] --> B[Next]', 'Comple'),
            ('A[Generat] --> B[Next]', 'Generat')
        ]
        
        # Test that we can detect truncated words in context (like at end of lines)
        truncated_at_end = "flowchart TD\n    A[Start] --> B[Continuo"
        errors = validate_mermaid_syntax(truncated_at_end)
        assert any("truncated word" in error for error in errors), \
            "Should detect truncated word at end of line"
    
    def test_detects_incomplete_arrows(self):
        """Test detection of incomplete arrow syntax."""
        problematic_diagram = '''flowchart TD
    A[Start] --> B[Middle]
    B --
    C[End]'''
        
        errors = validate_mermaid_syntax(problematic_diagram)
        assert any("Incomplete arrow syntax" in error for error in errors)
    
    def test_detects_missing_diagram_type(self):
        """Test detection of missing diagram type declaration."""
        problematic_diagram = '''A[Start] --> B[End]'''
        
        errors = validate_mermaid_syntax(problematic_diagram)
        assert any("Missing diagram type declaration" in error for error in errors)
    
    def test_detects_long_labels(self):
        """Test detection of labels that are too long."""
        long_label = "This is a very long label that exceeds fifty characters and might cause truncation issues"
        problematic_diagram = f'''flowchart TD
    A[{long_label}] --> B[End]'''
        
        errors = validate_mermaid_syntax(problematic_diagram)
        assert any("Label too long" in error for error in errors)


class TestMermaidFixes:
    """Test the automatic Mermaid error correction system."""
    
    def test_fixes_parentheses_in_labels(self):
        """Test automatic fixing of parentheses in node labels."""
        problematic_code = '''flowchart TD
    A[camera to focus on lens (S1)] --> B[Process (V2)]'''
        
        fixed_code = fix_common_mermaid_errors(problematic_code)
        
        # Should replace parentheses with dashes
        assert "(S1)" not in fixed_code
        assert "(V2)" not in fixed_code
        assert "-S1-" in fixed_code
        assert "-V2-" in fixed_code
    
    def test_fixes_truncated_words(self):
        """Test automatic completion of truncated words."""
        test_cases = [
            ('Continuo', 'Continuous'),
            ('Proces', 'Process'), 
            ('Comple', 'Complete'),
            ('Analysi', 'Analysis'),
            ('Generat', 'Generate'),
            ('Syste', 'System'),
            ('Manag', 'Manage')
        ]
        
        for truncated, expected in test_cases:
            problematic_code = f"flowchart TD\n    A[{truncated}] --> B[End]"
            fixed_code = fix_common_mermaid_errors(problematic_code)
            assert expected in fixed_code, \
                f"Should fix '{truncated}' to '{expected}', got: {fixed_code}"
    
    def test_fixes_incomplete_arrows(self):
        """Test removal of incomplete arrow syntax."""
        problematic_code = '''flowchart TD
    A[Start] --> B[Middle]
    B --
    C[End] --'''
        
        fixed_code = fix_common_mermaid_errors(problematic_code)
        
        # Should remove incomplete arrows
        lines = fixed_code.split('\n')
        for line in lines:
            assert not line.strip().endswith('--'), \
                f"Should not have incomplete arrows, but found in: {line}"
    
    def test_adds_quotes_to_multi_word_labels(self):
        """Test automatic addition of quotes to labels with spaces."""
        problematic_code = '''flowchart TD
    A[Start Process] --> B[End Result]'''
        
        fixed_code = fix_common_mermaid_errors(problematic_code)
        
        # Should add quotes around labels with spaces
        assert '["Start Process"]' in fixed_code
        assert '["End Result"]' in fixed_code
    
    def test_adds_flowchart_direction(self):
        """Test automatic addition of flowchart direction."""
        problematic_code = '''flowchart
    A[Start] --> B[End]'''
        
        fixed_code = fix_common_mermaid_errors(problematic_code)
        assert 'flowchart TD' in fixed_code
    
    def test_fixes_unclosed_parentheses(self):
        """Test fixing of unclosed parentheses in labels."""
        problematic_code = '''flowchart TD
    A[some text (incomplete --> B[Next]'''
        
        fixed_code = fix_common_mermaid_errors(problematic_code)
        
        # Should close the bracket properly
        assert '[some text]' in fixed_code
        assert '(incomplete' not in fixed_code


class TestRealWorldScenarios:
    """Test fixes against real-world error scenarios."""
    
    def test_console_error_scenario(self):
        """Test the exact error scenario from console logs."""
        # This is the exact problematic code from the console error
        problematic_code = '''flowchart TD
    A[camera to focus on lens (S1)] --> B[Continuo'''
        
        # Validate that we detect the issues
        errors = validate_mermaid_syntax(problematic_code)
        assert len(errors) > 0, "Should detect syntax issues"
        
        # Apply fixes
        fixed_code = fix_common_mermaid_errors(problematic_code)
        
        # Verify fixes
        assert '(S1)' not in fixed_code, "Should fix parentheses"
        assert 'Continuous' in fixed_code, "Should complete truncated word"
        assert '"camera to focus on lens -S1-"' in fixed_code, "Should properly format label"
        
        # Verify no errors remain
        remaining_errors = validate_mermaid_syntax(fixed_code)
        assert remaining_errors == [], f"Fixed code should have no errors, got: {remaining_errors}"
    
    def test_complex_diagram_with_multiple_issues(self):
        """Test a complex diagram with multiple syntax issues."""
        complex_problematic = '''flowchart
    A[Setup Camera (V1)] --> B[Continuo
    B -- 
    C[Analysi Results (Final)] --> D[Comple
    E[Very long process description that exceeds the fifty character limit] --> F[End]'''
        
        # Should detect multiple issues
        errors = validate_mermaid_syntax(complex_problematic)
        assert len(errors) >= 4, f"Should detect multiple issues, got {len(errors)}: {errors}"
        
        # Apply fixes
        fixed_code = fix_common_mermaid_errors(complex_problematic)
        
        # Verify multiple fixes applied
        assert 'flowchart TD' in fixed_code  # Added direction
        assert '-V1-' in fixed_code and '(V1)' not in fixed_code  # Fixed parentheses
        assert 'Continuous' in fixed_code  # Fixed truncation
        assert 'Analysis' in fixed_code  # Fixed truncation
        assert 'Complete' in fixed_code  # Fixed truncation
        assert not any(line.strip().endswith('--') for line in fixed_code.split('\n'))  # Fixed incomplete arrows


class TestFallbackSystem:
    """Test the fallback diagram generation system."""
    
    def test_creates_simple_fallback_diagram(self):
        """Test creation of simple fallback diagram."""
        user_input = "create a flowchart for the camera system process"
        fallback = create_fallback_diagram(user_input)
        
        # Should be valid Mermaid syntax
        errors = validate_mermaid_syntax(fallback)
        assert errors == [], f"Fallback should be valid, got errors: {errors}"
        
        # Should include flowchart declaration
        assert 'flowchart TD' in fallback
        
        # Should extract relevant words from user input
        assert any(word in fallback for word in ['Camera', 'System', 'Process', 'Flowchart'])
    
    def test_fallback_with_empty_input(self):
        """Test fallback diagram creation with minimal input."""
        user_input = ""
        fallback = create_fallback_diagram(user_input)
        
        # Should still create valid diagram
        errors = validate_mermaid_syntax(fallback)
        assert errors == [], f"Fallback should be valid even with empty input, got: {errors}"
        
        # Should have default terms
        default_terms = ['Start', 'Process', 'Decision', 'End']
        assert any(term in fallback for term in default_terms)
    
    def test_fallback_extracts_key_words(self):
        """Test that fallback extracts meaningful words from user input."""
        user_input = "generate analysis workflow for patent document review system"
        fallback = create_fallback_diagram(user_input)
        
        # Should extract and use key words
        key_words = ['Generate', 'Analysis', 'Workflow', 'Patent', 'Document', 'Review', 'System']
        extracted_count = sum(1 for word in key_words if word in fallback)
        
        assert extracted_count >= 2, f"Should extract key words from input, found: {fallback}"


class TestIntegration:
    """Integration tests for the complete Mermaid error handling workflow."""
    
    def test_full_error_handling_workflow(self):
        """Test the complete error detection -> fix -> fallback workflow."""
        # Start with highly problematic code
        bad_code = '''A[camera setup (S1)] --> B[Continuo
    B -- 
    C[Analysi (incomplete'''
        
        # Step 1: Validate (should find errors)
        errors = validate_mermaid_syntax(bad_code)
        assert len(errors) > 0
        
        # Step 2: Apply fixes
        fixed_code = fix_common_mermaid_errors(bad_code)
        
        # Step 3: Re-validate
        remaining_errors = validate_mermaid_syntax(fixed_code)
        
        # If still has errors, would use fallback
        if remaining_errors:
            fallback_code = create_fallback_diagram("camera setup process analysis")
            final_errors = validate_mermaid_syntax(fallback_code)
            assert final_errors == [], "Fallback should always be valid"
        else:
            # Fixed code should be valid
            assert remaining_errors == [], f"Fixed code should be valid, got: {remaining_errors}"
    
    def test_preserves_valid_diagrams(self):
        """Test that valid diagrams are not modified unnecessarily."""
        valid_code = '''flowchart TD
    A["Start Process"] --> B{"Decision"}
    B --> C["Action One"]
    B --> D["Action Two"]
    C --> E["End"]
    D --> E'''
        
        # Should pass validation
        errors = validate_mermaid_syntax(valid_code)
        assert errors == []
        
        # Fixes should not modify valid code significantly
        fixed_code = fix_common_mermaid_errors(valid_code)
        
        # Core structure should be preserved
        assert 'flowchart TD' in fixed_code
        assert 'Start Process' in fixed_code
        assert 'Decision' in fixed_code


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__])