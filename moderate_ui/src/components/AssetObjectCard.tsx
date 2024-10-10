import { Badge, Button, Card, Group, Stack, Text } from "@mantine/core";
import {
  IconBox,
  IconClock,
  IconExternalLink,
  IconLockAccess,
} from "@tabler/icons-react";
import React, { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { Asset, AssetModel, AssetObject } from "../api/types";

export const AssetObjectCard: React.FC<{
  asset: Asset;
  assetObject: AssetObject;
  maxHeight?: boolean;
}> = ({ asset, assetObject, maxHeight }) => {
  const { t } = useTranslation();

  const [assetModel, assetObjectModel] = useMemo(() => {
    const assetModel = new AssetModel(asset);
    const assetObjectModel = assetModel.getObject(assetObject.id);

    if (!assetObjectModel) {
      throw new Error("Asset object not found");
    }

    return [assetModel, assetObjectModel];
  }, [asset, assetObject.id]);

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
        value: <Badge color="gray">{assetModel.data.access_level}</Badge>,
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
      style={{ height: maxHeight ? "100%" : "inherit" }}
    >
      <Group position="apart" mb="xs">
        <Text weight={500} truncate>
          {assetObjectModel.humanName}
        </Text>
        {assetObjectModel.parsedKey?.ext && (
          <Badge color="pink" variant="light">
            {assetObjectModel.parsedKey.ext.toUpperCase()}
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
        to={`/assets/${asset.id}/objects/show/${assetObject.id}`}
      >
        {t("catalogue.card.view", "View details")}
      </Button>
      <Stack spacing="xs">
        {features.map((feature, idx) => (
          <Group spacing={0} position="left" key={idx}>
            <Text
              color="dimmed"
              size="sm"
              style={{ display: "flex", alignItems: "center" }}
              mr="xs"
            >
              <feature.icon size="1rem" style={{ marginRight: "0.25rem" }} />
              {feature.label}
            </Text>
            <Text size="sm" truncate>
              {feature.value}
            </Text>
          </Group>
        ))}
      </Stack>
    </Card>
  );
};
