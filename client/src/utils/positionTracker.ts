// Robust position tracking system for handling document changes during suggestion application

export interface Range {
  start: number;
  end: number;
  length: number;
}

export interface Position {
  start: number;
  end: number;
}

export interface TextChange {
  originalRange: Range;
  replacementRange: Range;
  originalText: string;
  replacementText: string;
}

export interface PositionMap {
  version: number;
  originalRange: Range;
  replacementRange: Range;
  offset: number;
  timestamp: number;
}

export interface ContextAnchor {
  before: string;
  target: string;
  after: string;
  hash: string;
}

/**
 * Position tracker: maintains position mapping during document editing
 */
export class PositionTracker {
  private positionMap: PositionMap[] = [];
  private currentVersion: number = 0;
  
  constructor(_initialText: string) {}
  
  /**
   * Record a text change for position tracking
   */
  recordChange(change: TextChange): void {
    const mapping: PositionMap = {
      version: this.currentVersion++,
      originalRange: change.originalRange,
      replacementRange: change.replacementRange,
      offset: change.replacementRange.length - change.originalRange.length,
      timestamp: Date.now()
    };
    
    this.positionMap.push(mapping);
    console.log(`📍 Position change recorded: v${mapping.version}, offset: ${mapping.offset}`);
  }
  
  /**
   * Map original position to current position
   */
  mapPosition(originalPos: number): number {
    let currentPos = originalPos;
    
    // Apply all position changes in order
    for (const mapping of this.positionMap) {
      if (originalPos >= mapping.originalRange.end) {
        // Position is after the change, adjust by offset
        currentPos += mapping.offset;
      } else if (originalPos > mapping.originalRange.start) {
        // Position falls within changed range - problematic!
        console.warn('⚠️ Position falls within a changed range');
        // Return end of replacement range + relative offset
        const relativeOffset = originalPos - mapping.originalRange.start;
        const mappedOffset = Math.min(relativeOffset, mapping.replacementRange.length);
        return mapping.replacementRange.start + mappedOffset;
      }
    }
    
    return Math.max(0, currentPos);
  }
  
  /**
   * Map multiple positions in batch
   */
  mapPositions(positions: Position[]): Position[] {
    return positions.map(pos => ({
      start: this.mapPosition(pos.start),
      end: this.mapPosition(pos.end)
    }));
  }
  
  /**
   * Clear all position mappings (reset tracker)
   */
  reset(): void {
    this.positionMap = [];
    this.currentVersion = 0;
    console.log('📍 Position tracker reset');
  }
  
  /**
   * Get current document version
   */
  getVersion(): number {
    return this.currentVersion;
  }
}

/**
 * Enhanced positioning information for suggestions
 */
export interface SuggestionPositioning {
  absolutePosition: Position;
  characterOffset: number;
  contextAnchor: ContextAnchor | null;
  paragraphIndex: number;
  sentenceIndex: number;
  fingerprint: string;
}

/**
 * Create context anchor for robust text location
 */
export function createContextAnchor(text: string, targetText: string): ContextAnchor | null {
  const position = text.toLowerCase().indexOf(targetText.toLowerCase());
  if (position === -1) return null;
  
  // Get context before and after (50 characters each)
  const beforeStart = Math.max(0, position - 50);
  const afterEnd = Math.min(text.length, position + targetText.length + 50);
  
  const before = text.substring(beforeStart, position);
  const after = text.substring(position + targetText.length, afterEnd);
  
  return {
    before,
    target: targetText,
    after,
    hash: calculateHash(text.substring(beforeStart, afterEnd))
  };
}

/**
 * Find text position using context anchor (most reliable method)
 */
export function findByContextAnchor(
  anchor: ContextAnchor | null,
  currentText: string
): Position | null {
  if (!anchor) return null;
  
  // Try full pattern first
  const fullPattern = `${anchor.before}${anchor.target}${anchor.after}`;
  let index = currentText.indexOf(fullPattern);
  
  if (index !== -1) {
    const start = index + anchor.before.length;
    return {
      start,
      end: start + anchor.target.length
    };
  }
  
  // Try with shorter context
  const shorterBefore = anchor.before.slice(-20);
  const shorterAfter = anchor.after.slice(0, 20);
  const shorterPattern = `${shorterBefore}${anchor.target}${shorterAfter}`;
  
  index = currentText.indexOf(shorterPattern);
  if (index !== -1) {
    const start = index + shorterBefore.length;
    return {
      start,
      end: start + anchor.target.length
    };
  }
  
  // Try target only with case-insensitive search
  const targetIndex = currentText.toLowerCase().indexOf(anchor.target.toLowerCase());
  if (targetIndex !== -1) {
    return {
      start: targetIndex,
      end: targetIndex + anchor.target.length
    };
  }
  
  return null;
}

/**
 * Find text by paragraph and sentence indices
 */
export function findByParagraphAndSentence(
  paragraphIndex: number,
  sentenceIndex: number,
  targetText: string,
  currentText: string
): Position | null {
  const paragraphs = currentText.split(/\n\n+/);
  
  if (paragraphIndex >= paragraphs.length) return null;
  
  const paragraph = paragraphs[paragraphIndex];
  const sentences = paragraph.split(/[.!?]+/);
  
  if (sentenceIndex >= sentences.length) return null;
  
  const sentence = sentences[sentenceIndex];
  const sentenceIndex_in_para = paragraph.indexOf(sentence);
  const paragraphStart = currentText.indexOf(paragraph);
  
  if (paragraphStart === -1 || sentenceIndex_in_para === -1) return null;
  
  const sentenceStart = paragraphStart + sentenceIndex_in_para;
  const targetIndex = sentence.toLowerCase().indexOf(targetText.toLowerCase());
  
  if (targetIndex === -1) return null;
  
  const absoluteStart = sentenceStart + targetIndex;
  return {
    start: absoluteStart,
    end: absoluteStart + targetText.length
  };
}

