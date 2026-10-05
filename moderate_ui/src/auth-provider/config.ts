import type { KeycloakConfig } from "keycloak-js";

export async function loadKeycloakConfig(): Promise<Required<KeycloakConfig>> {
  const response = await fetch("/config.json", { cache: "no-store" });

  if (!response.ok) {
    throw new Error(`Authentication configuration returned ${response.status}`);
  }

  const config: unknown = await response.json();

  if (config === null || typeof config !== "object") {
    throw new Error("Invalid authentication configuration");
  }

  const { url, realm, clientId } = config as Record<string, unknown>;

  if (
    typeof url !== "string" ||
    !url.trim() ||
    typeof realm !== "string" ||
    !realm.trim() ||
    typeof clientId !== "string" ||
    !clientId.trim()
  ) {
    throw new Error(
      "Authentication configuration requires url, realm, clientId",
    );
  }

  return { url, realm, clientId };
}
