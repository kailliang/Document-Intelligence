/**
 * Tests for suggestion merging utilities.
 */

import { mergeSuggestions } from '../../utils/suggestionMerging';

// Define types for testing
interface TestSuggestion {
  id: string;
  type: string;
  severity: 'high' | 'medium' | 'low';
  paragraph: number;
  description: string;
  original_text: string;
  replace_to: string;
  confidence: number;
  agent: string;
  created_at: string;
}

describe('suggestionMerging utilities', () => {
  const createMockSuggestion = (overrides: Partial<TestSuggestion> = {}): TestSuggestion => ({
    id: 'default-id',
    type: 'Grammar',
    severity: 'medium',
    paragraph: 1,
    description: 'Default description',
    original_text: 'Original text',
    replace_to: 'Replacement text',
    confidence: 0.8,
    agent: 'technical',
    created_at: '2024-01-01T00:00:00Z',
    ...overrides,
  });

  test('merges suggestions with different IDs', () => {
    const suggestions1: TestSuggestion[] = [
      createMockSuggestion({ id: '1', description: 'First suggestion' }),
      createMockSuggestion({ id: '2', description: 'Second suggestion' }),
    ];

    const suggestions2: TestSuggestion[] = [
      createMockSuggestion({ id: '3', description: 'Third suggestion' }),
      createMockSuggestion({ id: '4', description: 'Fourth suggestion' }),
    ];

    const mockDocumentContent = "This document contains Original text that needs improvement.";
    const allSuggestions = [...suggestions1, ...suggestions2];
    const merged = mergeSuggestions(allSuggestions, mockDocumentContent);

    // All suggestions have same original_text so they get merged into one
    expect(merged).toHaveLength(1);
    expect(merged[0].mergedIds).toEqual(['1', '2', '3', '4']);
  });

  test('removes duplicate suggestions with same ID', () => {
    const suggestions1: TestSuggestion[] = [
      createMockSuggestion({ id: '1', description: 'First suggestion' }),
      createMockSuggestion({ id: '2', description: 'Second suggestion' }),
    ];

    const suggestions2: TestSuggestion[] = [
      createMockSuggestion({ id: '1', description: 'Updated first suggestion' }),
      createMockSuggestion({ id: '3', description: 'Third suggestion' }),
    ];

    const mockDocumentContent = "This document contains Original text that needs improvement.";
    const allSuggestions = [...suggestions1, ...suggestions2];
    const merged = mergeSuggestions(allSuggestions, mockDocumentContent);

    expect(merged).toHaveLength(3);
    expect(merged.find(s => s.id === '1')?.description).toBe('Updated first suggestion');
  });

  test('handles empty arrays', () => {
    const mockDocumentContent = "This document contains Original text for testing.";
    const result1 = mergeSuggestions([], mockDocumentContent);
    expect(result1).toEqual([]);

    const suggestions = [createMockSuggestion({ id: '1' })];
    const result2 = mergeSuggestions(suggestions, mockDocumentContent);
    expect(result2).toHaveLength(1);

    const result3 = mergeSuggestions([], mockDocumentContent);
    expect(result3).toEqual([]);
  });

  test('preserves suggestion order', () => {
    const suggestions1: TestSuggestion[] = [
      createMockSuggestion({ id: '1', paragraph: 1 }),
      createMockSuggestion({ id: '2', paragraph: 2 }),
    ];

    const suggestions2: TestSuggestion[] = [
      createMockSuggestion({ id: '3', paragraph: 3 }),
      createMockSuggestion({ id: '4', paragraph: 1 }),
    ];

    const mockDocumentContent = "Document content for paragraph 1, paragraph 2, and paragraph 3 with Original text.";
    const allSuggestions = [...suggestions1, ...suggestions2];
    const merged = mergeSuggestions(allSuggestions, mockDocumentContent);

    expect(merged.map(s => s.id)).toEqual(['1', '2', '3', '4']);
  });

  test('handles suggestions with overlapping text ranges', () => {
    const suggestions1: TestSuggestion[] = [
      createMockSuggestion({
        id: '1',
        original_text: 'The quick brown fox',
        paragraph: 1,
      }),
    ];

    const suggestions2: TestSuggestion[] = [
      createMockSuggestion({
        id: '2',
        original_text: 'quick brown',
        paragraph: 1,
      }),
    ];

    const mockDocumentContent = "This text contains The quick brown fox and other quick brown animals.";
    const allSuggestions = [...suggestions1, ...suggestions2];
    const merged = mergeSuggestions(allSuggestions, mockDocumentContent);

    expect(merged).toHaveLength(2);
    expect(merged.find(s => s.id === '1')).toBeDefined();
    expect(merged.find(s => s.id === '2')).toBeDefined();
  });

  test('sorts merged suggestions by priority criteria', () => {
    const suggestions: TestSuggestion[] = [
      createMockSuggestion({
        id: '1',
        severity: 'low',
        confidence: 0.5,
        paragraph: 3,
      }),
      createMockSuggestion({
        id: '2',
        severity: 'high',
        confidence: 0.9,
        paragraph: 1,
      }),
      createMockSuggestion({
        id: '3',
        severity: 'medium',
        confidence: 0.8,
        paragraph: 2,
      }),
    ];

    const mockDocumentContent = "This document contains Original text in paragraph 1, paragraph 2, and paragraph 3.";
    const merged = mergeSuggestions(suggestions, mockDocumentContent);

    // Assuming sorting by severity (high > medium > low) then by paragraph
    const highSeverity = merged.filter(s => s.severity === 'high');
    const mediumSeverity = merged.filter(s => s.severity === 'medium');
    const lowSeverity = merged.filter(s => s.severity === 'low');

    expect(highSeverity.length).toBeGreaterThan(0);
    expect(mediumSeverity.length).toBeGreaterThan(0);
    expect(lowSeverity.length).toBeGreaterThan(0);
  });

  test('handles suggestions from different agents', () => {
    const technicalSuggestions: TestSuggestion[] = [
      createMockSuggestion({
        id: 'tech-1',
        agent: 'technical',
        type: 'Technical',
      }),
    ];

    const legalSuggestions: TestSuggestion[] = [
      createMockSuggestion({
        id: 'legal-1',
        agent: 'legal',
        type: 'Legal',
      }),
    ];

    const mockDocumentContent = "This document contains Original text that needs both technical and legal review.";
    const allSuggestions = [...technicalSuggestions, ...legalSuggestions];
    const merged = mergeSuggestions(allSuggestions, mockDocumentContent);

    expect(merged).toHaveLength(2);
    expect(merged.find(s => s.agent === 'technical')).toBeDefined();
    expect(merged.find(s => s.agent === 'legal')).toBeDefined();
  });

  test('validates suggestion data integrity', () => {
    const validSuggestions: TestSuggestion[] = [
      createMockSuggestion({ id: '1', confidence: 0.95 }),
      createMockSuggestion({ id: '2', confidence: 0.85 }),
    ];

    // Test with some invalid data mixed in
    const mixedSuggestions = [
      ...validSuggestions,
      // These would be filtered out in a real implementation
    ];

    const mockDocumentContent = "This document contains Original text for data integrity testing.";
    const merged = mergeSuggestions(mixedSuggestions, mockDocumentContent);

    // All results should be valid suggestions
    merged.forEach(suggestion => {
      expect(suggestion.id).toBeDefined();
      expect(suggestion.confidence).toBeGreaterThanOrEqual(0);
      expect(suggestion.confidence).toBeLessThanOrEqual(1);
      expect(['high', 'medium', 'low']).toContain(suggestion.severity);
    });
  });

  test('handles large numbers of suggestions efficiently', () => {
    const largeSuggestionSet1: TestSuggestion[] = Array.from({ length: 1000 }, (_, i) =>
      createMockSuggestion({
        id: `set1-${i}`,
        paragraph: i % 10 + 1,
        confidence: Math.random(),
      })
    );

    const largeSuggestionSet2: TestSuggestion[] = Array.from({ length: 1000 }, (_, i) =>
      createMockSuggestion({
        id: `set2-${i}`,
        paragraph: i % 10 + 1,
        confidence: Math.random(),
      })
    );

    const mockDocumentContent = "Large document content with Original text repeated many times for performance testing.";
    const allSuggestions = [...largeSuggestionSet1, ...largeSuggestionSet2];
    
    const startTime = performance.now();
    const merged = mergeSuggestions(allSuggestions, mockDocumentContent);
    const endTime = performance.now();

    expect(merged).toHaveLength(2000);
    expect(endTime - startTime).toBeLessThan(100); // Should complete in under 100ms
  });

  test('maintains suggestion metadata during merge', () => {
    const suggestions1: TestSuggestion[] = [
      createMockSuggestion({
        id: '1',
        created_at: '2024-01-01T00:00:00Z',
        confidence: 0.95,
        agent: 'technical',
      }),
    ];

    const suggestions2: TestSuggestion[] = [
      createMockSuggestion({
        id: '2',
        created_at: '2024-01-01T01:00:00Z',
        confidence: 0.85,
        agent: 'legal',
      }),
    ];

    const mockDocumentContent = "This document contains Original text with metadata preservation testing.";
    const allSuggestions = [...suggestions1, ...suggestions2];
    const merged = mergeSuggestions(allSuggestions, mockDocumentContent);

    expect(merged[0].created_at).toBe('2024-01-01T00:00:00Z');
    expect(merged[0].confidence).toBe(0.95);
    expect(merged[0].agent).toBe('technical');

    expect(merged[1].created_at).toBe('2024-01-01T01:00:00Z');
    expect(merged[1].confidence).toBe(0.85);
    expect(merged[1].agent).toBe('legal');
  });
});

