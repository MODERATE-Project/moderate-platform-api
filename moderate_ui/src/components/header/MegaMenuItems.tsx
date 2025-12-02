import {
  Group,
  SimpleGrid,
  Text,
  ThemeIcon,
  UnstyledButton,
  createStyles,
} from "@mantine/core";
import React from "react";
import { Link } from "react-router-dom";

const useStyles = createStyles((theme) => ({
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
}));

export interface MegaMenuItem {
  to: string;
  icon: React.ComponentType<{ size?: number | string; color?: string }>;
  title: string;
  description: string;
}

interface MegaMenuItemsProps {
  items: MegaMenuItem[];
}

/**
 * Mega menu items grid component
 * Displays a grid of clickable menu items with icons and descriptions
 */
export const MegaMenuItems: React.FC<MegaMenuItemsProps> = ({ items }) => {
  const { classes, theme } = useStyles();

  return (
    <SimpleGrid cols={2} spacing={0}>
      {items.map((item) => (
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
      ))}
    </SimpleGrid>
  );
};
