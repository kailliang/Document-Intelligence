import { Mark, mergeAttributes } from '@tiptap/core';
import { Plugin, PluginKey } from '@tiptap/pm/state';
import { Decoration, DecorationSet } from '@tiptap/pm/view';
import { findWordPositions, DiffResult } from '../utils/wordLevelDiff';

export interface WordLevelStrikethroughOptions {
  HTMLAttributes: Record<string, any>;
}

interface WordStrikethroughState {
  decorations: DecorationSet;
  activeSuggestions: Map<string, {
    wordPositions: Array<{ start: number; end: number; type: 'delete' | 'replace'; originalWord: string }>;
    sentencePosition: { start: number; end: number };
    severity: string;
    replacement: string;
    timeoutId: number;
  }>;
}

interface WordHighlightParams {
  suggestionId: string;
  sentenceStart: number;
  sentenceEnd: number;
  originalTextOffsetInSentence: number; // New: offset of original text within the sentence
  wordDiffs: DiffResult;
  originalText: string;
  severity: string;
  replacement: string;
}

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    wordLevelStrikethrough: {
      /**
       * Show word-level strikethrough for a suggestion
       */
      showWordLevelStrikethrough: (params: WordHighlightParams) => ReturnType;
      /**
       * Clear all word-level strikethroughs
       */
      clearAllWordStrikethroughs: () => ReturnType;
      /**
       * Clear specific suggestion strikethrough
       */
      clearSuggestionStrikethrough: (suggestionId: string) => ReturnType;
      /**
       * Get active strikethroughs
       */
      getActiveWordStrikethroughs: () => ReturnType;
    };
  }
}

const wordStrikethroughPluginKey = new PluginKey<WordStrikethroughState>('wordStrikethrough');

