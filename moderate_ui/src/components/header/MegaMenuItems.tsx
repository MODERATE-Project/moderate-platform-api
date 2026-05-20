import {
  Badge,
  Group,
  SimpleGrid,
  Text,
  ThemeIcon,
  UnstyledButton,
  createStyles,
} from "@mantine/core";
import { IconExternalLink } from "@tabler/icons-react";
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
  external?: boolean;
  iconColor?: string;
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
      {items.map((item) => {
        const body = (
          <Group noWrap align="flex-start">
            <ThemeIcon
              size={34}
              variant={item.iconColor ? "light" : "default"}
              radius="md"
              color={item.iconColor}
            >
              <item.icon
                size={22}
                color={item.iconColor ? undefined : theme.fn.primaryColor()}
              />
            </ThemeIcon>
            <div>
              <Group spacing={6} align="center">
                <Text size="sm" weight={500}>
                  {item.title}
                </Text>
                {item.external && (
                  <Badge
                    size="xs"
                    variant="light"
                    color="gray"
                    leftSection={<IconExternalLink size={10} />}
                  >
                    ext
                  </Badge>
                )}
              </Group>
              <Text size="xs" color="dimmed">
                {item.description}
              </Text>
            </div>
          </Group>
        );

        if (item.external) {
          return (
            <UnstyledButton
              component="a"
              href={item.to}
              target="_blank"
              rel="noopener noreferrer"
              className={classes.subLink}
              key={item.title}
            >
              {body}
            </UnstyledButton>
          );
        }

        return (
          <UnstyledButton
            component={Link}
            to={item.to}
            className={classes.subLink}
            key={item.title}
          >
            {body}
          </UnstyledButton>
        );
      })}
    </SimpleGrid>
  );
};
