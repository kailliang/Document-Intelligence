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

// Store for temporary decorations
let temporaryDecorations = DecorationSet.empty;
let highlightTimeout: number | null = null;

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
        ({ view, state }) => {
          // Clear previous timeout
          if (highlightTimeout) {
            clearTimeout(highlightTimeout);
          }

          // Create decoration
          const decoration = Decoration.inline(from, to, {
            class: `temporary-highlight temporary-highlight-${severity}`,
            'data-severity': severity,
          });

          // Update decorations
          temporaryDecorations = DecorationSet.create(state.doc, [decoration]);
          
          // Force re-render
          view.dispatch(state.tr);

          // Set timeout to clear after 3 seconds
          highlightTimeout = setTimeout(() => {
            temporaryDecorations = DecorationSet.empty;
            view.dispatch(state.tr);
            highlightTimeout = null;
          }, 3000);

          return true;
        },
      clearTemporaryHighlights:
        () =>
        ({ view, state }) => {
          if (highlightTimeout) {
            clearTimeout(highlightTimeout);
            highlightTimeout = null;
          }
          temporaryDecorations = DecorationSet.empty;
          view.dispatch(state.tr);
          return true;
        },
    };
  },

  addProseMirrorPlugins() {
    return [
      new Plugin({
        props: {
          decorations(_state) {
            return temporaryDecorations;
          },
        },
      }),
    ];
  },
});

// Helper function to find text in the document
export function findTextInDocument(doc: any, searchText: string): { from: number; to: number } | null {
  let result: { from: number; to: number } | null = null;
  const normalizedSearch = searchText.toLowerCase().trim();

  doc.descendants((node: any, pos: number) => {
    if (result) return false; // Already found

    if (node.isText && node.text) {
      const normalizedText = node.text.toLowerCase();
      const index = normalizedText.indexOf(normalizedSearch);
      
      if (index !== -1) {
        result = {
          from: pos + index,
          to: pos + index + searchText.length,
        };
        return false; // Stop searching
      }
    }
  });

  return result;
}

// Helper function to replace text
export function replaceText(editor: any, searchText: string, replaceWith: string): boolean {
  const { state } = editor;
  const result = findTextInDocument(state.doc, searchText);

  if (result) {
    editor
      .chain()
      .focus()
      .setTextSelection(result)
      .deleteSelection()
      .insertContent(replaceWith)
      .run();
    return true;
  }

  return false;
}