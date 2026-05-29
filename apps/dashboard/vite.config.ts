import react from "@vitejs/plugin-react";
import { resolve } from "node:path";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@kk/contracts": resolve(__dirname, "../../packages/contracts/src/index.ts") },
  },
  server: {
    port: 5173,
    proxy: { "/api": "http://localhost:8000", "/enroll": "http://localhost:8000" },
  },
});
