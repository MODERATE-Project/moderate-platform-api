import { useKeycloak } from "@react-keycloak/web";
import { useCallback, useEffect } from "react";
import { buildKeycloakAuthProvider } from "./keycloak";

export function useRefreshToken({
  intervalMs = 25000,
}: { intervalMs?: number } = {}) {
  const { keycloak, initialized } = useKeycloak();

  const refreshToken = useCallback(async () => {
    if (!initialized) {
      return;
    }

    const authProvider = buildKeycloakAuthProvider({ keycloak });
    await authProvider.refreshToken();
  }, [initialized, keycloak]);

  useEffect(() => {
    if (!intervalMs) {
      refreshToken();
      return;
    }

    const intervalId = setInterval(() => {
      refreshToken();
    }, intervalMs);

    return () => clearInterval(intervalId);
  }, [intervalMs, refreshToken]);
}
