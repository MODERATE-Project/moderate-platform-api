import { ReactKeycloakProvider } from "@react-keycloak/web";
import Keycloak from "keycloak-js";
import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./i18n";

const keycloak = new Keycloak({
  clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID,
  url: import.meta.env.VITE_KEYCLOAK_URL,
  realm: import.meta.env.VITE_KEYCLOAK_REALM,
});

const container = document.getElementById("root") as HTMLElement;
const root = createRoot(container);

root.render(
  <React.Suspense fallback="loading">
    <ReactKeycloakProvider authClient={keycloak}>
      <App />
    </ReactKeycloakProvider>
  </React.Suspense>,
);
