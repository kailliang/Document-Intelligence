// Suggestion management service integrating position tracking and word-level diff

import { 
  PositionTracker, 
  Position, 
  TextChange,
  SuggestionPositioning,
  createContextAnchor,
  calculateParagraphIndex,
  calculateSentenceIndex,
  createFingerprint,
  findTextWithFallback,
  verifyPosition
} from '../utils/positionTracker';
import { 
  calculateWordDiff, 
  generateStrikethroughHTML,
  generateStrikethroughPreview,
  findWordPositions,
  DiffResult,
  optimizeDiff
} from '../utils/wordLevelDiff';

export interface AISuggestion {
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

export interface EnhancedSuggestion extends AISuggestion {
  positioning: SuggestionPositioning;
  documentVersion: number;
  status: 'pending' | 'applied' | 'rejected';
  wordDiff?: DiffResult;
  strikethroughPreview?: string;
  strikethroughHTML?: string;
}

export interface ApplyResult {
  success: boolean;
  newText?: string;
  changes?: DiffResult;
  error?: string;
  appliedSuggestion?: EnhancedSuggestion;
}

/**
 * Comprehensive suggestion manager with robust positioning and word-level diff
 */
export class SuggestionManager {
  private suggestions: Map<string, EnhancedSuggestion> = new Map();
  private positionTracker: PositionTracker;
  private appliedSuggestions: Set<string> = new Set();
  private documentVersion: number = 0;
  private currentText: string;
  
  constructor(initialText: string) {
    this.currentText = initialText;
    this.positionTracker = new PositionTracker(initialText);
    console.log('🎯 SuggestionManager initialized with text length:', initialText.length);
  }
  
  /**
   * Add AI suggestions with enhanced positioning and word-level diff
   */
  addSuggestions(suggestions: AISuggestion[]): void {
    console.log(`📝 Adding ${suggestions.length} suggestions to manager`);
    
    suggestions.forEach(suggestion => {
      try {
        const enhanced = this.enhanceSuggestion(suggestion);
        this.suggestions.set(suggestion.id, enhanced);
        console.log(`✅ Enhanced suggestion ${suggestion.id}: ${enhanced.strikethroughPreview}`);
      } catch (error) {
        console.error(`❌ Failed to enhance suggestion ${suggestion.id}:`, error);
      }
    });
    
    console.log(`📊 Total suggestions managed: ${this.suggestions.size}`);
  }
  
  /**
   * Enhance suggestion with positioning and word-level diff
   */
  private enhanceSuggestion(suggestion: AISuggestion): EnhancedSuggestion {
    // Find absolute position in current text
    const absolutePosition = this.findAbsolutePosition(suggestion.original_text);
    
    // Calculate word-level diff
    const wordDiff = optimizeDiff(calculateWordDiff(suggestion.original_text, suggestion.replace_to));
    
    // Generate display formats
    const strikethroughPreview = generateStrikethroughPreview(wordDiff);
    const strikethroughHTML = generateStrikethroughHTML(wordDiff, suggestion.severity);
    
    // Create positioning information
    const positioning: SuggestionPositioning = {
      absolutePosition: absolutePosition || { start: 0, end: 0 },
      characterOffset: absolutePosition?.start || 0,
      contextAnchor: createContextAnchor(this.currentText, suggestion.original_text),
      paragraphIndex: calculateParagraphIndex(this.currentText, suggestion.original_text),
      sentenceIndex: calculateSentenceIndex(this.currentText, suggestion.original_text),
      fingerprint: createFingerprint(suggestion.original_text)
    };
    
    return {
      ...suggestion,
      positioning,
      documentVersion: this.documentVersion,
      status: 'pending',
      wordDiff,
      strikethroughPreview,
      strikethroughHTML
    };
  }
  
  /**
   * Find absolute position of text in document
   */
  private findAbsolutePosition(text: string): Position | null {
    const index = this.currentText.toLowerCase().indexOf(text.toLowerCase());
    if (index === -1) return null;
    
    return {
      start: index,
      end: index + text.length
    };
  }
  
  /**
   * Apply suggestion with robust positioning
   */
  applySuggestion(suggestionId: string, currentText: string): ApplyResult {
    console.log(`🔄 Applying suggestion: ${suggestionId}`);
    
    const suggestion = this.suggestions.get(suggestionId);
    if (!suggestion) {
      return { success: false, error: 'Suggestion not found' };
    }
    
    if (this.appliedSuggestions.has(suggestionId)) {
      return { success: false, error: 'Suggestion already applied' };
    }
    
    try {
      // Update current text reference
      this.currentText = currentText;
      
      // Find current position using multiple strategies
      const position = findTextWithFallback(
        suggestion.original_text,
        currentText,
        suggestion.positioning
      );
      
      if (!position) {
        console.error(`❌ Cannot locate text for suggestion ${suggestionId}`);
        return { success: false, error: 'Cannot locate text in current document' };
      }
      
      // Verify position is still accurate
      if (!verifyPosition(position, suggestion.original_text, currentText)) {
        console.error(`❌ Position verification failed for suggestion ${suggestionId}`);
        return { success: false, error: 'Text position verification failed' };
      }
      
      // Apply replacement
      const beforeText = currentText.substring(0, position.start);
      const afterText = currentText.substring(position.end);
      const newText = beforeText + suggestion.replace_to + afterText;
      
      // Record change for position tracking
      const change: TextChange = {
        originalRange: {
          start: position.start,
          end: position.end,
          length: position.end - position.start
        },
        replacementRange: {
          start: position.start,
          end: position.start + suggestion.replace_to.length,
          length: suggestion.replace_to.length
        },
        originalText: suggestion.original_text,
        replacementText: suggestion.replace_to
      };
      
      this.positionTracker.recordChange(change);
      
      // Update other suggestion positions
      this.updateOtherSuggestionPositions(suggestionId, position, change.replacementRange.length - change.originalRange.length);
      
      // Mark as applied
      this.appliedSuggestions.add(suggestionId);
      suggestion.status = 'applied';
      this.documentVersion++;
      this.currentText = newText;
      
      console.log(`✅ Successfully applied suggestion ${suggestionId}`);
      
      return {
        success: true,
        newText,
        changes: suggestion.wordDiff,
        appliedSuggestion: suggestion
      };
      
    } catch (error) {
      console.error(`❌ Error applying suggestion ${suggestionId}:`, error);
      return {
        success: false,
        error: `Failed to apply suggestion: ${error instanceof Error ? error.message : 'Unknown error'}`
      };
    }
  }
  
