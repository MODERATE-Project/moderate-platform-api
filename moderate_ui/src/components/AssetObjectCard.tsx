import {
  Badge,
  Box,
  Button,
  Card,
  Group,
  Stack,
  Text,
  Tooltip,
} from "@mantine/core";
import {
  IconBox,
  IconClock,
  IconExternalLink,
  IconLockAccess,
} from "@tabler/icons-react";
import React, { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import {
  Asset,
  AssetAccessLevel,
  AssetModel,
  AssetObject,
  AssetObjectModel,
} from "../api/types";
import { routes } from "../utils/routes";

export const AssetObjectCard: React.FC<{
  asset: Asset;
  assetObject: AssetObject;
  maxHeight?: boolean;
}> = ({ asset, assetObject, maxHeight }) => {
  const { t } = useTranslation();

  const [assetModel, assetObjectModel] = useMemo(() => {
    const assetModel = new AssetModel(asset);
    // Direct instantiation of AssetObjectModel for the single object passed in
    // This avoids the lookup failure if asset.objects doesn't contain all objects
    const assetObjectModel = new AssetObjectModel(assetObject);

    return [assetModel, assetObjectModel];
  }, [asset, assetObject]);

  const features = useMemo(() => {
    return [
      {
        label: t("catalogue.card.asset", "Asset"),
        value: assetModel.data.name,
        icon: IconBox,
      },
      {
        label: t("catalogue.card.createdAt", "Uploaded"),
        value: assetObjectModel.createdAt.toLocaleString(),
        icon: IconClock,
      },
      {
        label: t("catalogue.card.accessLevel", "Access level"),
        value: (
          <Tooltip
            label={
              assetModel.data.access_level === AssetAccessLevel.PUBLIC
                ? t(
                    "asset.fields.accessLevelPublic",
                    "Public: Visible and downloadable by everyone",
                  )
                : assetModel.data.access_level === AssetAccessLevel.VISIBLE
                  ? t(
                      "asset.fields.accessLevelVisible",
                      "Visible: Searchable by everyone, but only downloadable by you",
                    )
                  : t(
                      "asset.fields.accessLevelPrivate",
                      "Private: Only visible and downloadable by you",
                    )
            }
            multiline
            withArrow
          >
            <Box sx={{ cursor: "help", display: "inline-block" }}>
              <Badge color="gray">{assetModel.data.access_level}</Badge>
            </Box>
          </Tooltip>
        ),
        icon: IconLockAccess,
      },
    ];
  }, [t, assetModel, assetObjectModel]);

  return (
    <Card
      shadow="sm"
      p="lg"
      radius="md"
      withBorder
      h={maxHeight ? "100%" : undefined}
    >
      <Group position="apart" mb="xs">
        <Text weight={500} truncate>
          {assetObjectModel.humanName}
        </Text>
        {assetObjectModel.format && (
          <Badge color="pink" variant="light">
            {assetObjectModel.format.toUpperCase()}
          </Badge>
        )}
      </Group>
      <Button
        variant="light"
        leftIcon={<IconExternalLink size="1em" />}
        fullWidth
        mt="md"
        mb="md"
        radius="md"
        target="_blank"
        component={Link}
        to={routes.assetObjectShow(asset.id, assetObject.id)}
      >
        {t("catalogue.card.view", "View details")}
      </Button>
      <Stack spacing="xs">
        {features.map((feature, idx) => (
          <Group spacing={0} position="left" key={idx}>
            <Group spacing="xs" noWrap>
              <feature.icon size="1rem" />
              <Text color="dimmed" size="sm">
                {feature.label}
              </Text>
            </Group>
            <Text size="sm" truncate>
              {feature.value}
            </Text>
          </Group>
        ))}
      </Stack>
    </Card>
  );
};
