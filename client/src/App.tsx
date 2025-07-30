import Document from "./Document";
import { useEffect, useState } from "react";
import axios from "axios";
import LoadingOverlay from "./internal/LoadingOverlay";
import Logo from "./assets/logo.png";
import { useMutation, useQuery } from "@tanstack/react-query";


const BACKEND_URL = "http://localhost:8000";

function App() {
  const [currentDocumentContent, setCurrentDocumentContent] =
    useState<string>("");
  const [currentDocumentId, setCurrentDocumentId] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  // Load the first patent on mount
  useEffect(() => {
    loadPatent(1);
  }, []);

  // Callback to load a patent from the backend
  const loadPatent = async (documentNumber: number) => {
    setIsLoading(true);
    console.log("Loading patent:", documentNumber);
    try {
      const response = await axios.get(
        `${BACKEND_URL}/document/${documentNumber}`
      );
      setCurrentDocumentContent(response.data.content);
      setCurrentDocumentId(documentNumber);
    } catch (error) {
      console.error("Error loading document:", error);
    }
    setIsLoading(false);
  };

  // Callback to persist a patent in the DB
  const savePatent = async (documentNumber: number) => {
    setIsLoading(true);
    try {
      await axios.post(`${BACKEND_URL}/save/${documentNumber}`, {
        content: currentDocumentContent,
      });
    } catch (error) {
      console.error("Error saving document:", error);
    }
    setIsLoading(false);
  };

  return (
    <div className="flex flex-col h-full w-full">
      {isLoading && <LoadingOverlay />}
      <header className="flex items-center justify-center top-0 w-full bg-black text-white text-center z-50 mb-[30px] h-[80px]">
        <img src={Logo} alt="Logo" style={{ height: "50px" }} />
      </header>
      <div className="flex w-full bg-white h=[calc(100%-100px) gap-4 justify-center box-shadow">
        <div className="flex flex-col h-full items-center gap-2 px-4">
          <button onClick={() => loadPatent(1)}>Patent 1</button>
          <button onClick={() => loadPatent(2)}>Patent 2</button>
        </div>
        <div className="flex flex-col h-full items-center gap-2 px-4 flex-1">
          <h2 className="self-start text-[#213547] opacity-60 text-2xl font-semibold">{`Patent ${currentDocumentId}`}</h2>
          <Document
            onContentChange={setCurrentDocumentContent}
            content={currentDocumentContent}
          />
        </div>
        <div className="flex flex-col h-full items-center gap-2 px-4">
          <button onClick={() => savePatent(currentDocumentId)}>Save</button>
        </div>
      </div>
    </div>
  );
}

export default App;
