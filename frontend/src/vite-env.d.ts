/// <reference types="vite/client" />

/* ==================================================================
   Vite environment variables
   ==================================================================
   Anything you read via `import.meta.env.VITE_*` at runtime must be
   declared here so TypeScript stops complaining and autocomplete works.
   ================================================================== */

interface ImportMetaEnv {
  /** Backend base URL. Example: "https://ajali-alert.onrender.com". */
  readonly VITE_API_URL?: string;

  /** WebSocket base URL. Falls back to VITE_API_URL with ws:// if unset. */
  readonly VITE_WS_URL?: string;

  /** Build mode: "development" | "production" | "test". */
  readonly MODE: string;

  /** True during `vite dev`, false during `vite build`. */
  readonly DEV: boolean;

  /** True during `vite build`. */
  readonly PROD: boolean;

  /** True during `vite test` (Vitest). */
  readonly SSR: boolean;

  /** Base URL path, defaults to "/". */
  readonly BASE_URL: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

/* ==================================================================
   Optional: narrow useful globals
   ================================================================== */

// Some analytics / Sentry SDKs attach to window. Add here if you use any:
// interface Window {
//   __AJALI_VERSION__?: string;
// }

/* ==================================================================
   Ensure this file is treated as a module (prevents global leakage).
   ================================================================== */
export {};
