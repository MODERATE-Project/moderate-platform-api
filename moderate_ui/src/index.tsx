import { ReactKeycloakProvider } from "@react-keycloak/web";
import Keycloak from "keycloak-js";
import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { loadKeycloakConfig } from "./auth-provider/config";
import "./i18n";

const container = document.getElementById("root") as HTMLElement;
const root = createRoot(container);

root.render(<p>Loading...</p>);

async function bootstrap(): Promise<void> {
  try {
    const config = await loadKeycloakConfig();
    const keycloak = new Keycloak(config);

    root.render(
      <React.Suspense fallback="loading">
        <ReactKeycloakProvider authClient={keycloak}>
          <App />
        </ReactKeycloakProvider>
      </React.Suspense>,
    );
  } catch (error) {
    console.error("Failed to load authentication configuration", error);
    root.render(
      <main role="alert">
        <p>Authentication configuration is unavailable.</p>
        <p>Reload the page or contact the administrator.</p>
        <button onClick={() => window.location.reload()}>Reload</button>
      </main>,
    );
  }
}

void bootstrap();