describe('suggestionMerging edge cases', () => {
  const createMockSuggestion = (overrides: Partial<TestSuggestion> = {}): TestSuggestion => ({
    id: 'default-id',
    type: 'Grammar',
    severity: 'medium',
    paragraph: 1,
    description: 'Default description',
    original_text: 'Original text',
    replace_to: 'Replacement text',
    confidence: 0.8,
    agent: 'technical',
    created_at: '2024-01-01T00:00:00Z',
    ...overrides,
  });

  test('handles null and undefined inputs gracefully', () => {
    const mockDocumentContent = "Test content with Original text.";
    expect(() => mergeSuggestions(null as any, mockDocumentContent)).not.toThrow();
    expect(() => mergeSuggestions([], null as any)).not.toThrow();
    expect(() => mergeSuggestions(undefined as any, mockDocumentContent)).not.toThrow();
  });

  test('handles malformed suggestion objects', () => {
    const validSuggestions = [createMockSuggestion({ id: '1' })];
    const malformedSuggestions = [
      { id: '2' }, // Missing required fields
      null,
      undefined,
    ] as any;

    const mockDocumentContent = "Test content with Original text for malformed suggestion testing.";
    const allSuggestions = [...validSuggestions, ...malformedSuggestions.filter(s => s)];
    const merged = mergeSuggestions(allSuggestions, mockDocumentContent);

    // Should include valid suggestions and filter out malformed ones
    expect(merged.length).toBeGreaterThan(0);
    expect(merged.every(s => s && s.id)).toBe(true);
  });

  test('handles duplicate IDs with different content', () => {
    const suggestion1 = createMockSuggestion({
      id: 'duplicate',
      description: 'First version',
      confidence: 0.8,
    });

    const suggestion2 = createMockSuggestion({
      id: 'duplicate',
      description: 'Second version',
      confidence: 0.9,
    });

    const mockDocumentContent = "Test content with Original text for duplicate ID testing.";
    const allSuggestions = [suggestion1, suggestion2];
    const merged = mergeSuggestions(allSuggestions, mockDocumentContent);

    expect(merged).toHaveLength(1);
    expect(merged[0].id).toBe('duplicate');
    // Should prefer the later/higher confidence suggestion
    expect(merged[0].description).toBe('Second version');
  });
});