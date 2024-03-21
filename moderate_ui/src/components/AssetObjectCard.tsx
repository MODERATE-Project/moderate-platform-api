import { Badge, Card, Group, Text, createStyles } from "@mantine/core";
import { DateTime } from "luxon";
import React, { useMemo } from "react";
import { Link } from "react-router-dom";

const useStyles = createStyles((theme) => ({
  card: {
    transition: "0.3s",
    "&:hover": {
      backgroundColor:
        theme.colorScheme === "dark"
          ? theme.colors.dark[4]
          : theme.colors.gray[1],
    },
  },
}));

const parseObjectName = (
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
  const { classes } = useStyles();

  const { name, extension } = useMemo(
    () => parseObjectName(assetObject.key),
    [assetObject]
  );

  return (
    <Card
      className={classes.card}
      component={Link}
      to={`/assets/${asset.id}/objects/show/${assetObject.id}`}
      withBorder
      p="sm"
      radius="md"
    >
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
    </Card>
  );
};
