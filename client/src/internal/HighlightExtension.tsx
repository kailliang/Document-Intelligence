import { Mark, mergeAttributes } from '@tiptap/core';
import { Plugin } from '@tiptap/pm/state';
import { Decoration, DecorationSet } from '@tiptap/pm/view';

export interface HighlightOptions {
  multicolor: boolean;
  HTMLAttributes: Record<string, any>;
}

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    highlight: {
      /**
       * Set a highlight mark with severity
       */
      setHighlight: (attributes?: { severity?: string }) => ReturnType;
      /**
       * Toggle a highlight mark
       */
      toggleHighlight: (attributes?: { severity?: string }) => ReturnType;
      /**
       * Unset a highlight mark
       */
      unsetHighlight: () => ReturnType;
      /**
       * Add temporary highlight decoration
       */
      addTemporaryHighlight: (from: number, to: number, severity: string) => ReturnType;
      /**
       * Clear all temporary highlights
       */
      clearTemporaryHighlights: () => ReturnType;
    };
  }
}

// Store for temporary decorations - using WeakMap to prevent memory leaks
const editorTimeouts = new WeakMap<any, number>();

export const Highlight = Mark.create<HighlightOptions>({
  name: 'highlight',

  addOptions() {
    return {
      multicolor: true,
      HTMLAttributes: {},
    };
  },

  addAttributes() {
    if (!this.options.multicolor) {
      return {};
    }

    return {
      severity: {
        default: 'medium',
        parseHTML: element => element.getAttribute('data-severity') || element.dataset.severity,
        renderHTML: attributes => {
          if (!attributes.severity) {
            return {};
          }

          return {
            'data-severity': attributes.severity,
            class: `highlight-${attributes.severity}`,
          };
        },
      },
    };
  },

  parseHTML() {
    return [
      {
        tag: 'mark',
        getAttrs: element => {
          const severity = (element as HTMLElement).getAttribute('data-severity');
          return severity ? { severity } : {};
        },
      },
    ];
  },

  renderHTML({ HTMLAttributes }) {
    return ['mark', mergeAttributes(this.options.HTMLAttributes, HTMLAttributes), 0];
  },

  addCommands() {
    return {
      setHighlight:
        (attributes) =>
        ({ commands }) => {
          return commands.setMark(this.name, attributes);
        },
      toggleHighlight:
        (attributes) =>
        ({ commands }) => {
          return commands.toggleMark(this.name, attributes);
        },
      unsetHighlight:
        () =>
        ({ commands }) => {
          return commands.unsetMark(this.name);
        },
      addTemporaryHighlight:
        (from: number, to: number, severity: string) =>
        ({ view, state, editor }) => {
          // Clear previous timeout for this editor instance
          const existingTimeout = editorTimeouts.get(editor);
          if (existingTimeout) {
            clearTimeout(existingTimeout);
            editorTimeouts.delete(editor);
          }

          // Create decoration
          const decoration = Decoration.inline(from, to, {
            class: `temporary-highlight temporary-highlight-${severity}`,
            'data-severity': severity,
          });

          // Update decorations using plugin state
          const newDecorations = DecorationSet.create(state.doc, [decoration]);
          const tr = state.tr.setMeta('addHighlight', newDecorations);
          
          // Dispatch transaction to update plugin state
          view.dispatch(tr);

          // Set timeout to clear after 5 seconds (increased for better UX)
          const timeoutId = setTimeout(() => {
            const clearTr = view.state.tr.setMeta('clearHighlight', true);
            view.dispatch(clearTr);
            editorTimeouts.delete(editor);
          }, 5000);
          
          editorTimeouts.set(editor, timeoutId);

          return true;
        },
      clearTemporaryHighlights:
        () =>
        ({ view, editor }) => {
          // Clear timeout for this editor instance
          const existingTimeout = editorTimeouts.get(editor);
          if (existingTimeout) {
            clearTimeout(existingTimeout);
            editorTimeouts.delete(editor);
          }
          
          // Clear decorations using plugin state
          const tr = view.state.tr.setMeta('clearHighlight', true);
          view.dispatch(tr);
          
          return true;
        },
    };
  },

  addProseMirrorPlugins() {
    return [
      new Plugin({
        props: {
          decorations(state: any) {
            // Get decorations from the current plugin state
            // We'll store decorations in plugin state instead of WeakMap for the plugin
            return this.getState(state) || DecorationSet.empty;
          },
        },
        state: {
          init() {
            return DecorationSet.empty;
          },
          apply(tr: any, decorations: DecorationSet) {
            // Handle highlight metadata
            if (tr.getMeta('addHighlight')) {
              return tr.getMeta('addHighlight');
            }
            if (tr.getMeta('clearHighlight')) {
              return DecorationSet.empty;
            }
            
            // Map existing decorations through transaction
            return decorations.map(tr.mapping, tr.doc);
          },
        },
      }),
    ];
  },
});


