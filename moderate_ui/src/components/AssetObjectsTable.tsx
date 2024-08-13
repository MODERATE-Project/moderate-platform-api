import {
  ActionIcon,
  Badge,
  Group,
  LoadingOverlay,
  Table,
  Tooltip,
} from "@mantine/core";
import { useTranslate } from "@refinedev/core";
import { IconEye, IconTrash } from "@tabler/icons-react";
import React, { useCallback, useState } from "react";
import { Link } from "react-router-dom";
import { deleteAssetObject } from "../api/assets";
import { AssetModel } from "../api/types";

export const AssetObjectsTable: React.FC<{
  asset: AssetModel;
  onDeleted?: () => void;
}> = ({ asset, onDeleted }) => {
  const t = useTranslate();
  const [isLoading, setIsLoading] = useState(false);

  const ths = (
    <tr>
      <th>{t("assetObject.table.name", "Name")}</th>
      <th>{t("assetObject.table.createdAt", "Upload date")}</th>
      <th>{t("assetObject.table.extension", "Format")}</th>
      <th>{t("assetObject.table.actions", "Actions")}</th>
    </tr>
  );

  const onDeleteClick = useCallback(
    async ({ objectId }: { objectId: number }) => {
      setIsLoading(true);

      try {
        await deleteAssetObject({ assetId: asset.data.id, objectId });
      } finally {
        setIsLoading(false);
      }
    },
    [asset.data.id]
  );

  return (
    <>
      <LoadingOverlay visible={isLoading} overlayBlur={2} />
      <Table>
        <thead>{ths}</thead>
        <tbody>
          {asset.getObjects().map((assetObject) => (
            <tr key={assetObject.data.id}>
              <td>{assetObject.humanName}</td>
              <td>{assetObject.createdAt.toLocaleString()}</td>
              <td>
                <Badge>{assetObject.parsedKey?.ext}</Badge>
              </td>
              <td>
                <Group spacing="xs">
                  <Tooltip
                    openDelay={500}
                    label={t(
                      "assetObject.table.tooltip.view",
                      "Go to details page"
                    )}
                  >
                    <ActionIcon
                      component={Link}
                      to={`/assets/${asset.data.id}/objects/show/${assetObject.data.id}`}
                      variant="light"
                      color="blue"
                    >
                      <IconEye size="1em" />
                    </ActionIcon>
                  </Tooltip>
                  <Tooltip
                    openDelay={500}
                    label={t("assetObject.table.tooltip.delete", "Delete file")}
                  >
                    <ActionIcon
                      variant="light"
                      color="red"
                      onClick={() => {
                        onDeleteClick({ objectId: assetObject.data.id }).then(
                          () => {
                            onDeleted && onDeleted();
                          }
                        );
                      }}
                    >
                      <IconTrash size="1em" />
                    </ActionIcon>
                  </Tooltip>
                </Group>
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
    </>
  );
};
