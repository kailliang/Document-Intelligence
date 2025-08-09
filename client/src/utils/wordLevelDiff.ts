// Word-level difference algorithm for precise strikethrough implementation

export interface WordDiff {
  type: 'keep' | 'delete' | 'insert' | 'replace';
  originalWord?: string;
  newWord?: string;
  position: number;
}

export interface DiffResult {
  diffs: WordDiff[];
  originalWords: string[];
  newWords: string[];
  hasChanges: boolean;
}

export interface WordSegment {
  word: string;
  isWord: boolean; // true for words, false for punctuation/spaces
  startIndex: number;
  endIndex: number;
}

/**
 * Tokenize text into words and punctuation while preserving positions
 */
function tokenize(text: string): WordSegment[] {
  const segments: WordSegment[] = [];
  const regex = /(\w+|[^\w\s]|\s+)/g;
  let match;
  
  while ((match = regex.exec(text)) !== null) {
    const segment = match[1];
    const isWord = /\w/.test(segment) && !/^\s+$/.test(segment);
    
    segments.push({
      word: segment,
      isWord,
      startIndex: match.index,
      endIndex: match.index + segment.length
    });
  }
  
  return segments;
}

/**
 * Extract only words from segments (filtering out punctuation and spaces)
 */
function extractWords(segments: WordSegment[]): string[] {
  return segments.filter(seg => seg.isWord).map(seg => seg.word.toLowerCase());
}

/**
 * Calculate word-level Levenshtein distance with operation tracking
 */
function calculateWordLevelDiff(originalWords: string[], newWords: string[]): WordDiff[] {
  const m = originalWords.length;
  const n = newWords.length;
  
  // DP table: dp[i][j] represents minimum operations to transform originalWords[0..i-1] to newWords[0..j-1]
  const dp: number[][] = Array(m + 1).fill(null).map(() => Array(n + 1).fill(0));
  const operations: string[][] = Array(m + 1).fill(null).map(() => Array(n + 1).fill(''));
  
  // Initialize base cases
  for (let i = 0; i <= m; i++) {
    dp[i][0] = i;
    operations[i][0] = 'delete';
  }
  for (let j = 0; j <= n; j++) {
    dp[0][j] = j;
    operations[0][j] = 'insert';
  }
  
  // Fill DP table
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (originalWords[i - 1] === newWords[j - 1]) {
        // Words match - keep
        dp[i][j] = dp[i - 1][j - 1];
        operations[i][j] = 'keep';
      } else {
        // Find minimum cost operation
        const deleteCost = dp[i - 1][j] + 1;
        const insertCost = dp[i][j - 1] + 1;
        const replaceCost = dp[i - 1][j - 1] + 1;
        
        const minCost = Math.min(deleteCost, insertCost, replaceCost);
        dp[i][j] = minCost;
        
        if (minCost === replaceCost) {
          operations[i][j] = 'replace';
        } else if (minCost === deleteCost) {
          operations[i][j] = 'delete';
        } else {
          operations[i][j] = 'insert';
        }
      }
    }
  }
  
  // Backtrack to construct diff sequence
  const diffs: WordDiff[] = [];
  let i = m, j = n;
  let position = 0;
  
  while (i > 0 || j > 0) {
    const op = operations[i][j];
    
    switch (op) {
      case 'keep':
        diffs.unshift({
          type: 'keep',
          originalWord: originalWords[i - 1],
          newWord: newWords[j - 1],
          position: position++
        });
        i--;
        j--;
        break;
        
      case 'replace':
        diffs.unshift({
          type: 'replace',
          originalWord: originalWords[i - 1],
          newWord: newWords[j - 1],
          position: position++
        });
        i--;
        j--;
        break;
        
      case 'delete':
        diffs.unshift({
          type: 'delete',
          originalWord: originalWords[i - 1],
          position: position++
        });
        i--;
        break;
        
      case 'insert':
        diffs.unshift({
          type: 'insert',
          newWord: newWords[j - 1],
          position: position++
        });
        j--;
        break;
    }
  }
  
  return diffs;
}

/**
 * Main function to calculate word-level differences
 */
