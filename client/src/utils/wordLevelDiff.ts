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

// Legacy Levenshtein algorithm removed - using simpler approach for better accuracy

/**
 * Simple word difference algorithm for better accuracy
 */
function calculateSimpleWordDiff(originalWords: string[], newWords: string[]): WordDiff[] {
  const diffs: WordDiff[] = [];
  
  // First pass: identify common prefix and suffix
  let commonPrefix = 0;
  let commonSuffix = 0;
  
  // Find common prefix
  while (commonPrefix < originalWords.length && 
         commonPrefix < newWords.length && 
         originalWords[commonPrefix] === newWords[commonPrefix]) {
    commonPrefix++;
  }
  
  // Find common suffix
  while (commonSuffix < originalWords.length - commonPrefix && 
         commonSuffix < newWords.length - commonPrefix && 
         originalWords[originalWords.length - 1 - commonSuffix] === 
         newWords[newWords.length - 1 - commonSuffix]) {
    commonSuffix++;
  }
  
  // Add prefix words (keep)
  for (let i = 0; i < commonPrefix; i++) {
    diffs.push({
      type: 'keep',
      originalWord: originalWords[i],
      newWord: newWords[i],
      position: i
    });
  }
  
  // Handle middle section (differences)
  const originalMiddle = originalWords.slice(commonPrefix, originalWords.length - commonSuffix);
  const newMiddle = newWords.slice(commonPrefix, newWords.length - commonSuffix);
  
  // Simple approach: mark all original middle words as delete, all new middle words as insert
  originalMiddle.forEach((word, index) => {
    diffs.push({
      type: 'delete',
      originalWord: word,
      position: commonPrefix + index
    });
  });
  
  newMiddle.forEach((word, index) => {
    diffs.push({
      type: 'insert',
      newWord: word,
      position: commonPrefix + index
    });
  });
  
  // Add suffix words (keep)
  for (let i = 0; i < commonSuffix; i++) {
    const originalIndex = originalWords.length - commonSuffix + i;
    const newIndex = newWords.length - commonSuffix + i;
    diffs.push({
      type: 'keep',
      originalWord: originalWords[originalIndex],
      newWord: newWords[newIndex],
      position: originalIndex
    });
  }
  
  return diffs;
}

/**
 * Main function to calculate word-level differences
 */
export function calculateWordDiff(originalText: string, newText: string): DiffResult {
  // Disabled console logging to avoid noise
  // console.log('🔍 Calculating word-level diff:');
  // console.log('Original:', originalText);
  // console.log('New:', newText);
  
  // Tokenize both texts
  const originalSegments = tokenize(originalText);
  const newSegments = tokenize(newText);
  
  // Extract words for comparison
  const originalWords = extractWords(originalSegments);
  const newWords = extractWords(newSegments);
  
  // console.log('Original words:', originalWords);
  // console.log('New words:', newWords);
  
  // Use simple algorithm for better accuracy
  const diffs = calculateSimpleWordDiff(originalWords, newWords);
  const hasChanges = diffs.some(diff => diff.type !== 'keep');
  
  // console.log('Calculated diffs:', diffs);
  
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
  _severityClass: string = 'medium'  // Unused parameter, kept for API compatibility
): string {
  if (!diffResult.hasChanges) {
    return `<span class="text-gray-700">${diffResult.newWords.join(' ')}</span>`;
  }
  
  const segments: string[] = [];
  
  // Group consecutive delete/insert operations
  let i = 0;
  while (i < diffResult.diffs.length) {
    const diff = diffResult.diffs[i];
    
    switch (diff.type) {
      case 'keep':
        const word = diff.newWord || diff.originalWord || '';
        segments.push(`<span class="text-gray-700">${word}</span>`);
        i++;
        break;
        
      case 'delete':
        // Collect all consecutive deletes
        const deletedWords: string[] = [];
        let j = i;
        while (j < diffResult.diffs.length && diffResult.diffs[j].type === 'delete') {
          deletedWords.push(diffResult.diffs[j].originalWord || '');
          j++;
        }
        
        // Collect all consecutive inserts that follow
        const insertedWords: string[] = [];
        while (j < diffResult.diffs.length && diffResult.diffs[j].type === 'insert') {
          insertedWords.push(diffResult.diffs[j].newWord || '');
          j++;
        }
        
        // Generate combined delete + insert HTML
        if (deletedWords.length > 0) {
          const deletedHTML = deletedWords.map(word => 
            `<span class="text-red-600 line-through decoration-red-500 decoration-2">${word}</span>`
          ).join(' ');
          segments.push(deletedHTML);
        }
        
        if (insertedWords.length > 0) {
          const insertedHTML = insertedWords.map(word => 
            `<span class="text-green-600 font-medium">${word}</span>`
          ).join(' ');
          segments.push(insertedHTML);
        }
        
        i = j;
        break;
        
      case 'insert':
        // Handle standalone inserts (shouldn't happen with our algorithm, but just in case)
        const insertedWord = diff.newWord || '';
        segments.push(`<span class="text-green-600 font-medium">${insertedWord}</span>`);
        i++;
        break;
        
      case 'replace':
        const originalWord = diff.originalWord || '';
        const newWord = diff.newWord || '';
        segments.push(
          `<span class="text-red-600 line-through decoration-red-500 decoration-2">${originalWord}</span> <span class="text-green-600 font-medium">${newWord}</span>`
        );
        i++;
        break;
        
      default:
        i++;
        break;
    }
  }
  
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