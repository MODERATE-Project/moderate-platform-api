import {
  Badge,
  Box,
  Card,
  Group,
  Stack,
  Text,
  Tooltip,
  useMantineTheme,
} from "@mantine/core";
import { IconBox, IconClock } from "@tabler/icons-react";
import React, { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { Asset, AssetModel, AssetObject, AssetObjectModel } from "../api/types";
import {
  ACCESS_LEVEL_COLORS,
  ACCESS_LEVEL_TOOLTIP_KEYS,
  ACCESS_LEVEL_TOOLTIPS,
} from "../utils/accessLevel";
import { routes } from "../utils/routes";

export const AssetObjectCard: React.FC<{
  asset: Asset;
  assetObject: AssetObject;
  maxHeight?: boolean;
}> = ({ asset, assetObject, maxHeight }) => {
  const { t } = useTranslation();
  const theme = useMantineTheme();

  const [assetModel, assetObjectModel] = useMemo(() => {
    const assetModel = new AssetModel(asset);
    // Direct instantiation of AssetObjectModel for the single object passed in
    // This avoids the lookup failure if asset.objects doesn't contain all objects
    const assetObjectModel = new AssetObjectModel(assetObject);

    return [assetModel, assetObjectModel];
  }, [asset, assetObject]);

  const accessLevelColor = ACCESS_LEVEL_COLORS[assetModel.data.access_level];
  const borderColor = theme.colors[accessLevelColor][6];

  return (
    <Card
      shadow="sm"
      p="lg"
      radius="md"
      withBorder
      h={maxHeight ? "100%" : undefined}
      component={Link}
      to={routes.assetObjectShow(asset.id, assetObject.id)}
      sx={{
        display: "flex",
        flexDirection: "column",
        transition: "transform 200ms ease, box-shadow 200ms ease",
        borderTop: `4px solid ${borderColor}`,
        "&:hover": {
          transform: "translateY(-4px)",
          boxShadow: theme.shadows.xl,
        },
        textDecoration: "none",
        color: "inherit",
      }}
    >
      <Group position="apart" align="flex-start" mb="xs" noWrap>
        <Stack spacing={4} style={{ flex: 1, minWidth: 0 }}>
          <Group spacing="xs" noWrap align="center">
            <Text
              weight={600}
              size="lg"
              truncate
              title={assetObjectModel.humanName}
              style={{ lineHeight: 1.2 }}
            >
              {assetObjectModel.humanName}
            </Text>
            {assetObjectModel.format && (
              <Badge color="gray" variant="outline" size="xs" radius="sm">
                {assetObjectModel.format.toUpperCase()}
              </Badge>
            )}
          </Group>
        </Stack>

        <Tooltip
          label={t(
            ACCESS_LEVEL_TOOLTIP_KEYS[assetModel.data.access_level],
            ACCESS_LEVEL_TOOLTIPS[assetModel.data.access_level],
          )}
          multiline
          withArrow
          withinPortal
        >
          <Badge color={accessLevelColor} variant="light" size="sm">
            {assetModel.data.access_level}
          </Badge>
        </Tooltip>
      </Group>

      <Text
        size="sm"
        color="dimmed"
        lineClamp={3}
        mb="md"
        sx={{ flex: 1 }}
        title={assetObjectModel.description}
      >
        {assetObjectModel.description ||
          t("common.noDescription", "No description available")}
      </Text>

      <Box
        sx={(theme) => ({
          borderTop: `1px solid ${
            theme.colorScheme === "dark"
              ? theme.colors.dark[4]
              : theme.colors.gray[2]
          }`,
          paddingTop: theme.spacing.sm,
          marginTop: "auto",
        })}
      >
        <Stack spacing={4}>
          <Group spacing="xs" noWrap>
            <IconBox size="0.9rem" style={{ opacity: 0.5 }} />
            <Text
              size="xs"
              color="dimmed"
              truncate
              title={assetModel.data.name}
            >
              {assetModel.data.name}
            </Text>
          </Group>
          <Group spacing="xs" noWrap>
            <IconClock size="0.9rem" style={{ opacity: 0.5 }} />
            <Text size="xs" color="dimmed">
              {assetObjectModel.createdAt.toLocaleDateString()}
            </Text>
          </Group>
        </Stack>
      </Box>
    </Card>
  );
};
