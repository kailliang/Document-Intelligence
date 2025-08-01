import { useEffect, useState } from "react";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { Highlight } from "./HighlightExtension";
import "./highlight.css";

const extensions = [
  StarterKit,
  Highlight.configure({
    multicolor: true,
    HTMLAttributes: {
      class: 'text-highlight',
    },
  }),
];

export interface EditorProps {
  handleEditorChange: (content: string) => void;
  content: string;
  onEditorReady?: (editor: any) => void;  // 新增：编辑器实例回调
}

export default function Editor({ handleEditorChange, content, onEditorReady }: EditorProps) {
  const [isLoading, setIsLoading] = useState<boolean>(false);
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
      setIsLoading(true);
      editor.commands.setContent(content);
      setIsLoading(false);
    }
  }, [content, editor]);

  return (
    <>
      {isLoading && <div>Loading...</div>}
      <EditorContent editor={editor}></EditorContent>
    </>
  );
}
