import {
  Box,
  Button,
  Card,
  Container,
  createStyles,
  Card as MantineCard,
  SimpleGrid,
  Stack,
  Text,
  ThemeIcon,
  Title,
} from "@mantine/core";
import { useIsAuthenticated } from "@refinedev/core";
import {
  IconBolt,
  IconBox,
  IconExternalLink,
  IconFileSearch,
  IconFlask,
  IconLock,
  IconTimeline,
} from "@tabler/icons-react";
import React from "react";
import { useTranslation } from "react-i18next";
import { usePing } from "../api/ping";

const useStyles = createStyles((theme) => ({
  logo: {
    display: "flex",
    justifyContent: "center",
    marginBottom: theme.spacing.xl,
  },
  sectionHeading: {
    textAlign: "center",
    marginBottom: theme.spacing.xs,
    fontWeight: 800,
    letterSpacing: -1,
  },
  sectionSubtitle: {
    textAlign: "center",
    color: theme.colors.gray[7],
    marginBottom: theme.spacing.xl,
    fontSize: theme.fontSizes.lg,
  },
  featureGrid: {
    marginTop: theme.spacing.xl,
    marginBottom: theme.spacing.xl * 1.5,
  },
  card: {
    transition: "transform 120ms ease, box-shadow 120ms ease",
    cursor: "pointer",
    boxShadow: theme.shadows.sm,
    borderRadius: theme.radius.lg,
    "&:hover": {
      transform: "translateY(-6px) scale(1.03)",
      boxShadow: theme.shadows.xl,
    },
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    textAlign: "center",
    padding: theme.spacing.lg,
    background:
      theme.colorScheme === "dark" ? theme.colors.dark[6] : theme.white,
    [`@media (min-width: ${theme.breakpoints.lg}px)`]: {
      minHeight: 260,
    },
  },
  cardIcon: {
    marginBottom: theme.spacing.md,
  },
  cardTitle: {
    fontWeight: 700,
    fontSize: theme.fontSizes.xl,
    marginBottom: theme.spacing.xs,
    marginTop: 0,
  },
  cardDescription: {
    color:
      theme.colorScheme === "dark"
        ? theme.colors.dark[1]
        : theme.colors.gray[7],
    fontSize: theme.fontSizes.md,
    lineHeight: 1.6,
    marginBottom: 0,
  },
  mainSiteButton: {
    marginTop: theme.spacing.xl * 1.5,
    display: "flex",
    justifyContent: "center",
  },
  overlay: {
    position: "absolute",
    top: 0,
    left: 0,
    width: "100%",
    height: "100%",
    background: "rgba(255,255,255,0.5)",
    zIndex: 10,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "column",
    textAlign: "center",
    color: theme.colors.dark[7],
    textShadow: "0 1px 6px rgba(0,0,0,0.10)",
  },
  overlayCard: {
    background:
      theme.colorScheme === "dark"
        ? theme.colors.dark[5]
        : theme.colors.gray[0],
    borderRadius: theme.radius.lg,
    boxShadow: theme.shadows.lg,
    border: `1.5px solid ${
      theme.colorScheme === "dark" ? theme.colors.dark[4] : theme.colors.gray[3]
    }`,
    minWidth: 320,
    maxWidth: 400,
    margin: theme.spacing.md,
    color: theme.colors.dark[7],
  },
}));

