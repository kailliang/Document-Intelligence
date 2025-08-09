import { Mark, mergeAttributes } from '@tiptap/core';
import { Plugin, PluginKey } from '@tiptap/pm/state';
import { Decoration, DecorationSet } from '@tiptap/pm/view';

export interface WordLevelStrikethroughOptions {
  HTMLAttributes: Record<string, any>;
}

interface SentenceHighlightState {
  decorations: DecorationSet;
  activeSuggestions: Map<string, {
    sentencePosition: { start: number; end: number };
    timeoutId: number;
  }>;
}

interface SentenceHighlightParams {
  suggestionId: string;
  sentenceStart: number;
  sentenceEnd: number;
}

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    sentenceHighlight: {
      /**
       * Show sentence highlight for a suggestion
       */
      showSentenceHighlight: (params: SentenceHighlightParams) => ReturnType;
      /**
       * Clear all sentence highlights
       */
      clearAllSentenceHighlights: () => ReturnType;
      /**
       * Clear specific suggestion highlight
       */
      clearSuggestionHighlight: (suggestionId: string) => ReturnType;
    };
  }
}

const sentenceHighlightPluginKey = new PluginKey<SentenceHighlightState>('sentenceHighlight');

export const SentenceHighlightExtension = Mark.create<WordLevelStrikethroughOptions>({
  name: 'sentenceHighlight',

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
      showSentenceHighlight:
        (params: SentenceHighlightParams) =>
        ({ state, view }) => {
          const pluginState = sentenceHighlightPluginKey.getState(state);
          if (!pluginState) return false;

          console.log('🎯 Showing sentence highlight for:', params.suggestionId);

          // Clear existing suggestion if present
          const existing = pluginState.activeSuggestions.get(params.suggestionId);
          if (existing) {
            clearTimeout(existing.timeoutId);
            pluginState.activeSuggestions.delete(params.suggestionId);
          }

          // Create sentence highlight decoration
          const sentenceDecoration = Decoration.inline(params.sentenceStart, params.sentenceEnd, {
            class: 'sentence-highlight sentence-highlight-3s',
            'data-sentence-highlight': 'true',
            'data-suggestion-id': params.suggestionId,
          });

          // Set timeout to auto-clear after 3 seconds
          const timeoutId = window.setTimeout(() => {
            const currentState = view.state;
            const currentPluginState = sentenceHighlightPluginKey.getState(currentState);
            if (currentPluginState?.activeSuggestions.has(params.suggestionId)) {
              currentPluginState.activeSuggestions.delete(params.suggestionId);
              const tr = currentState.tr.setMeta(sentenceHighlightPluginKey, {
                action: 'remove',
                suggestionId: params.suggestionId,
              });
              view.dispatch(tr);
              console.log('⏱️ Auto-cleared sentence highlight after 3s:', params.suggestionId);
            }
          }, 3000);

          // Store suggestion state
          pluginState.activeSuggestions.set(params.suggestionId, {
            sentencePosition: { start: params.sentenceStart, end: params.sentenceEnd },
            timeoutId,
          });

          // Dispatch transaction with decoration
          const tr = state.tr.setMeta(sentenceHighlightPluginKey, {
            action: 'add',
            suggestionId: params.suggestionId,
            decorations: [sentenceDecoration],
          });
          view.dispatch(tr);
          
          console.log('✅ Applied sentence highlight for suggestion', params.suggestionId);
          return true;
        },

      clearAllSentenceHighlights:
        () =>
        ({ state, view }) => {
          const pluginState = sentenceHighlightPluginKey.getState(state);
          if (!pluginState) return false;

          console.log('🧹 Clearing all sentence highlights');

          // Clear all timeouts
          pluginState.activeSuggestions.forEach((suggestion) => {
            clearTimeout(suggestion.timeoutId);
          });
          pluginState.activeSuggestions.clear();

          const tr = state.tr.setMeta(sentenceHighlightPluginKey, {
            action: 'clear-all',
          });
          view.dispatch(tr);
          return true;
        },

      clearSuggestionHighlight:
        (suggestionId: string) =>
        ({ state, view }) => {
          const pluginState = sentenceHighlightPluginKey.getState(state);
          if (!pluginState) return false;

          const suggestion = pluginState.activeSuggestions.get(suggestionId);
          if (!suggestion) return false;

          console.log('🧹 Clearing highlight for suggestion:', suggestionId);

          // Clear timeout
          clearTimeout(suggestion.timeoutId);
          pluginState.activeSuggestions.delete(suggestionId);

          const tr = state.tr.setMeta(sentenceHighlightPluginKey, {
            action: 'remove',
            suggestionId,
          });
          view.dispatch(tr);
          return true;
        },
    };
  },

  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: sentenceHighlightPluginKey,
        state: {
          init(): SentenceHighlightState {
            console.log('🔧 Sentence highlight plugin initialized');
            return {
              decorations: DecorationSet.empty,
              activeSuggestions: new Map(),
            };
          },
          apply(tr, pluginState: SentenceHighlightState): SentenceHighlightState {
            const meta = tr.getMeta(sentenceHighlightPluginKey);
            
            if (meta) {
              switch (meta.action) {
                case 'add':
                  console.log(`🎨 Adding sentence highlight for suggestion: ${meta.suggestionId}`);
                  return {
                    ...pluginState,
                    decorations: pluginState.decorations.add(tr.doc, meta.decorations || []),
                  };
                  
                case 'remove':
                  console.log(`🗑️ Removing sentence highlight for suggestion: ${meta.suggestionId}`);
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
                  console.log('🧹 Clearing all sentence highlights');
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
            const pluginState = sentenceHighlightPluginKey.getState(state);
            return pluginState?.decorations || DecorationSet.empty;
          },
        },
      }),
    ];
  },
});

// Export both the old extension name for compatibility and the new one
export const WordLevelStrikethroughExtension = SentenceHighlightExtension;
export const StrikethroughExtension = SentenceHighlightExtension;