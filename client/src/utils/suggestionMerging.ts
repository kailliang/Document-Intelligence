// Utility functions for merging overlapping suggestions

interface Suggestion {
  id: string;
  type: string;
  severity: 'high' | 'medium' | 'low';
  paragraph: number;
  description: string;
  original_text: string;
  replace_to: string;
  confidence: number;
  agent: 'technical' | 'legal' | 'novelty' | 'lead';
  created_at: string;
}

interface TextRange {
  start: number;
  end: number;
  text: string;
}

interface MergedSuggestion extends Suggestion {
  mergedIds: string[];
  mergedDescriptions: string[];
  mergedTypes: string[];
  highestSeverity: 'high' | 'medium' | 'low';
  averageConfidence: number;
}

/**
 * Check if two text ranges overlap
 */
function rangesOverlap(range1: TextRange, range2: TextRange): boolean {
  return range1.start < range2.end && range2.start < range1.end;
}

/**
 * Calculate text similarity between two strings
 */
function calculateTextSimilarity(text1: string, text2: string): number {
  const normalize = (text: string) => text.toLowerCase().replace(/\s+/g, ' ').trim();
  const norm1 = normalize(text1);
  const norm2 = normalize(text2);
  
  if (norm1 === norm2) return 1.0;
  
  // Check if one text contains the other
  if (norm1.includes(norm2) || norm2.includes(norm1)) return 0.8;
  
  // Simple Jaccard similarity for words
  const words1 = new Set(norm1.split(' '));
  const words2 = new Set(norm2.split(' '));
  const intersection = new Set([...words1].filter(x => words2.has(x)));
  const union = new Set([...words1, ...words2]);
  
  return intersection.size / union.size;
}

/**
 * Get severity priority (higher number = higher priority)
 */
function getSeverityPriority(severity: string): number {
  switch (severity) {
    case 'high': return 3;
    case 'medium': return 2;
    case 'low': return 1;
    default: return 0;
  }
}

/**
 * Get the highest severity from a list of severities
 */
function getHighestSeverity(severities: string[]): 'high' | 'medium' | 'low' {
  const priorities = severities.map(getSeverityPriority);
  const maxPriority = Math.max(...priorities);
  
  switch (maxPriority) {
    case 3: return 'high';
    case 2: return 'medium';
    case 1: return 'low';
    default: return 'medium';
  }
}

/**
 * Find text ranges in document content
 */
function findTextRange(content: string, searchText: string): TextRange | null {
  const normalizedContent = content.toLowerCase();
  const normalizedSearch = searchText.toLowerCase();
  
  const index = normalizedContent.indexOf(normalizedSearch);
  if (index === -1) return null;
  
  return {
    start: index,
    end: index + searchText.length,
    text: searchText
  };
}

/**
 * Merge suggestions that target overlapping or very similar text
 */
