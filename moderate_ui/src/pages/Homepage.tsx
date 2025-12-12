import {
  Badge,
  Box,
  Button,
  Card,
  Container,
  createStyles,
  Group,
  SimpleGrid,
  Stack,
  Text,
  ThemeIcon,
  Title,
  Card as MantineCard,
} from "@mantine/core";
import { useIsAuthenticated } from "@refinedev/core";
import {
  IconBolt,
  IconDatabase,
  IconExternalLink,
  IconFileAnalytics,
  IconGraph,
  IconLock,
  IconTools,
} from "@tabler/icons-react";
import React from "react";
import { useTranslation } from "react-i18next";
import { usePing } from "../api/ping";

const useStyles = createStyles((theme) => ({
  wrapper: {
    paddingTop: theme.spacing.xl * 2,
    paddingBottom: theme.spacing.xl * 2,
    background:
      theme.colorScheme === "dark"
        ? theme.colors.dark[8]
        : theme.colors.gray[0],
    minHeight: "100vh",
  },
  logo: {
    display: "flex",
    justifyContent: "center",
    marginBottom: theme.spacing.xl,
  },
  sectionHeading: {
    textAlign: "center",
    marginBottom: theme.spacing.sm,
    fontWeight: 900,
    fontSize: 42,
    letterSpacing: -1,
    color: theme.colorScheme === "dark" ? theme.white : theme.colors.dark[9],
    [`@media (max-width: ${theme.breakpoints.sm}px)`]: {
      fontSize: 32,
    },
  },
  sectionSubtitle: {
    textAlign: "center",
    color:
      theme.colorScheme === "dark"
        ? theme.colors.dark[1]
        : theme.colors.gray[6],
    marginBottom: theme.spacing.xl * 2,
    fontSize: theme.fontSizes.lg,
    maxWidth: 700,
    marginLeft: "auto",
    marginRight: "auto",
    lineHeight: 1.6,
  },
  featureGrid: {
    marginBottom: theme.spacing.xl * 2,
  },
  card: {
    transition: "all 0.3s ease",
    cursor: "pointer",
    backgroundColor:
      theme.colorScheme === "dark" ? theme.colors.dark[6] : theme.white,
    border: `1px solid ${
      theme.colorScheme === "dark" ? theme.colors.dark[5] : theme.colors.gray[2]
    }`,
    height: "100%",
    display: "flex",
    flexDirection: "column",
    padding: theme.spacing.xl,
    "&:hover": {
      transform: "translateY(-5px)",
      boxShadow: theme.shadows.lg,
      borderColor: theme.colors.blue[6],
    },
  },
  cardHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: theme.spacing.md,
  },
  cardIcon: {
    width: 50,
    height: 50,
  },
  cardTitle: {
    fontWeight: 700,
    fontSize: theme.fontSizes.lg,
    marginBottom: theme.spacing.xs,
    color: theme.colorScheme === "dark" ? theme.white : theme.colors.dark[8],
  },
  cardDescription: {
    color:
      theme.colorScheme === "dark"
        ? theme.colors.dark[2]
        : theme.colors.gray[6],
    fontSize: theme.fontSizes.md,
    lineHeight: 1.6,
    flexGrow: 1,
  },
  cardFooter: {
    marginTop: theme.spacing.md,
    display: "flex",
    alignItems: "center",
    color: theme.colors.blue[6],
    fontWeight: 600,
    fontSize: theme.fontSizes.sm,
  },
  mainSiteButton: {
    display: "flex",
    justifyContent: "center",
  },
  overlay: {
    position: "absolute",
    top: 0,
    left: 0,
    width: "100%",
    height: "100%",
    background:
      theme.colorScheme === "dark"
        ? "rgba(0, 0, 0, 0.7)"
        : "rgba(255, 255, 255, 0.7)",
    backdropFilter: "blur(3px)",
    zIndex: 10,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  overlayCard: {
    maxWidth: 400,
    width: "100%",
    margin: theme.spacing.md,
    textAlign: "center",
  },
}));

