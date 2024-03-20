import { Box, Button, Text, Title, createStyles } from "@mantine/core";
import { IconExternalLink } from "@tabler/icons";
import React from "react";
import { useTranslation } from "react-i18next";

const useStyles = createStyles((theme) => ({
  wrapper: {
    position: "relative",
    paddingTop: 120,
    paddingBottom: 80,

    "@media (max-width: 755px)": {
      paddingTop: 80,
      paddingBottom: 60,
    },
  },

  inner: {
    position: "relative",
    zIndex: 1,
  },

  dots: {
    position: "absolute",
    color:
      theme.colorScheme === "dark"
        ? theme.colors.dark[5]
        : theme.colors.gray[1],

    "@media (max-width: 755px)": {
      display: "none",
    },
  },

  dotsLeft: {
    left: 0,
    top: 0,
  },

  title: {
    textAlign: "center",
    fontWeight: 800,
    fontSize: 40,
    letterSpacing: -1,
    color: theme.colorScheme === "dark" ? theme.white : theme.black,
    marginBottom: theme.spacing.xs,
    fontFamily: `Greycliff CF, ${theme.fontFamily}`,

    "@media (max-width: 520px)": {
      fontSize: 28,
    },
  },

  highlight: {
    color:
      theme.colors[theme.primaryColor][theme.colorScheme === "dark" ? 4 : 6],
  },

  description: {
    textAlign: "center",

    "@media (max-width: 520px)": {
      fontSize: theme.fontSizes.md,
    },
  },

  controls: {
    marginTop: theme.spacing.lg,
    display: "flex",
    justifyContent: "center",

    "@media (max-width: 520px)": {
      flexDirection: "column",
    },
  },

  control: {
    "&:not(:first-of-type)": {
      marginLeft: theme.spacing.md,
    },

    "@media (max-width: 520px)": {
      height: 42,
      fontSize: theme.fontSizes.md,

      "&:not(:first-of-type)": {
        marginTop: theme.spacing.md,
        marginLeft: 0,
      },
    },
  },
}));

export const Homepage: React.FC = () => {
  const { t } = useTranslation();
  const { classes } = useStyles();

  return (
    <>
      <Box mt="5rem">
        <div className={classes.inner}>
          <Title className={classes.title}>
            <Box mb="md">
              <img
                src="/images/moderate-logo-collapsed.png"
                style={{ maxHeight: "100px" }}
              />
            </Box>
            <Text component="span" className={classes.highlight} inherit>
              MODERATE
            </Text>{" "}
            Platform
          </Title>

          <Text size="lg" color="dimmed" className={classes.description}>
            {t(
              "home.goal",
              "The MODERATE platform aims to be an ecosystem for datasets, tools, and models related to buildings"
            )}
          </Text>

          <div className={classes.controls}>
            <Button
              component="a"
              href="https://moderate-project.eu/"
              target="_blank"
              className={classes.control}
              size="lg"
              variant="default"
              leftIcon={<IconExternalLink />}
            >
              {t("home.catalogue", "Visit our main site for more information")}
            </Button>
          </div>
        </div>
      </Box>
    </>
  );
};
