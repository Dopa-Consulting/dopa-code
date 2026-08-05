import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./index.css";

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").then(
      () => console.log("[sw] Registered"),
      (err) => console.warn("[sw] Registration failed:", err)
    );
  });

  // Escuchar mensajes del SW (Background Sync triggers)
  navigator.serviceWorker.addEventListener("message", (event) => {
    if (event.data?.type === "bg-sync" && event.data?.tag === "flush-pending") {
      import("./services/sync").then(({ flushPendingActions }) => {
        flushPendingActions();
      });
    }
  });
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>
);
