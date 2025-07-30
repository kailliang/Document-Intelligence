import { useEffect, useState } from "react";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";

const extensions = [StarterKit];

export interface EditorProps {
  handleEditorChange: (content: string) => void;
  content: string;
}

export default function Editor({ handleEditorChange, content }: EditorProps) {
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