/**
 * Fuzzy text matching using Levenshtein distance
 */
export function findByFuzzyMatch(
  targetText: string,
  currentText: string,
  threshold: number = 0.8
): Position | null {
  const targetLen = targetText.length;
  Math.max(targetLen, 50);
  
  let bestMatch: { position: Position; score: number } | null = null;
  
  // Slide window across text
  for (let i = 0; i <= currentText.length - targetLen; i++) {
    const candidate = currentText.substring(i, i + targetLen);
    const similarity = calculateSimilarity(targetText.toLowerCase(), candidate.toLowerCase());
    
    if (similarity >= threshold && (!bestMatch || similarity > bestMatch.score)) {
      bestMatch = {
        position: { start: i, end: i + targetLen },
        score: similarity
      };
    }
  }
  
  return bestMatch?.position || null;
}

/**
 * Calculate text similarity using Levenshtein distance
 */
function calculateSimilarity(str1: string, str2: string): number {
  const maxLen = Math.max(str1.length, str2.length);
  if (maxLen === 0) return 1.0;
  
  const distance = levenshteinDistance(str1, str2);
  return 1 - (distance / maxLen);
}

/**
 * Calculate Levenshtein distance between two strings
 */
function levenshteinDistance(str1: string, str2: string): number {
  const m = str1.length;
  const n = str2.length;
  
  const dp: number[][] = Array(m + 1).fill(null).map(() => Array(n + 1).fill(0));
  
  // Initialize base cases
  for (let i = 0; i <= m; i++) dp[i][0] = i;
  for (let j = 0; j <= n; j++) dp[0][j] = j;
  
  // Fill DP table
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (str1[i - 1] === str2[j - 1]) {
        dp[i][j] = dp[i - 1][j - 1];
      } else {
        dp[i][j] = Math.min(
          dp[i - 1][j] + 1,     // deletion
          dp[i][j - 1] + 1,     // insertion
          dp[i - 1][j - 1] + 1  // substitution
        );
      }
    }
  }
  
  return dp[m][n];
}

/**
 * Calculate paragraph index for a position in text
 */
export function calculateParagraphIndex(text: string, targetText: string): number {
  const position = text.indexOf(targetText);
  if (position === -1) return -1;
  
  const textBeforeTarget = text.substring(0, position);
  return textBeforeTarget.split(/\n\n+/).length - 1;
}

/**
 * Calculate sentence index within a paragraph
 */
export function calculateSentenceIndex(text: string, targetText: string): number {
  const paragraphIndex = calculateParagraphIndex(text, targetText);
  if (paragraphIndex === -1) return -1;
  
  const paragraphs = text.split(/\n\n+/);
  const paragraph = paragraphs[paragraphIndex];
  const sentences = paragraph.split(/[.!?]+/);
  
  for (let i = 0; i < sentences.length; i++) {
    if (sentences[i].includes(targetText)) {
      return i;
    }
  }
  
  return -1;
}

/**
 * Calculate hash for text comparison
 */
function calculateHash(text: string): string {
  let hash = 0;
  for (let i = 0; i < text.length; i++) {
    const char = text.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32-bit integer
  }
  return hash.toString(36);
}

/**
 * Create fingerprint for unique text identification
 */
export function createFingerprint(text: string): string {
  // Combine multiple characteristics for uniqueness
  const length = text.length;
  const wordCount = text.split(/\s+/).length;
  const firstWords = text.split(/\s+/).slice(0, 3).join(' ');
  const lastWords = text.split(/\s+/).slice(-3).join(' ');
  
  return calculateHash(`${length}:${wordCount}:${firstWords}:${lastWords}`);
}

/**
 * Verify that a found position matches the expected text
 */
export function verifyPosition(
  position: Position,
  expectedText: string,
  currentText: string,
  threshold: number = 0.9
): boolean {
  if (position.start < 0 || position.end > currentText.length) {
    return false;
  }
  
  const foundText = currentText.substring(position.start, position.end);
  const similarity = calculateSimilarity(
    expectedText.toLowerCase(),
    foundText.toLowerCase()
  );
  
  return similarity >= threshold;
}

/**
 * Multi-strategy text location with fallback
 */
export function findTextWithFallback(
  targetText: string,
  currentText: string,
  positioning?: SuggestionPositioning
): Position | null {
  const strategies = [
    // Strategy 1: Context anchor (most reliable)
    () => positioning ? findByContextAnchor(positioning.contextAnchor, currentText) : null,
    
    // Strategy 2: Paragraph and sentence indices
    () => positioning ? findByParagraphAndSentence(
      positioning.paragraphIndex,
      positioning.sentenceIndex,
      targetText,
      currentText
    ) : null,
    
    // Strategy 3: Fuzzy matching
    () => findByFuzzyMatch(targetText, currentText),
    
    // Strategy 4: Simple indexOf as last resort
    () => {
      const index = currentText.toLowerCase().indexOf(targetText.toLowerCase());
      return index !== -1 ? { start: index, end: index + targetText.length } : null;
    }
  ];
  
  for (const strategy of strategies) {
    try {
      const position = strategy();
      if (position && verifyPosition(position, targetText, currentText)) {
        return position;
      }
    } catch (error) {
      console.warn('⚠️ Strategy failed:', error);
      continue;
    }
  }
  
  console.error('❌ All positioning strategies failed for text:', targetText);
  return null;
}