// Helper function to find text in the document with enhanced matching
export function findTextInDocument(doc: any, searchText: string): { from: number; to: number } | null {
  let result: { from: number; to: number } | null = null;
  
  // Normalize search text - handle HTML entities, whitespace, and strikethrough formatting
  const normalizedSearch = searchText
    .replace(/&nbsp;/g, ' ')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&amp;/g, '&')
    .replace(/\s+/g, ' ')
    .toLowerCase()
    .trim();

  // Helper function to normalize text content from editor nodes
  const normalizeNodeText = (text: string) => {
    return text
      .replace(/&nbsp;/g, ' ')
      .replace(/&lt;/g, '<')
      .replace(/&gt;/g, '>')
      .replace(/&amp;/g, '&')
      .replace(/\s+/g, ' ')
      .toLowerCase();
  };

  // Helper function to extract plain text from node, handling special formatting
  const extractPlainText = (node: any): string => {
    if (node.isText) {
      return node.text || '';
    }
    
    let text = '';
    node.forEach((childNode: any) => {
      if (childNode.isText) {
        text += childNode.text || '';
      } else {
        // Recursively extract text from child nodes
        text += extractPlainText(childNode);
      }
    });
    return text;
  };

  // First try: exact match in text nodes
  doc.descendants((node: any, pos: number) => {
    if (result) return false;

    if (node.isText && node.text) {
      const normalizedText = normalizeNodeText(node.text);
      const index = normalizedText.indexOf(normalizedSearch);
      
      if (index !== -1) {
        result = {
          from: pos + index,
          to: pos + index + normalizedSearch.length,
        };
        return false;
      }
    }
  });

  // Second try: match across parent nodes (handles spans and formatting)
  if (!result) {
    doc.descendants((node: any, pos: number) => {
      if (result) return false;

      // Check if node has children (like paragraph, spans, etc.)
      if (!node.isText && node.content && node.content.size > 0) {
        const plainText = extractPlainText(node);
        const normalizedText = normalizeNodeText(plainText);
        const index = normalizedText.indexOf(normalizedSearch);
        
        if (index !== -1) {
          // Find the actual position within the node structure
          let currentPos = 0;
          let foundPos = -1;
          
          node.descendants((childNode: any, childPos: number) => {
            if (foundPos !== -1) return false;
            
            if (childNode.isText && childNode.text) {
              const childText = normalizeNodeText(childNode.text);
              if (currentPos <= index && currentPos + childText.length > index) {
                const relativeIndex = index - currentPos;
                foundPos = pos + childPos + relativeIndex;
                return false;
              }
              currentPos += childText.length;
            }
          });
          
          if (foundPos !== -1) {
            result = {
              from: foundPos,
              to: foundPos + normalizedSearch.length,
            };
            return false;
          }
        }
      }
    });
  }

  // Third try: fuzzy matching for shorter text (first 30 chars)
  if (!result && normalizedSearch.length > 10) {
    const shortSearch = normalizedSearch.substring(0, 30);
    
    doc.descendants((node: any, pos: number) => {
      if (result) return false;

      if (node.isText && node.text) {
        const normalizedText = normalizeNodeText(node.text);
        const index = normalizedText.indexOf(shortSearch);
        
        if (index !== -1) {
          result = {
            from: pos + index,
            to: pos + index + shortSearch.length,
          };
          return false;
        }
      }
    });
  }

  return result;
}

// Helper function to replace text
export function replaceText(editor: any, searchText: string, replaceWith: string): boolean {
  const { state } = editor;
  const result = findTextInDocument(state.doc, searchText);

  if (result) {
    try {
      console.log(`🔄 Replacing text from ${result.from} to ${result.to}`);
      console.log(`🔍 Original: "${searchText}"`);
      console.log(`➡️ Replace with: "${replaceWith}"`);
      
      // Use a transaction to replace text and remove any formatting
      const transaction = state.tr
        .delete(result.from, result.to)
        .insertText(replaceWith, result.from);
      
      // Apply the transaction
      editor.view.dispatch(transaction);
      
      console.log(`✅ Text replacement successful`);
      return true;
    } catch (error) {
      console.error(`❌ Text replacement failed:`, error);
      
      // Fallback to the original chain method
      try {
        editor
          .chain()
          .focus()
          .setTextSelection(result)
          .deleteSelection()
          .insertContent(replaceWith)
          .run();
        console.log(`✅ Text replacement successful (fallback method)`);
        return true;
      } catch (fallbackError) {
        console.error(`❌ Fallback text replacement also failed:`, fallbackError);
        return false;
      }
    }
  }

  console.warn(`⚠️ Text not found for replacement: "${searchText}"`);
  return false;
}