const features = [
  {
    icon: IconBox,
    iconColor: "blue",
    titleKey: "home.feature.assets.title",
    defaultTitle: "Datasets (Assets)",
    descKey: "home.feature.assets.desc",
    defaultDesc:
      "Browse, upload, and manage building-related datasets. Share and discover valuable data for research and innovation.",
    link: "/assets",
  },
  {
    icon: IconFileSearch,
    iconColor: "teal",
    titleKey: "home.feature.exploration.title",
    defaultTitle: "Data Exploration",
    descKey: "home.feature.exploration.desc",
    defaultDesc:
      "Explore, filter, and visualize datasets to uncover insights and trends in building data.",
    link: "/workflows/exploratory",
  },
  {
    icon: IconTimeline,
    iconColor: "grape",
    titleKey: "home.feature.matrix.title",
    defaultTitle: "Matrix Profile",
    descKey: "home.feature.matrix.desc",
    defaultDesc:
      "Detect anomalies and patterns in time series data for building performance and monitoring.",
    link: "/workflows/matrix-profile",
  },
  {
    icon: IconBolt,
    iconColor: "orange",
    titleKey: "home.feature.synthetic.title",
    defaultTitle: "Synthetic Load Generation",
    descKey: "home.feature.synthetic.desc",
    defaultDesc:
      "Generate synthetic load profiles for simulation, testing, and energy modeling.",
    link: "/workflows/synthetic-load",
  },
  {
    icon: IconFlask,
    iconColor: "violet",
    titleKey: "home.feature.catalogue.title",
    defaultTitle: "Tools & Services Catalogue",
    descKey: "home.feature.catalogue.desc",
    defaultDesc:
      "Explore experimental tools and services in the MODERATE ecosystem.",
    link: "https://moderate-project.github.io/moderate-docs/tools-and-services/",
  },
];

export const Homepage: React.FC = () => {
  const { t } = useTranslation();
  const { classes } = useStyles();
  usePing();
  const { isLoading, data } = useIsAuthenticated();
  const isAuthenticated = data?.authenticated;

  return (
    <Box style={{ position: "relative" }} pt="lg" pb="lg">
      <Container size="md">
        <div className={classes.logo}>
          <img
            src="/images/moderate-logo-collapsed.png"
            style={{ maxHeight: "100px" }}
            alt="MODERATE logo"
          />
        </div>
        <Title order={1} className={classes.sectionHeading}>
          MODERATE Platform
        </Title>
        <Text className={classes.sectionSubtitle}>
          {t(
            "home.goal",
            "The MODERATE platform is an ecosystem for datasets, tools, and models related to buildings."
          )}
        </Text>
        <SimpleGrid
          cols={3}
          spacing="xl"
          breakpoints={[
            { maxWidth: 1200, cols: 2 },
            { maxWidth: 800, cols: 1 },
          ]}
          className={classes.featureGrid}
        >
          {features.map((feature) => (
            <Card
              key={feature.titleKey}
              className={classes.card}
              component="a"
              href={feature.link}
              target={feature.link.startsWith("http") ? "_blank" : undefined}
              rel={
                feature.link.startsWith("http")
                  ? "noopener noreferrer"
                  : undefined
              }
              withBorder
              shadow="md"
            >
              <ThemeIcon
                size={56}
                radius="xl"
                variant="light"
                color={feature.iconColor}
                className={classes.cardIcon}
              >
                <feature.icon size={32} />
              </ThemeIcon>
              <Text className={classes.cardTitle}>
                {t(feature.titleKey, feature.defaultTitle)}
              </Text>
              <Text className={classes.cardDescription}>
                {t(feature.descKey, feature.defaultDesc)}
              </Text>
            </Card>
          ))}
        </SimpleGrid>
        <div className={classes.mainSiteButton}>
          <Button
            component="a"
            href="https://moderate-project.eu/"
            target="_blank"
            size="lg"
            variant="default"
            leftIcon={<IconExternalLink />}
          >
            {t("home.catalogue", "Visit our main site for more information")}
          </Button>
        </div>
        {!isLoading && !isAuthenticated && (
          <div className={classes.overlay}>
            <MantineCard className={classes.overlayCard} shadow="lg" withBorder>
              <Stack align="center" spacing="md" p="lg">
                <ThemeIcon size={48} radius="xl" color="blue" variant="light">
                  <IconLock size={28} />
                </ThemeIcon>
                <Title order={3}>
                  {t(
                    "home.overlay.title",
                    "Please log in to access the platform"
                  )}
                </Title>
                <Text color="dimmed">
                  {t(
                    "home.overlay.desc",
                    "During the development phase, the MODERATE platform is only accessible to registered users"
                  )}
                </Text>
              </Stack>
            </MantineCard>
          </div>
        )}
      </Container>
    </Box>
  );
};
