import {
  Box,
  Burger,
  Center,
  Collapse,
  Divider,
  Drawer,
  Group,
  Header,
  HoverCard,
  ScrollArea,
  Text,
  UnstyledButton,
  createStyles,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { useKeycloak } from "@react-keycloak/web";
import {
  useActiveAuthProvider,
  useGetIdentity,
  useIsAuthenticated,
  useLogin,
  useLogout,
} from "@refinedev/core";
import {
  IconBolt,
  IconChevronDown,
  IconDatabase,
  IconFileSearch,
  IconFolders,
  IconTimeline,
  IconTools,
} from "@tabler/icons-react";
import { useCallback, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import {
  buildKeycloakAuthProvider,
  IIdentity,
} from "../auth-provider/keycloak";
import { AuthButtons } from "./header/AuthButtons";
import { MainNavLinks } from "./header/MainNavLinks";
import { MegaMenuItem, MegaMenuItems } from "./header/MegaMenuItems";
import { platformApplications } from "../data/platformApplications";

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

export function HeaderMegaMenu() {
  const { t } = useTranslation();
  const authProvider = useActiveAuthProvider();
  const { isLoading, data } = useIsAuthenticated();
  const { data: identity } = useGetIdentity<IIdentity>();

  const { mutate: mutateLogout } = useLogout({
    v3LegacyAuthProviderCompatible: Boolean(authProvider?.isLegacy),
  });

  const { mutate: login } = useLogin();
  const { keycloak, initialized } = useKeycloak();

  const onLogout = useCallback(() => {
    mutateLogout();
  }, [mutateLogout]);

  const onLogin = useCallback(() => {
    login({});
  }, [login]);

  const onRegister = useCallback(() => {
    if (!initialized) {
      return;
    }

    const authProvider = buildKeycloakAuthProvider({ keycloak });
    window.location.href = authProvider.getSignUpUrl();
  }, [keycloak, initialized]);

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

  const mainMenuItems: MegaMenuItem[] = useMemo(() => {
    return [
      {
        to: "/catalogue",
        icon: IconDatabase,
        title: t("nav.datasetCatalogue", "Dataset Catalogue"),
        description: t(
          "nav.megaMenu.datasetCatalogue",
          "Browse, search and download published datasets",
        ),
      },
      {
        to: "/workflows/exploratory",
        icon: IconFileSearch,
        title: t("nav.dataExploration", "Data Exploration"),
        description: t(
          "nav.megaMenu.dataExploration",
          "Download and visualize datasets",
        ),
      },
      {
        to: "https://moderate-project.github.io/moderate-docs/tools-and-services/",
        icon: IconTools,
        title: t("nav.toolsCatalogue", "Tools & Services Catalogue"),
        description: t(
          "nav.megaMenu.toolsCatalogue",
          "Tools and services in the MODERATE ecosystem",
        ),
        external: true,
      },
      {
        to: "/assets",
        icon: IconFolders,
        title: t("nav.myAssets", "My Assets"),
        description: t(
          "nav.megaMenu.myAssets",
          "Create, edit and manage the assets you own",
        ),
      },
    ];
  }, [t]);

  const applicationMenuItems: MegaMenuItem[] = useMemo(() => {
    return [
      {
        to: "/workflows/matrix-profile",
        icon: IconTimeline,
        title: t("nav.matrixProfile", "Matrix Profile"),
        description: t(
          "nav.megaMenu.matrixProfile",
          "Detect anomalies in time series",
        ),
      },
      {
        to: "/workflows/synthetic-load",
        icon: IconBolt,
        title: t("nav.syntheticLoad", "Synthetic Load Generation"),
        description: t(
          "nav.megaMenu.syntheticLoad",
          "Generate synthetic load profiles",
        ),
      },
      ...platformApplications.map((application) => ({
        to: application.url,
        icon: application.icon,
        iconColor: application.iconColor,
        title: t(application.titleKey, application.defaultTitle),
        description: t(application.descKey, application.defaultDesc),
        external: true,
      })),
    ];
  }, [t]);

  return (
    <Box>
      <Header height={60} px="md">
        <Group position="apart" sx={{ height: "100%" }}>
          <Box style={{ height: "55%" }}>
            <Link to="/">
              <img
                src="/images/moderate-logo-wide.png"
                style={{ height: "100%" }}
                alt="MODERATE logo"
              />
            </Link>
          </Box>

          <Group
            sx={{ height: "100%" }}
            spacing={0}
            className={classes.hiddenMobile}
          >
            {isAuthenticated === true && (
              <>
                <MainNavLinks t={t} />

                <HoverCard
                  width={780}
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

                    <MegaMenuItems items={mainMenuItems} />

                    <Group position="apart" px="md" mt="md">
                      <Text weight={500}>
                        {t("nav.platformApplications", "Example Applications")}
                      </Text>
                    </Group>

                    <Divider
                      my="sm"
                      mx="-md"
                      color={theme.colorScheme === "dark" ? "dark.5" : "gray.1"}
                    />

                    <MegaMenuItems items={applicationMenuItems} />
                  </HoverCard.Dropdown>
                </HoverCard>
              </>
            )}
          </Group>

          <Group className={classes.hiddenMobile}>
            <AuthButtons
              isAuthenticated={isAuthenticated}
              identityName={identity?.name}
              onLogin={onLogin}
              onLogout={onLogout}
              onRegister={onRegister}
              t={t}
            />
          </Group>

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

          {isAuthenticated === true && (
            <>
              <MainNavLinks t={t} />
              <UnstyledButton className={classes.link} onClick={toggleLinks}>
                <Center inline>
                  <Box component="span" mr={5}>
                    {t("nav.platformFeatures", "Platform Features")}
                  </Box>
                  <IconChevronDown size={16} color={theme.fn.primaryColor()} />
                </Center>
              </UnstyledButton>

              <Collapse in={linksOpened}>
                <Box ml="sm">
                  <MegaMenuItems items={mainMenuItems} />
                  <Text weight={500} mt="md" px="md">
                    {t("nav.platformApplications", "Example Applications")}
                  </Text>
                  <Divider
                    my="sm"
                    color={theme.colorScheme === "dark" ? "dark.5" : "gray.1"}
                  />
                  <MegaMenuItems items={applicationMenuItems} />
                </Box>
              </Collapse>
            </>
          )}

          <Divider
            my="sm"
            color={theme.colorScheme === "dark" ? "dark.5" : "gray.1"}
          />

          <Group position="center" grow pb="xl" px="md">
            <AuthButtons
              isAuthenticated={isAuthenticated}
              identityName={identity?.name}
              onLogin={onLogin}
              onLogout={onLogout}
              onRegister={onRegister}
              t={t}
            />
          </Group>
        </ScrollArea>
      </Drawer>
    </Box>
  );
}
