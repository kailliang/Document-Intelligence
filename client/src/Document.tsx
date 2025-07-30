import Editor from "./internal/Editor";
import useWebSocket from "react-use-websocket";
import { debounce } from "lodash";
import { useCallback, useEffect, useState } from "react";

export interface DocumentProps {
  onContentChange: (content: string) => void;
  content: string;
}

const SOCKET_URL = "ws://localhost:8000/ws";

export default function Document({ onContentChange, content }: DocumentProps) {
  const [messageHistory, setMessageHistory] = useState<MessageEvent[]>([]);

  const { sendMessage, lastMessage } = useWebSocket(SOCKET_URL, {
    onOpen: () => console.log("WebSocket Connected"),
    onClose: () => console.log("WebSocket Disconnected"),
    shouldReconnect: (_closeEvent) => true,
    // Optionally, you can configure WebSocket options here
  });

  useEffect(() => {
    if (lastMessage !== null) {
      setMessageHistory((prev) => prev.concat(lastMessage));
      // Handle the incoming message as needed. For example, update the editor content or display suggestions.
      console.log(lastMessage.data);
    }
  }, [lastMessage, setMessageHistory]);

  // Debounce editor content changes
  const sendEditorContent = useCallback(
    debounce((content: string) => {
      sendMessage(content);
    }, 500), // Adjust debounce time as needed
    [sendMessage]
  );

  const handleEditorChange = (content: string) => {
    onContentChange(content);
    sendEditorContent(content);
  };

  return (
    <div className="w-full h-full overflow-y-auto">
      <Editor handleEditorChange={handleEditorChange} content={content} />
    </div>
  );
}
