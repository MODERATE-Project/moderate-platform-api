import { Box, Button, Space, Text } from "@mantine/core";
import { useLogin, useTranslate } from "@refinedev/core";
import { ThemedTitleV2 } from "@refinedev/mantine";

export const Login: React.FC = () => {
  const { mutate: login } = useLogin();

  const t = useTranslate();

  return (
    <Box
      sx={{
        height: "100vh",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <ThemedTitleV2
        collapsed={false}
        wrapperStyles={{
          fontSize: "22px",
        }}
      />
      <Space h="xl" />

      <Button
        style={{ width: "240px" }}
        type="button"
        variant="filled"
        onClick={() => login({})}
      >
        {t("pages.login.signin", "Sign in")}
      </Button>
      <Space h="xl" />
      <Text fz="sm" color="gray">
        Powered by
        <img
          style={{ padding: "0 5px" }}
          alt="Keycloak"
          src="https://refine.ams3.cdn.digitaloceanspaces.com/superplate-auth-icons%2Fkeycloak.svg"
        />
        Keycloak
      </Text>
    </Box>
  );
};