export function calculateWordDiff(originalText: string, newText: string): DiffResult {
  console.log('🔍 Calculating word-level diff:');
  console.log('Original:', originalText);
  console.log('New:', newText);
  
  // Tokenize both texts
  const originalSegments = tokenize(originalText);
  const newSegments = tokenize(newText);
  
  // Extract words for comparison
  const originalWords = extractWords(originalSegments);
  const newWords = extractWords(newSegments);
  
  console.log('Original words:', originalWords);
  console.log('New words:', newWords);
  
  // Calculate differences
  const diffs = calculateWordLevelDiff(originalWords, newWords);
  const hasChanges = diffs.some(diff => diff.type !== 'keep');
  
  console.log('Calculated diffs:', diffs);
  
  return {
    diffs,
    originalWords,
    newWords,
    hasChanges
  };
}

/**
 * Convert diff result to strikethrough format for display
 */
export function generateStrikethroughPreview(diffResult: DiffResult): string {
  if (!diffResult.hasChanges) {
    return diffResult.newWords.join(' ');
  }
  
  const segments: string[] = [];
  
  diffResult.diffs.forEach(diff => {
    switch (diff.type) {
      case 'keep':
        segments.push(diff.newWord || diff.originalWord || '');
        break;
        
      case 'delete':
        segments.push(`~~${diff.originalWord}~~`);
        break;
        
      case 'insert':
        segments.push(`**${diff.newWord}**`);
        break;
        
      case 'replace':
        segments.push(`~~${diff.originalWord}~~ **${diff.newWord}**`);
        break;
    }
  });
  
  return segments.join(' ');
}

/**
 * Generate HTML with spans for precise styling
 */
export function generateStrikethroughHTML(
  diffResult: DiffResult,
  severityClass: string = 'medium'
): string {
  if (!diffResult.hasChanges) {
    return `<span class="text-gray-700">${diffResult.newWords.join(' ')}</span>`;
  }
  
  const segments: string[] = [];
  
  diffResult.diffs.forEach(diff => {
    switch (diff.type) {
      case 'keep':
        const word = diff.newWord || diff.originalWord || '';
        segments.push(`<span class="text-gray-700">${word}</span>`);
        break;
        
      case 'delete':
        const deletedWord = diff.originalWord || '';
        segments.push(
          `<span class="strikethrough-${severityClass} line-through">${deletedWord}</span>`
        );
        break;
        
      case 'insert':
        const insertedWord = diff.newWord || '';
        segments.push(`<span class="text-green-600 font-medium">${insertedWord}</span>`);
        break;
        
      case 'replace':
        const originalWord = diff.originalWord || '';
        const newWord = diff.newWord || '';
        segments.push(
          `<span class="strikethrough-${severityClass} line-through">${originalWord}</span> <span class="text-green-600 font-medium">${newWord}</span>`
        );
        break;
    }
  });
  
  return segments.join(' ');
}

/**
 * Find word positions in the original text for editor highlighting
 */
export function findWordPositions(
  originalText: string,
  diffResult: DiffResult
): Array<{ start: number; end: number; type: 'delete' | 'replace'; originalWord: string }> {
  const segments = tokenize(originalText);
  const wordPositions: Array<{ start: number; end: number; type: 'delete' | 'replace'; originalWord: string }> = [];
  
  let wordIndex = 0;
  
  for (const diff of diffResult.diffs) {
    if (diff.type === 'delete' || diff.type === 'replace') {
      // Find the corresponding word segment in the original text
      for (let i = wordIndex; i < segments.length; i++) {
        const segment = segments[i];
        if (segment.isWord && segment.word.toLowerCase() === (diff.originalWord || '').toLowerCase()) {
          wordPositions.push({
            start: segment.startIndex,
            end: segment.endIndex,
            type: diff.type,
            originalWord: diff.originalWord || ''
          });
          wordIndex = i + 1;
          break;
        }
      }
    }
  }
  
  return wordPositions;
}

/**
 * Optimize diff result by merging adjacent operations
 */
export function optimizeDiff(diffResult: DiffResult): DiffResult {
  const optimizedDiffs: WordDiff[] = [];
  let i = 0;
  
  while (i < diffResult.diffs.length) {
    const current = diffResult.diffs[i];
    
    // Try to merge consecutive delete + insert into replace
    if (
      current.type === 'delete' &&
      i + 1 < diffResult.diffs.length &&
      diffResult.diffs[i + 1].type === 'insert'
    ) {
      const next = diffResult.diffs[i + 1];
      optimizedDiffs.push({
        type: 'replace',
        originalWord: current.originalWord,
        newWord: next.newWord,
        position: current.position
      });
      i += 2;
    } else {
      optimizedDiffs.push(current);
      i++;
    }
  }
  
  return {
    ...diffResult,
    diffs: optimizedDiffs,
    hasChanges: optimizedDiffs.some(diff => diff.type !== 'keep')
  };
}