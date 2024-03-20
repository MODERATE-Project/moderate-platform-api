import { Box, Button, Space } from "@mantine/core";
import { useLogin, useTranslate } from "@refinedev/core";
import { IconLogin } from "@tabler/icons";

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
      <Box style={{ height: 70 }}>
        <img
          src="/images/moderate-logo-wide.png"
          alt="MODERATE"
          style={{ maxHeight: "100%" }}
        />
      </Box>
      <Space h="xl" />
      <Button
        type="button"
        variant="filled"
        size="lg"
        leftIcon={<IconLogin />}
        onClick={() => login({})}
      >
        {t("pages.login.signin", "Sign in")}
      </Button>
    </Box>
  );
};
