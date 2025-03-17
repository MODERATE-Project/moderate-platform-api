import { AuthProvider } from "@refinedev/core";
import axios from "axios";
import Keycloak from "keycloak-js";

export interface IIdentity {
  username: string;
  email: string;
  emailVerified?: boolean;
  name?: string;
  familyName?: string;
  givenName?: string;
}

export type ExtendedAuthProvider = AuthProvider & {
  refreshToken: () => Promise<void>;
  getSignUpUrl: () => string;
};

export function buildKeycloakAuthProvider({
  keycloak,
  refreshMinValidity = 30,
}: {
  keycloak: Keycloak;
  refreshMinValidity?: number;
}): ExtendedAuthProvider {
  const refreshToken = async () => {
    if (!keycloak.authenticated || !keycloak.token) {
      return;
    }

    try {
      const refreshed = await keycloak.updateToken(refreshMinValidity);

      if (refreshed) {
        console.debug("Updated default headers with new token");

        axios.defaults.headers.common = {
          Authorization: `Bearer ${keycloak.token}`,
        };
      }
    } catch (error) {
      console.error("Failed to refresh token", error);
    }
  };

  const authProvider: ExtendedAuthProvider = {
    refreshToken,
    login: async () => {
      const urlSearchParams = new URLSearchParams(window.location.search);
      const { to } = Object.fromEntries(urlSearchParams.entries());

      await keycloak.login({
        redirectUri: to ? `${window.location.origin}${to}` : undefined,
      });

      return {
        success: true,
      };
    },
    logout: async () => {
      try {
        await keycloak.logout({
          redirectUri: window.location.origin,
        });

        return {
          success: true,
          redirectTo: "/login",
        };
      } catch (error) {
        return {
          success: false,
          error: new Error("Logout failed"),
        };
      }
    },
    onError: async (error) => {
      console.error(error);
      return { error };
    },
    check: async () => {
      try {
        await refreshToken();

        const { token } = keycloak;

        if (token) {
          axios.defaults.headers.common = {
            Authorization: `Bearer ${token}`,
          };

          axios.defaults.withCredentials = true;

          return {
            authenticated: true,
          };
        } else {
          return {
            authenticated: false,
            logout: true,
            redirectTo: "/login",
            error: {
              message: "Check failed",
              name: "Token not found",
            },
          };
        }
      } catch (error) {
        return {
          authenticated: false,
          logout: true,
          redirectTo: "/login",
          error: {
            message: "Check failed",
            name: "Token not found",
          },
        };
      }
    },
    getPermissions: async () => null,
    getIdentity: async (): Promise<IIdentity | null> => {
      if (!keycloak?.tokenParsed) {
        return null;
      }

      const identity: IIdentity = {
        username: keycloak.tokenParsed.preferred_username,
        name: keycloak.tokenParsed.name,
        email: keycloak.tokenParsed.email,
        emailVerified: keycloak.tokenParsed.email_verified,
        familyName: keycloak.tokenParsed.family_name,
        givenName: keycloak.tokenParsed.given_name,
      };

      return identity;
    },
    getSignUpUrl: () => {
      return keycloak.createRegisterUrl();
    },
  };

  return authProvider;
}
