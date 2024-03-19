import { Badge, Button, Card, Group, Text } from "@mantine/core";
import { useTranslate } from "@refinedev/core";
import { IconEye } from "@tabler/icons";
import { DateTime } from "luxon";
import React, { useMemo } from "react";
import { Link } from "react-router-dom";

export const parseObjectName = (
  name: string
): { name: string; extension?: string } => {
  const parts = name.split("/");
  const lastPart = parts[parts.length - 1];
  const partsExtension = lastPart.split(".");

  return {
    name: partsExtension[0],
    extension: partsExtension.length > 1 ? partsExtension[1] : undefined,
  };
};

export const AssetObjectCard: React.FC<{
  asset: { [key: string]: any };
  assetObject: { [key: string]: any };
}> = ({ assetObject, asset }) => {
  const translate = useTranslate();

  const { name, extension } = useMemo(
    () => parseObjectName(assetObject.key),
    [assetObject]
  );

  return (
    <Card withBorder p="sm" radius="md">
      <Card.Section withBorder inheritPadding py="sm">
        <Group mb="sm">
          <Badge color="gray">
            {DateTime.fromISO(assetObject.created_at).toLocaleString(
              DateTime.DATETIME_FULL
            )}
          </Badge>
          <Badge color="cyan">{extension}</Badge>
        </Group>
        <Text>{name}</Text>
      </Card.Section>

      <Card.Section withBorder inheritPadding py="sm">
        <Group position="left">
          <Button
            component={Link}
            to={`/assets/${asset.id}/objects/show/${assetObject.id}`}
            leftIcon={<IconEye size="1em" />}
            variant="light"
            size="xs"
          >
            {translate("asset.objects.show")}
          </Button>
        </Group>
      </Card.Section>
    </Card>
  );
};
