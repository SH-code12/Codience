import { useEffect } from "react";
import "./App.css";
import Welcome from "./components/Welcome";

function App() {
  // Send a message to the extension
  const vscode = (window as any).acquireVsCodeApi();

  function sendMessage() {
    vscode.postMessage({ text: "Hello from React + Vite!" });
  }
  // Listen for messages from the extension
  useEffect(() => {
    window.addEventListener("message", (event) => {
      console.log("Message from extension:", event.data);
    });
  }, []);

  return (
    <>
      <Welcome />
    </>
  );
}

export default App;
