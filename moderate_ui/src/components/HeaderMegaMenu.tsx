import {
  Box,
  Burger,
  Button,
  Center,
  Collapse,
  Divider,
  Drawer,
  Group,
  Header,
  HoverCard,
  ScrollArea,
  SimpleGrid,
  Text,
  ThemeIcon,
  UnstyledButton,
  createStyles,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import {
  useActiveAuthProvider,
  useGetIdentity,
  useIsAuthenticated,
  useLogin,
  useLogout,
} from "@refinedev/core";
import { IconBox, IconChevronDown, IconUser } from "@tabler/icons-react";
import { useCallback, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

const useStyles = createStyles((theme) => ({
  link: {
    display: "flex",
    alignItems: "center",
    height: "100%",
    paddingLeft: theme.spacing.md,
    paddingRight: theme.spacing.md,
    textDecoration: "none",
    color: theme.colorScheme === "dark" ? theme.white : theme.black,
    fontWeight: 500,
    fontSize: theme.fontSizes.sm,

    [theme.fn.smallerThan("md")]: {
      height: 42,
      display: "flex",
      alignItems: "center",
      width: "100%",
    },

    ...theme.fn.hover({
      backgroundColor:
        theme.colorScheme === "dark"
          ? theme.colors.dark[6]
          : theme.colors.gray[0],
    }),
  },

  subLink: {
    width: "100%",
    padding: `${theme.spacing.xs}px ${theme.spacing.md}px`,
    borderRadius: theme.radius.md,

    ...theme.fn.hover({
      backgroundColor:
        theme.colorScheme === "dark"
          ? theme.colors.dark[7]
          : theme.colors.gray[0],
    }),

    "&:active": theme.activeStyles,
  },

  dropdownFooter: {
    backgroundColor:
      theme.colorScheme === "dark"
        ? theme.colors.dark[7]
        : theme.colors.gray[0],
    margin: -theme.spacing.md,
    marginTop: theme.spacing.sm,
    padding: `${theme.spacing.md}px ${theme.spacing.md * 2}px`,
    paddingBottom: theme.spacing.xl,
    borderTop: `1px solid ${
      theme.colorScheme === "dark" ? theme.colors.dark[5] : theme.colors.gray[1]
    }`,
  },

  hiddenMobile: {
    [theme.fn.smallerThan("md")]: {
      display: "none",
    },
  },

  hiddenDesktop: {
    [theme.fn.largerThan("md")]: {
      display: "none",
    },
  },
}));

type IIdentity = {
  name: string;
};

export function HeaderMegaMenu() {
  const { t } = useTranslation();
  const authProvider = useActiveAuthProvider();
  const { isLoading, data } = useIsAuthenticated();
  const { data: identity } = useGetIdentity<IIdentity>();

  const { mutate: mutateLogout } = useLogout({
    v3LegacyAuthProviderCompatible: Boolean(authProvider?.isLegacy),
  });

  const { mutate: login } = useLogin();

  const onLogout = useCallback(() => {
    mutateLogout();
  }, [mutateLogout]);

  const onLogin = useCallback(() => {
    login({});
  }, [login]);

  const isAuthenticated = useMemo((): boolean | undefined => {
    if (isLoading) {
      return undefined;
    }

    return data?.authenticated;
  }, [isLoading, data]);

  const [drawerOpened, { toggle: toggleDrawer, close: closeDrawer }] =
    useDisclosure(false);

  const [linksOpened, { toggle: toggleLinks }] = useDisclosure(false);
  const { classes, theme } = useStyles();

  const megaMenuItems = useMemo(() => {
    return [
      {
        to: "/assets",
        icon: IconBox,
        title: t("nav.assets", "Assets"),
        description: t(
          "nav.megaMenu.assets",
          "Datasets published to the MODERATE platform"
        ),
      },
    ];
  }, [t]);

  const megaMenuLinks = megaMenuItems.map((item) => (
    <UnstyledButton
      component={Link}
      to={item.to}
      className={classes.subLink}
      key={item.title}
    >
      <Group noWrap align="flex-start">
        <ThemeIcon size={34} variant="default" radius="md">
          <item.icon size={22} color={theme.fn.primaryColor()} />
        </ThemeIcon>
        <div>
          <Text size="sm" weight={500}>
            {item.title}
          </Text>
          <Text size="xs" color="dimmed">
            {item.description}
          </Text>
        </div>
      </Group>
    </UnstyledButton>
  ));

  const authButtons = useMemo(() => {
    return (
      <>
        {isAuthenticated === false && (
          <>
            <Button onClick={onLogin}>{t("nav.logIn", "Log in")}</Button>
            <Button disabled>{t("nav.signUp", "Sign up")}</Button>
          </>
        )}
        {isAuthenticated === true && (
          <>
            <ThemeIcon variant="light" color="blue" style={{ flexGrow: 0 }}>
              <IconUser size="1em" />
            </ThemeIcon>
            <Text fw={500} size="sm">
              {identity?.name}
            </Text>
            <Button onClick={onLogout} variant="filled" color="gray">
              {t("nav.logOut", "Logout")}
            </Button>
          </>
        )}
      </>
    );
  }, [isAuthenticated, onLogout, identity, onLogin, t]);

  const mainLinks = useMemo(() => {
    return (
      <>
        <Link className={classes.link} to="/catalogue">
          {t("nav.catalogue", "Catalogue")}
        </Link>
        <Link className={classes.link} to="/tools">
          {t("nav.tools", "Tools")}
        </Link>
      </>
    );
  }, [classes.link, t]);

  return (
    <Box>
      <Header height={60} px="md">
        <Group position="apart" sx={{ height: "100%" }}>
          <Box style={{ height: "55%" }}>
            <Link to="/">
              <img
                src="/images/moderate-logo-wide.png"
                style={{ height: "100%" }}
              />
            </Link>
          </Box>

          <Group
            sx={{ height: "100%" }}
            spacing={0}
            className={classes.hiddenMobile}
          >
            {mainLinks}

            {isAuthenticated === true && (
              <HoverCard
                width={600}
                position="bottom"
                radius="md"
                shadow="md"
                withinPortal
              >
                <HoverCard.Target>
                  <a href="#" className={classes.link}>
                    <Center inline>
                      <Box component="span" mr={5}>
                        {t("nav.platformFeatures", "Platform Features")}
                      </Box>
                      <IconChevronDown
                        size={16}
                        color={theme.fn.primaryColor()}
                      />
                    </Center>
                  </a>
                </HoverCard.Target>

                <HoverCard.Dropdown sx={{ overflow: "hidden" }}>
                  <Group position="apart" px="md">
                    <Text weight={500}>
                      {t("nav.platformFeatures", "Platform Features")}
                    </Text>
                  </Group>

                  <Divider
                    my="sm"
                    mx="-md"
                    color={theme.colorScheme === "dark" ? "dark.5" : "gray.1"}
                  />

                  <SimpleGrid cols={2} spacing={0}>
                    {megaMenuLinks}
                  </SimpleGrid>
                </HoverCard.Dropdown>
              </HoverCard>
            )}
          </Group>

          <Group className={classes.hiddenMobile}>{authButtons}</Group>

          <Burger
            opened={drawerOpened}
            onClick={toggleDrawer}
            className={classes.hiddenDesktop}
          />
        </Group>
      </Header>

      <Drawer
        opened={drawerOpened}
        onClose={closeDrawer}
        size="100%"
        padding="md"
        title="MODERATE"
        className={classes.hiddenDesktop}
        zIndex={1000000}
      >
        <ScrollArea sx={{ height: "calc(100vh - 60px)" }} mx="-md">
          <Divider
            my="sm"
            color={theme.colorScheme === "dark" ? "dark.5" : "gray.1"}
          />

          {mainLinks}

          {isAuthenticated === true && (
            <>
              <UnstyledButton className={classes.link} onClick={toggleLinks}>
                <Center inline>
                  <Box component="span" mr={5}>
                    {t("nav.platformFeatures", "Platform Features")}
                  </Box>
                  <IconChevronDown size={16} color={theme.fn.primaryColor()} />
                </Center>
              </UnstyledButton>

              <Collapse in={linksOpened}>
                <Box ml="sm">{megaMenuLinks}</Box>
              </Collapse>
            </>
          )}

          <Divider
            my="sm"
            color={theme.colorScheme === "dark" ? "dark.5" : "gray.1"}
          />

          <Group position="center" grow pb="xl" px="md">
            {authButtons}
          </Group>
        </ScrollArea>
      </Drawer>
    </Box>
  );
}
