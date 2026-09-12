import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => ({
  plugins: [react()],

  server: {
    port: 5173,
    strictPort: false,
    host: true,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        secure: false,
      },
      "/ws": {
        target: "ws://localhost:8000",
        ws: true,
      },
    },
  },

  preview: {
    port: 4173,
    host: true,
  },

  build: {
    target: "es2020",
    outDir: "dist",
    sourcemap: mode === "development",
    cssCodeSplit: true,
    minify: "esbuild",
    chunkSizeWarningLimit: 800,
    rollupOptions: {
      output: {
        // rolldown requires a function, not an object
        manualChunks(id) {
          if (id.includes("node_modules/react/") || id.includes("node_modules/react-dom/")) {
            return "react";
          }
          if (id.includes("node_modules/lucide-react/")) {
            return "icons";
          }
          if (id.includes("node_modules/")) {
            return "vendor";
          }
          return undefined;
        },
      },
    },
  },

  envDir: ".",
  envPrefix: "VITE_",
  clearScreen: false,
  logLevel: "info",
}));