  /**
   * Update positions of other suggestions after one is applied
   */
  private updateOtherSuggestionPositions(
    appliedSuggestionId: string,
    appliedPosition: Position,
    offset: number
  ): void {
    console.log(`📍 Updating positions for other suggestions, offset: ${offset}`);
    
    this.suggestions.forEach((suggestion, id) => {
      if (id === appliedSuggestionId || this.appliedSuggestions.has(id)) {
        return;
      }
      
      // Update absolute position
      const currentPosition = suggestion.positioning.absolutePosition;
      if (currentPosition.start > appliedPosition.end) {
        currentPosition.start += offset;
        currentPosition.end += offset;
      }
      
      // Update character offset
      if (suggestion.positioning.characterOffset > appliedPosition.end) {
        suggestion.positioning.characterOffset += offset;
      }
      
      console.log(`📍 Updated position for suggestion ${id}: ${currentPosition.start}-${currentPosition.end}`);
    });
  }
  
  /**
   * Get all suggestions
   */
  getSuggestions(): EnhancedSuggestion[] {
    return Array.from(this.suggestions.values());
  }
  
  /**
   * Get pending suggestions (not applied or rejected)
   */
  getPendingSuggestions(): EnhancedSuggestion[] {
    return this.getSuggestions().filter(s => s.status === 'pending');
  }
  
  /**
   * Get applied suggestions
   */
  getAppliedSuggestions(): EnhancedSuggestion[] {
    return this.getSuggestions().filter(s => s.status === 'applied');
  }
  
  /**
   * Get suggestion by ID
   */
  getSuggestion(id: string): EnhancedSuggestion | undefined {
    return this.suggestions.get(id);
  }
  
  /**
   * Reject a suggestion
   */
  rejectSuggestion(suggestionId: string): void {
    const suggestion = this.suggestions.get(suggestionId);
    if (suggestion) {
      suggestion.status = 'rejected';
      console.log(`❌ Rejected suggestion: ${suggestionId}`);
    }
  }
  
  /**
   * Get word positions for editor highlighting
   */
  getWordPositionsForHighlight(suggestionId: string): Array<{ start: number; end: number; type: 'delete' | 'replace'; originalWord: string }> | null {
    const suggestion = this.suggestions.get(suggestionId);
    if (!suggestion || !suggestion.wordDiff) return null;
    
    return findWordPositions(suggestion.original_text, suggestion.wordDiff);
  }
  
  /**
   * Update current document text
   */
  updateCurrentText(newText: string): void {
    this.currentText = newText;
    console.log(`📄 Document text updated, length: ${newText.length}`);
  }
  
  /**
   * Reset manager for new document
   */
  reset(newText: string): void {
    this.suggestions.clear();
    this.appliedSuggestions.clear();
    this.positionTracker.reset();
    this.currentText = newText;
    this.documentVersion = 0;
    console.log('🔄 SuggestionManager reset for new document');
  }
  
  /**
   * Get statistics
   */
  getStatistics(): {
    total: number;
    pending: number;
    applied: number;
    rejected: number;
    documentVersion: number;
  } {
    const suggestions = this.getSuggestions();
    return {
      total: suggestions.length,
      pending: suggestions.filter(s => s.status === 'pending').length,
      applied: suggestions.filter(s => s.status === 'applied').length,
      rejected: suggestions.filter(s => s.status === 'rejected').length,
      documentVersion: this.documentVersion
    };
  }
  
  /**
   * Validate current state
   */
  validateState(): { valid: boolean; issues: string[] } {
    const issues: string[] = [];
    
    // Check for position conflicts
    const positions = this.getPendingSuggestions().map(s => ({
      id: s.id,
      position: s.positioning.absolutePosition
    }));
    
    for (let i = 0; i < positions.length; i++) {
      for (let j = i + 1; j < positions.length; j++) {
        const pos1 = positions[i].position;
        const pos2 = positions[j].position;
        
        // Check for overlap
        if (pos1.start < pos2.end && pos2.start < pos1.end) {
          issues.push(`Position overlap between suggestions ${positions[i].id} and ${positions[j].id}`);
        }
      }
    }
    
    // Check for invalid positions
    this.getPendingSuggestions().forEach(suggestion => {
      const pos = suggestion.positioning.absolutePosition;
      if (pos.start < 0 || pos.end > this.currentText.length) {
        issues.push(`Invalid position for suggestion ${suggestion.id}: ${pos.start}-${pos.end}`);
      }
    });
    
    return {
      valid: issues.length === 0,
      issues
    };
  }
}