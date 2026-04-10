import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:5050",
        changeOrigin: true,
        // Whisper + Gemini can exceed default proxy timeouts (502 BAD GATEWAY)
        timeout: 600_000,
        proxyTimeout: 600_000,
      },
    },
  },
});