export function mergeSuggestions(
  suggestions: Suggestion[],
  documentContent: string,
  similarityThreshold: number = 0.7
): MergedSuggestion[] {
  console.log(`🔄 Merging ${suggestions.length} suggestions with threshold ${similarityThreshold}`);
  
  const mergedSuggestions: MergedSuggestion[] = [];
  const processedIds = new Set<string>();
  
  for (const suggestion of suggestions) {
    if (processedIds.has(suggestion.id)) continue;
    
    // Find the text range for this suggestion
    const mainRange = findTextRange(documentContent, suggestion.original_text);
    if (!mainRange) {
      console.warn(`⚠️ Could not find text range for suggestion: ${suggestion.id}`);
      // Add as standalone suggestion
      mergedSuggestions.push({
        ...suggestion,
        mergedIds: [suggestion.id],
        mergedDescriptions: [suggestion.description],
        mergedTypes: [suggestion.type],
        highestSeverity: suggestion.severity,
        averageConfidence: suggestion.confidence
      });
      processedIds.add(suggestion.id);
      continue;
    }
    
    // Find overlapping suggestions
    const overlappingSuggestions = suggestions.filter(otherSuggestion => {
      if (processedIds.has(otherSuggestion.id) || otherSuggestion.id === suggestion.id) {
        return false;
      }
      
      const otherRange = findTextRange(documentContent, otherSuggestion.original_text);
      if (!otherRange) return false;
      
      // Check for overlap or high text similarity
      const hasOverlap = rangesOverlap(mainRange, otherRange);
      const textSimilarity = calculateTextSimilarity(
        suggestion.original_text, 
        otherSuggestion.original_text
      );
      
      return hasOverlap || textSimilarity >= similarityThreshold;
    });
    
    if (overlappingSuggestions.length === 0) {
      // No overlaps, add as standalone
      mergedSuggestions.push({
        ...suggestion,
        mergedIds: [suggestion.id],
        mergedDescriptions: [suggestion.description],
        mergedTypes: [suggestion.type],
        highestSeverity: suggestion.severity,
        averageConfidence: suggestion.confidence
      });
      processedIds.add(suggestion.id);
    } else {
      // Merge with overlapping suggestions
      const allSuggestions = [suggestion, ...overlappingSuggestions];
      const allIds = allSuggestions.map(s => s.id);
      const allDescriptions = allSuggestions.map(s => s.description);
      const allTypes = [...new Set(allSuggestions.map(s => s.type))];
      const allSeverities = allSuggestions.map(s => s.severity);
      const allConfidences = allSuggestions.map(s => s.confidence);
      
      // Mark all as processed
      allIds.forEach(id => processedIds.add(id));
      
      // Create merged suggestion using the main suggestion as base
      const mergedSuggestion: MergedSuggestion = {
        ...suggestion,
        id: `merged-${allIds.join('-')}`,
        description: allDescriptions.join(' | '),
        type: allTypes.join(' & '),
        severity: getHighestSeverity(allSeverities),
        confidence: allConfidences.reduce((sum, conf) => sum + conf, 0) / allConfidences.length,
        mergedIds: allIds,
        mergedDescriptions: allDescriptions,
        mergedTypes: allTypes,
        highestSeverity: getHighestSeverity(allSeverities),
        averageConfidence: allConfidences.reduce((sum, conf) => sum + conf, 0) / allConfidences.length
      };
      
      mergedSuggestions.push(mergedSuggestion);
      console.log(`✅ Merged ${allIds.length} suggestions into: ${mergedSuggestion.id}`);
    }
  }
  
  console.log(`🎯 Final result: ${mergedSuggestions.length} merged suggestions`);
  return mergedSuggestions;
}

/**
 * Check if two suggestions should be merged based on text overlap and similarity
 */
export function shouldMergeSuggestions(
  suggestion1: Suggestion,
  suggestion2: Suggestion,
  documentContent: string,
  similarityThreshold: number = 0.7
): boolean {
  const range1 = findTextRange(documentContent, suggestion1.original_text);
  const range2 = findTextRange(documentContent, suggestion2.original_text);
  
  if (!range1 || !range2) return false;
  
  // Check for overlap
  if (rangesOverlap(range1, range2)) return true;
  
  // Check for text similarity
  const similarity = calculateTextSimilarity(
    suggestion1.original_text,
    suggestion2.original_text
  );
  
  return similarity >= similarityThreshold;
}

/**
 * Get merged replacement text for overlapping suggestions
 */
export function getMergedReplacement(
  suggestions: Suggestion[]
): string {
  if (suggestions.length === 0) return '';
  if (suggestions.length === 1) return suggestions[0].replace_to;
  
  // For multiple suggestions, prioritize by severity and confidence
  const sortedSuggestions = suggestions.sort((a, b) => {
    const severityDiff = getSeverityPriority(b.severity) - getSeverityPriority(a.severity);
    if (severityDiff !== 0) return severityDiff;
    return b.confidence - a.confidence;
  });
  
  // Use the highest priority suggestion's replacement
  return sortedSuggestions[0].replace_to;
}