import { useEffect } from "react";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Image from "@tiptap/extension-image";
import { Highlight } from "./HighlightExtension";
import { WordLevelStrikethroughExtension } from "./StrikethroughExtension";
import { MermaidNode } from "./MermaidExtension";
import "./highlight.css";

const extensions = [
  StarterKit,
  Image.configure({
    HTMLAttributes: {
      class: 'editor-image',
      style: 'width:300px; height: auto;objectFit:contain;'
    },
    allowBase64: true,
    inline: true,
  }),
  Highlight.configure({
    multicolor: true,
    HTMLAttributes: {
      class: 'text-highlight',
    },
  }),
  WordLevelStrikethroughExtension.configure({
    HTMLAttributes: {
      class: 'word-level-strikethrough-extension',
    },
  }),
  MermaidNode.configure({
    HTMLAttributes: {
      class: 'mermaid-node',
    },
  }),
];

export interface EditorProps {
  handleEditorChange: (content: string) => void;
  content: string;
  onEditorReady?: (editor: any) => void;  // Added: editor instance callback
}

export default function Editor({ handleEditorChange, content, onEditorReady }: EditorProps) {
  const editor = useEditor({
    content: content,
    extensions: extensions,
    onUpdate: ({ editor }) => {
      const html = editor.getHTML();
      handleEditorChange(html);
    },
  });

  useEffect(() => {
    if (editor && onEditorReady) {
      onEditorReady(editor);
    }
  }, [editor, onEditorReady]);

  useEffect(() => {
    if (editor && content !== editor.getHTML()) {
      const currentContent = editor.getHTML();
      // Only sync when content is truly different and not from internal editor updates
      if (content.trim() !== currentContent.trim()) {
        editor.commands.setContent(content, false); // false = don't trigger update event
      }
    }
  }, [content, editor]);

  return (
    <EditorContent editor={editor}></EditorContent>
  );
}
