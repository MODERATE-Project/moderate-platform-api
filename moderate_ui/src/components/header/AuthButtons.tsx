import { Button, Text, ThemeIcon } from "@mantine/core";
import { IconLogin, IconUser, IconUserPlus } from "@tabler/icons-react";
import React from "react";

interface AuthButtonsProps {
  isAuthenticated?: boolean;
  identityName?: string;
  onLogin: () => void;
  onLogout: () => void;
  onRegister: () => void;
  t: (key: string, defaultValue: string) => string;
}

/**
 * Authentication buttons component
 * Displays login/register buttons when not authenticated
 * Displays user info and logout button when authenticated
 */
export const AuthButtons: React.FC<AuthButtonsProps> = ({
  isAuthenticated,
  identityName,
  onLogin,
  onLogout,
  onRegister,
  t,
}) => {
  if (isAuthenticated === false) {
    return (
      <>
        <Button
          variant="light"
          onClick={onLogin}
          leftIcon={<IconLogin size={16} />}
        >
          {t("nav.logIn", "Log in")}
        </Button>
        <Button
          variant="filled"
          color="blue"
          onClick={onRegister}
          leftIcon={<IconUserPlus size={16} />}
        >
          {t("nav.signUp", "Sign up")}
        </Button>
      </>
    );
  }

  if (isAuthenticated === true) {
    return (
      <>
        <ThemeIcon variant="light" color="blue" style={{ flexGrow: 0 }}>
          <IconUser size="1em" />
        </ThemeIcon>
        <Text fw={500} size="sm">
          {identityName}
        </Text>
        <Button onClick={onLogout} variant="filled" color="gray">
          {t("nav.logOut", "Logout")}
        </Button>
      </>
    );
  }

  return null;
};
