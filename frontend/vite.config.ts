import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => ({
  plugins: [react()],

  /* ------------------------------------------------------------------ */
  /* Dev server                                                         */
  /* ------------------------------------------------------------------ */
  server: {
    port: 5173,
    strictPort: false,
    host: true, // expose on LAN so you can test from a phone
    proxy: {
      // Forward /api/* to the local backend during dev.
      // Your code can then fetch("/api/v1/...") with no CORS issues.
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        secure: false,
      },
      // WebSocket proxy for the live incident feed
      "/ws": {
        target: "ws://localhost:8000",
        ws: true,
      },
    },
  },

  /* ------------------------------------------------------------------ */
  /* Preview server (npm run preview)                                   */
  /* ------------------------------------------------------------------ */
  preview: {
    port: 4173,
    host: true,
  },

  /* ------------------------------------------------------------------ */
  /* Build                                                              */
  /* ------------------------------------------------------------------ */
  build: {
    target: "es2020",
    outDir: "dist",
    sourcemap: mode === "development",
    cssCodeSplit: true,
    minify: "esbuild",
    chunkSizeWarningLimit: 800,
    rollupOptions: {
      output: {
        // Split vendor libraries so a React bump doesn't bust the cache
        // for users who already have lucide icons cached, and vice versa.
        manualChunks: {
          react: ["react", "react-dom"],
          icons: ["lucide-react"],
        },
      },
    },
  },

  /* ------------------------------------------------------------------ */
  /* Misc                                                               */
  /* ------------------------------------------------------------------ */
  envDir: ".",
  envPrefix: "VITE_",
  clearScreen: false,
  logLevel: "info",
}));
