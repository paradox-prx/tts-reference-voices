import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// `npm run dev` proxies the API to a running studio backend (STUDIO_PORT, default 8100)
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": `http://127.0.0.1:${process.env.STUDIO_PORT ?? 8100}` } },
  build: { outDir: "dist", chunkSizeWarningLimit: 900 },
});
