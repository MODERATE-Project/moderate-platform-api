import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const apiTarget = process.env.VITE_PROXY_API_TARGET || "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // This is necessary to allow the frontend to communicate with the backend API
      "/api": {
        target: apiTarget,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
      // Notebooks are a special case to enable embedding in iframes
      "^/notebook-.*": {
        target: apiTarget,
        changeOrigin: true,
        ws: true,
      },
    },
  },
});