const features = [
  {
    icon: IconDatabase,
    iconColor: "blue",
    titleKey: "home.feature.assets.title",
    defaultTitle: "Dataset Catalogue",
    descKey: "home.feature.assets.desc",
    defaultDesc:
      "Browse and manage building-related datasets. Upload and share your data to facilitate research and innovation.",
    link: "/catalogue",
    isExternal: false,
  },
  {
    icon: IconFileAnalytics,
    iconColor: "teal",
    titleKey: "home.feature.exploration.title",
    defaultTitle: "Data Exploration",
    descKey: "home.feature.exploration.desc",
    defaultDesc:
      "Visualize trends, filter datasets, and explore data with interactive tools.",
    link: "/workflows/exploratory",
    isExternal: false,
  },
  {
    icon: IconGraph,
    iconColor: "grape",
    titleKey: "home.feature.matrix.title",
    defaultTitle: "Matrix Profile",
    descKey: "home.feature.matrix.desc",
    defaultDesc:
      "Analyze time-series data with advanced algorithms. Detect anomalies, motifs, and patterns to optimize building performance.",
    link: "/workflows/matrix-profile",
    isExternal: false,
  },
  {
    icon: IconBolt,
    iconColor: "orange",
    titleKey: "home.feature.synthetic.title",
    defaultTitle: "Synthetic Load Generation",
    descKey: "home.feature.synthetic.desc",
    defaultDesc:
      "Generate synthetic load profiles for simulations and energy modeling.",
    link: "/workflows/synthetic-load",
    isExternal: false,
  },
  {
    icon: IconTools,
    iconColor: "violet",
    titleKey: "home.feature.catalogue.title",
    defaultTitle: "Tools & Services Catalogue",
    descKey: "home.feature.catalogue.desc",
    defaultDesc:
      "Discover the full MODERATE ecosystem. Access a curated list of experimental tools and services designed for energy professionals.",
    link: "https://moderate-project.github.io/moderate-docs/tools-and-services/",
    isExternal: true,
  },
];

export const Homepage: React.FC = () => {
  const { t } = useTranslation();
  const { classes } = useStyles();
  usePing();
  const { isLoading, data } = useIsAuthenticated();
  const isAuthenticated = data?.authenticated;

  return (
    <Box className={classes.wrapper}>
      <Container size="lg" style={{ position: "relative" }}>
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
            "The MODERATE platform is an ecosystem for building-related data, tools, and models. Connect with resources for your energy efficiency projects.",
          )}
        </Text>

        <SimpleGrid
          cols={3}
          spacing="xl"
          breakpoints={[
            { maxWidth: 1024, cols: 2 },
            { maxWidth: 768, cols: 1 },
          ]}
          className={classes.featureGrid}
        >
          {features.map((feature) => (
            <Card
              key={feature.titleKey}
              className={classes.card}
              component="a"
              href={feature.link}
              target={feature.isExternal ? "_blank" : undefined}
              rel={feature.isExternal ? "noopener noreferrer" : undefined}
              radius="lg"
            >
              <div className={classes.cardHeader}>
                <ThemeIcon
                  size={48}
                  radius="md"
                  variant="light"
                  color={feature.iconColor}
                  className={classes.cardIcon}
                >
                  <feature.icon size={28} stroke={1.5} />
                </ThemeIcon>
                {feature.isExternal && (
                  <Badge variant="outline" color="gray" size="sm">
                    External
                  </Badge>
                )}
              </div>

              <Text className={classes.cardTitle}>
                {t(feature.titleKey, feature.defaultTitle)}
              </Text>

              <Text className={classes.cardDescription}>
                {t(feature.descKey, feature.defaultDesc)}
              </Text>

              <Group className={classes.cardFooter} spacing={4}>
                <Text size="sm">
                  {feature.isExternal ? "Visit Resource" : "Get Started"}
                </Text>
                {feature.isExternal ? (
                  <IconExternalLink size={16} />
                ) : (
                  <IconExternalLink
                    size={16}
                    style={{ transform: "rotate(45deg)" }}
                  />
                )}
              </Group>
            </Card>
          ))}
        </SimpleGrid>

        <div className={classes.mainSiteButton}>
          <Button
            component="a"
            href="https://moderate-project.eu/"
            target="_blank"
            size="md"
            variant="outline"
            color="gray"
            radius="xl"
            rightIcon={<IconExternalLink size={16} />}
            styles={{ root: { borderWidth: 2 } }}
          >
            {t("home.catalogue", "Visit Project Website")}
          </Button>
        </div>

        {!isLoading && !isAuthenticated && (
          <div className={classes.overlay}>
            <MantineCard
              className={classes.overlayCard}
              shadow="xl"
              radius="lg"
            >
              <Stack align="center" spacing="md" p="md">
                <ThemeIcon
                  size={60}
                  radius="xl"
                  color="blue"
                  variant="light"
                  style={{ marginBottom: 8 }}
                >
                  <IconLock size={32} />
                </ThemeIcon>
                <Title order={3}>
                  {t("home.overlay.title", "Platform Access Restricted")}
                </Title>
                <Text color="dimmed" size="sm">
                  {t(
                    "home.overlay.desc",
                    "The MODERATE platform is currently in development phase and accessible to registered users only. Please log in to continue.",
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
