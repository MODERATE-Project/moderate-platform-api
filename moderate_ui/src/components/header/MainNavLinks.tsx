import { createStyles } from "@mantine/core";
import { IconExternalLink } from "@tabler/icons-react";
import React from "react";
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
}));

interface MainNavLinksProps {
  t: (key: string, defaultValue: string) => string;
}

/**
 * Main navigation links component
 * Displays catalogue and tools/services links
 */
export const MainNavLinks: React.FC<MainNavLinksProps> = ({ t }) => {
  const { classes } = useStyles();

  return (
    <>
      <Link className={classes.link} to="/catalogue">
        {t("nav.catalogue", "Catalogue")}
      </Link>
      <Link
        className={classes.link}
        to="https://moderate-project.github.io/moderate-docs/tools-and-services/"
        target="_blank"
      >
        <IconExternalLink size={16} /> &nbsp;
        {t("nav.tools", "Tools & Services")}
      </Link>
    </>
  );
};