export const WordLevelStrikethroughExtension = Mark.create<WordLevelStrikethroughOptions>({
  name: 'wordLevelStrikethrough',

  addOptions() {
    return {
      HTMLAttributes: {},
    };
  },

  addAttributes() {
    return {
      severity: {
        default: 'medium',
        parseHTML: element => element.getAttribute('data-severity'),
        renderHTML: attributes => ({
          'data-severity': attributes.severity,
        }),
      },
      wordType: {
        default: 'normal',
        parseHTML: element => element.getAttribute('data-word-type'),
        renderHTML: attributes => ({
          'data-word-type': attributes.wordType,
        }),
      },
    };
  },

  parseHTML() {
    return [
      {
        tag: 'span[data-word-strikethrough]',
        getAttrs: element => {
          const el = element as HTMLElement;
          return {
            severity: el.getAttribute('data-severity') || 'medium',
            wordType: el.getAttribute('data-word-type') || 'normal',
          };
        },
      },
    ];
  },

  renderHTML({ HTMLAttributes }) {
    return [
      'span',
      mergeAttributes(
        {
          'data-word-strikethrough': 'true',
          class: 'word-strikethrough-text',
        },
        this.options.HTMLAttributes,
        HTMLAttributes
      ),
      0,
    ];
  },

  addCommands() {
    return {
      showWordLevelStrikethrough:
        (params: WordHighlightParams) =>
        ({ state, view }) => {
          const pluginState = wordStrikethroughPluginKey.getState(state);
          if (!pluginState) return false;

          console.log('🎯 Showing word-level strikethrough for:', params.suggestionId);

          // Clear existing suggestion if present
          const existing = pluginState.activeSuggestions.get(params.suggestionId);
          if (existing) {
            clearTimeout(existing.timeoutId);
            pluginState.activeSuggestions.delete(params.suggestionId);
          }

          // Find word positions in the original text (relative to original text)
          const wordPositions = findWordPositions(params.originalText, params.wordDiffs);
          
          console.log('🔤 Word positions in original text:', wordPositions);
          
          // Create decorations for word-level strikethroughs and sentence highlight
          const decorations: Decoration[] = [];

          // 1. Sentence background highlight
          const sentenceDecoration = Decoration.inline(params.sentenceStart, params.sentenceEnd, {
            class: 'sentence-highlight sentence-highlight-3s',
            'data-sentence-highlight': 'true',
            'data-suggestion-id': params.suggestionId,
          });
          decorations.push(sentenceDecoration);

          // 2. Word-level strikethroughs with correct absolute positioning
          wordPositions.forEach((wordPos) => {
            // Calculate absolute position in document:
            // sentence start + offset of original text in sentence + word position in original text
            const absoluteStart = params.sentenceStart + params.originalTextOffsetInSentence + wordPos.start;
            const absoluteEnd = params.sentenceStart + params.originalTextOffsetInSentence + wordPos.end;
            
            console.log(`📍 Word "${wordPos.originalWord}" absolute position: ${absoluteStart}-${absoluteEnd}`);
            
            // Validate position is within document bounds and sentence bounds
            if (absoluteStart >= 0 && absoluteEnd <= tr.doc.content.size && 
                absoluteStart >= params.sentenceStart && absoluteEnd <= params.sentenceEnd &&
                absoluteStart < absoluteEnd) { // Ensure valid range
              
              try {
                const wordDecoration = Decoration.inline(absoluteStart, absoluteEnd, {
                  class: `word-strikethrough word-strikethrough-${params.severity} ${wordPos.type === 'delete' ? 'strikethrough-delete' : 'strikethrough-replace'}`,
                  'data-word-type': wordPos.type,
                  'data-severity': params.severity,
                  'data-suggestion-id': params.suggestionId,
                  'data-original-word': wordPos.originalWord,
                }, {
                  // Ensure decoration is non-inclusive to prevent text modification
                  inclusiveStart: false,
                  inclusiveEnd: false,
                });
                decorations.push(wordDecoration);
                console.log(`✅ Created decoration for word "${wordPos.originalWord}" at ${absoluteStart}-${absoluteEnd}`);
              } catch (error) {
                console.error(`❌ Failed to create decoration for word "${wordPos.originalWord}":`, error);
              }
            } else {
              console.warn(`⚠️ Invalid word position: ${absoluteStart}-${absoluteEnd}, document size: ${tr.doc.content.size}, sentence: ${params.sentenceStart}-${params.sentenceEnd}`);
            }
          });

          // Set timeout to auto-clear after 3 seconds
          const timeoutId = window.setTimeout(() => {
            const currentState = view.state;
            const currentPluginState = wordStrikethroughPluginKey.getState(currentState);
            if (currentPluginState?.activeSuggestions.has(params.suggestionId)) {
              currentPluginState.activeSuggestions.delete(params.suggestionId);
              const tr = currentState.tr.setMeta(wordStrikethroughPluginKey, {
                action: 'remove',
                suggestionId: params.suggestionId,
              });
              view.dispatch(tr);
              console.log('⏱️ Auto-cleared word strikethrough after 3s:', params.suggestionId);
            }
          }, 3000);

          // Store suggestion state
          pluginState.activeSuggestions.set(params.suggestionId, {
            wordPositions,
            sentencePosition: { start: params.sentenceStart, end: params.sentenceEnd },
            severity: params.severity,
            replacement: params.replacement,
            timeoutId,
          });

          // Dispatch transaction with decorations
          const tr = state.tr.setMeta(wordStrikethroughPluginKey, {
            action: 'add',
            suggestionId: params.suggestionId,
            decorations,
          });
          view.dispatch(tr);
          
          console.log(`✅ Applied ${decorations.length} decorations for suggestion ${params.suggestionId}`);
          return true;
        },

      clearAllWordStrikethroughs:
        () =>
        ({ state, view }) => {
          const pluginState = wordStrikethroughPluginKey.getState(state);
          if (!pluginState) return false;

          console.log('🧹 Clearing all word strikethroughs');

          // Clear all timeouts
          pluginState.activeSuggestions.forEach((suggestion) => {
            clearTimeout(suggestion.timeoutId);
          });
          pluginState.activeSuggestions.clear();

          const tr = state.tr.setMeta(wordStrikethroughPluginKey, {
            action: 'clear-all',
          });
          view.dispatch(tr);
          return true;
        },

      clearSuggestionStrikethrough:
        (suggestionId: string) =>
        ({ state, view }) => {
          const pluginState = wordStrikethroughPluginKey.getState(state);
          if (!pluginState) return false;

          const suggestion = pluginState.activeSuggestions.get(suggestionId);
          if (!suggestion) return false;

          console.log('🧹 Clearing strikethrough for suggestion:', suggestionId);

          // Clear timeout
          clearTimeout(suggestion.timeoutId);
          pluginState.activeSuggestions.delete(suggestionId);

          const tr = state.tr.setMeta(wordStrikethroughPluginKey, {
            action: 'remove',
            suggestionId,
          });
          view.dispatch(tr);
          return true;
        },

      getActiveWordStrikethroughs:
        () =>
        ({ state }) => {
          const pluginState = wordStrikethroughPluginKey.getState(state);
          const activeCount = pluginState?.activeSuggestions.size || 0;
          console.log(`📊 Active word strikethroughs: ${activeCount}`);
          return true;
        },
    };
  },

  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: wordStrikethroughPluginKey,
        state: {
          init(): WordStrikethroughState {
            console.log('🔧 Word-level strikethrough plugin initialized');
            return {
              decorations: DecorationSet.empty,
              activeSuggestions: new Map(),
            };
          },
          apply(tr, pluginState: WordStrikethroughState): WordStrikethroughState {
            const meta = tr.getMeta(wordStrikethroughPluginKey);
            
            if (meta) {
              switch (meta.action) {
                case 'add':
                  console.log(`🎨 Adding decorations for suggestion: ${meta.suggestionId}`);
                  return {
                    ...pluginState,
                    decorations: pluginState.decorations.add(tr.doc, meta.decorations || []),
                  };
                  
                case 'remove':
                  console.log(`🗑️ Removing decorations for suggestion: ${meta.suggestionId}`);
                  // Get all current decorations and filter out the ones for this suggestion
                  const decorationsToKeep: Decoration[] = [];
                  const allDecorations = pluginState.decorations.find();
                  
                  allDecorations.forEach(decoration => {
                    const spec = decoration.spec as any;
                    if (spec && spec['data-suggestion-id'] !== meta.suggestionId) {
                      decorationsToKeep.push(decoration);
                    }
                  });
                  
                  console.log(`🔄 Keeping ${decorationsToKeep.length} decorations after removing suggestion ${meta.suggestionId}`);
                  
                  return {
                    ...pluginState,
                    decorations: DecorationSet.create(tr.doc, decorationsToKeep),
                  };
                  
                case 'clear-all':
                  console.log('🧹 Clearing all decorations');
                  return {
                    ...pluginState,
                    decorations: DecorationSet.empty,
                  };
              }
            }

            // Map decorations through document changes
            const mappedDecorations = pluginState.decorations.map(tr.mapping, tr.doc);
            return {
              ...pluginState,
              decorations: mappedDecorations,
            };
          },
        },
        props: {
          decorations(state) {
            const pluginState = wordStrikethroughPluginKey.getState(state);
            return pluginState?.decorations || DecorationSet.empty;
          },
        },
      }),
    ];
  },
});

// Export both the old extension name for compatibility and the new one
export const StrikethroughExtension = WordLevelStrikethroughExtension;