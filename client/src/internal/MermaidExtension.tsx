import { Node, mergeAttributes } from '@tiptap/core';
import { ReactNodeViewRenderer, NodeViewWrapper } from '@tiptap/react';
import { useEffect, useRef } from 'react';
import mermaid from 'mermaid';

// Mermaid diagram component for TipTap
function MermaidNodeView({ node }: { node: any; updateAttributes?: any }) {
  const ref = useRef<HTMLDivElement>(null);
  const { syntax, title } = node.attrs;
  
  useEffect(() => {
    if (ref.current) {
      if (syntax && syntax.trim()) {
        // Initialize mermaid with settings
        mermaid.initialize({ 
          startOnLoad: false, 
          theme: 'default',
          securityLevel: 'loose',
          flowchart: {
            htmlLabels: true,
            curve: 'basis',
            useMaxWidth: true
          },
          maxTextSize: 90000
        });
        
        // Clear previous content
        ref.current.innerHTML = '';
        
        // Render the diagram
        mermaid.render('mermaid-' + Date.now(), syntax)
          .then(({ svg }) => {
            if (ref.current) {
              ref.current.innerHTML = svg;
            }
          })
          .catch((error) => {
            console.error('Mermaid rendering error:', error);
            if (ref.current) {
              ref.current.innerHTML = `<div class="text-red-500 text-sm p-2 border border-red-300 rounded bg-red-50">⚠️ Chart rendering failed: ${error.message}</div>`;
            }
          });
      } else {
        // Handle empty syntax - show placeholder or hide node
        ref.current.innerHTML = '<div class="text-gray-400 text-sm p-2 border border-gray-300 rounded bg-gray-50">Empty diagram</div>';
      }
    }
  }, [syntax]);

  return (
    <NodeViewWrapper 
      className="mermaid-node-wrapper mermaid-node" 
      data-syntax={syntax}
      data-title={title}
      data-type="mermaid-diagram"
    >
      {title && (
        <div className="mermaid-title text-sm font-semibold text-gray-700 mb-2 text-center">
          {title}
        </div>
      )}
      <div 
        ref={ref} 
        className="mermaid-diagram border rounded-lg p-2 bg-gray-50 my-2"
        style={{maxWidth: "100%", overflow: "auto"}}
      />
    </NodeViewWrapper>
  );
}

export interface MermaidOptions {
  HTMLAttributes: Record<string, any>;
}

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    mermaidDiagram: {
      /**
       * Insert a Mermaid diagram
       */
      insertMermaidDiagram: (options: { syntax: string; title?: string }) => ReturnType;
    };
  }
}

export const MermaidNode = Node.create<MermaidOptions>({
  name: 'mermaidDiagram',

  addOptions() {
    return {
      HTMLAttributes: {},
    };
  },

  group: 'block',

  atom: true,

  addAttributes() {
    return {
      syntax: {
        default: '',
        parseHTML: element => element.getAttribute('data-syntax'),
        renderHTML: attributes => {
          if (!attributes.syntax) {
            return {};
          }
          return {
            'data-syntax': attributes.syntax,
          };
        },
      },
      title: {
        default: '',
        parseHTML: element => element.getAttribute('data-title'),
        renderHTML: attributes => {
          if (!attributes.title) {
            return {};
          }
          return {
            'data-title': attributes.title,
          };
        },
      },
    };
  },

  parseHTML() {
    return [
      {
        tag: 'div[data-type="mermaid-diagram"]',
        getAttrs: element => {
          const syntax = (element as HTMLElement).getAttribute('data-syntax');
          const title = (element as HTMLElement).getAttribute('data-title');
          return { syntax, title };
        },
      },
      {
        tag: 'div.mermaid-node',
        getAttrs: element => {
          const syntax = (element as HTMLElement).getAttribute('data-syntax');
          const title = (element as HTMLElement).getAttribute('data-title');
          return { syntax, title };
        },
      },
    ];
  },

  renderHTML({ HTMLAttributes }) {
    return [
      'div',
      mergeAttributes(
        { 'data-type': 'mermaid-diagram', 'class': 'mermaid-node' },
        this.options.HTMLAttributes,
        HTMLAttributes
      ),
    ];
  },

  addNodeView() {
    return ReactNodeViewRenderer(MermaidNodeView);
  },

  addCommands() {
    return {
      insertMermaidDiagram:
        (options) =>
        ({ commands }) => {
          return commands.insertContent({
            type: this.name,
            attrs: options,
          });
        },
    };
  },
});

// Helper function to insert diagram after specific text
export function insertDiagramAfterText(
  editor: any, 
  searchText: string, 
  mermaidSyntax: string, 
  title?: string
): boolean {
  console.log(`🔍 Searching for text: "${searchText}"`);
  console.log(`📊 Diagram syntax: "${mermaidSyntax.substring(0, 50)}..."`);
  
  const { state } = editor;
  let insertPosition: number | null = null;
  let foundText = "";
  
  // Find the text in the document
  state.doc.descendants((node: any, pos: number) => {
    if (insertPosition !== null) return false; // Already found
    
    if (node.isText && node.text) {
      const normalizedText = node.text.toLowerCase();
      const normalizedSearch = searchText.toLowerCase().trim();
      const index = normalizedText.indexOf(normalizedSearch);
      
      if (index !== -1) {
        // Position after the found text
        insertPosition = pos + index + searchText.length;
        foundText = node.text.substring(index, index + searchText.length);
        console.log(`✅ Found text at position ${insertPosition}: "${foundText}"`);
        return false; // Stop searching
      }
    }
  });
  
  if (insertPosition !== null) {
    console.log(`📍 Inserting diagram at position ${insertPosition}`);
    try {
      // Insert a new paragraph and then the diagram
      const result = editor
        .chain()
        .focus()
        .setTextSelection(insertPosition)
        .insertContent('\n\n') // Add some spacing
        .insertMermaidDiagram({ syntax: mermaidSyntax, title })
        .insertContent('\n') // Add spacing after diagram
        .run();
      
      console.log(`📊 insertMermaidDiagram result: ${result}`);
      return true;
    } catch (error) {
      console.error('❌ Diagram insertion at found position failed:', error);
    }
  }
  
  // 🎯 Improvement: If text matching fails, fallback to current cursor position
  console.warn(`⚠️ Cannot find specified text "${searchText}", will insert diagram at cursor position`);
  
  try {
    const result = editor
      .chain()
      .focus()
      .insertContent('\n\n') // Add some spacing
      .insertMermaidDiagram({ syntax: mermaidSyntax, title })
      .insertContent('\n') // Add spacing after diagram
      .run();
    
    console.log(`📊 Fallback insertMermaidDiagram result: ${result}`);
    return true;
  } catch (error) {
    console.error('❌ Diagram insertion failed:', error);
    return false;
  }
}