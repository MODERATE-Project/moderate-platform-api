import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";
import type { Connect, Plugin } from "vite";

const apiTarget = process.env.VITE_PROXY_API_TARGET || "http://localhost:8000";

function runtimeConfigPlugin(env: Record<string, string>): Plugin {
  const middleware: Connect.NextHandleFunction = (request, response, next) => {
    if (request.url?.split("?")[0] !== "/config.json") {
      next();
      return;
    }

    response.setHeader("Content-Type", "application/json");
    response.setHeader("Cache-Control", "no-store");

    const url = env.MODERATE_UI_KEYCLOAK_URL;

    if (!url?.trim()) {
      response.statusCode = 503;
      response.end();
      return;
    }

    response.end(
      JSON.stringify({
        url,
        realm: env.MODERATE_UI_KEYCLOAK_REALM || "moderate",
        clientId: env.MODERATE_UI_KEYCLOAK_CLIENT_ID || "ui",
      }),
    );
  };

  return {
    name: "runtime-auth-config",
    configureServer(server) {
      server.middlewares.use(middleware);
    },
    configurePreviewServer(server) {
      server.middlewares.use(middleware);
    },
  };
}

export default defineConfig(({ mode }) => ({
  plugins: [
    react(),
    runtimeConfigPlugin(loadEnv(mode, process.cwd(), "MODERATE_UI_KEYCLOAK_")),
  ],
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
}));
