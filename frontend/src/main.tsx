import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { ErrorBoundary } from "./ErrorBoundary";
import "./styles.css";

/* ------------------------------------------------------------------ */
/* Root element                                                        */
/* ------------------------------------------------------------------ */

const container = document.getElementById("root");

if (!container) {
  // Fail loudly rather than silently mounting nowhere
  throw new Error(
    'Ajali Alert: missing #root element. Check that index.html contains <div id="root"></div>.',
  );
}

/* ------------------------------------------------------------------ */
/* Global error handlers                                              */
/* ------------------------------------------------------------------ */

// Catch errors that escape React (async, event handlers, promises)
window.addEventListener("error", (event) => {
  console.error("[ajali] uncaught error", event.error ?? event.message);
});

window.addEventListener("unhandledrejection", (event) => {
  console.error("[ajali] unhandled promise rejection", event.reason);
});

/* ------------------------------------------------------------------ */
/* Render                                                             */
/* ------------------------------------------------------------------ */

const root = createRoot(container);

root.render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>,
);

/* ------------------------------------------------------------------ */
/* Service worker (optional — remove if you don't have one)           */
/* ------------------------------------------------------------------ */

if ("serviceWorker" in navigator && import.meta.env.PROD) {
  window.addEventListener("load", () => {
    navigator.serviceWorker
      .register("/sw.js")
      .catch((err) => console.warn("[ajali] service worker registration failed", err));
  });
}
