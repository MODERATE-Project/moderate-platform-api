import {
  ActionIcon,
  Badge,
  Button,
  Code,
  Group,
  HoverCard,
  LoadingOverlay,
  Popover,
  Stack,
  Table,
  Text,
  TextInput,
  Tooltip,
} from "@mantine/core";
import { useTranslate } from "@refinedev/core";
import {
  IconCheck,
  IconEdit,
  IconEye,
  IconTrash,
  IconX,
} from "@tabler/icons-react";
import React, { useCallback, useState } from "react";
import { Link } from "react-router-dom";
import { deleteAssetObject, updateAssetObject } from "../api/assets";
import { AssetModel, AssetObjectModel } from "../api/types";
import { routes } from "../utils/routes";

const RenamePopover: React.FC<{
  assetObject: AssetObjectModel;
  assetId: number;
  onRenamed?: () => void;
}> = ({ assetObject, assetId, onRenamed }) => {
  const t = useTranslate();
  const [opened, setOpened] = useState(false);
  const [newName, setNewName] = useState(assetObject.data.name || "");
  const [isLoading, setIsLoading] = useState(false);

  const handleSave = async (): Promise<void> => {
    setIsLoading(true);
    try {
      await updateAssetObject({
        assetId,
        objectId: assetObject.data.id,
        updateBody: { name: newName || null },
      });
      setOpened(false);
      onRenamed?.();
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancel = (): void => {
    setNewName(assetObject.data.name || "");
    setOpened(false);
  };

  return (
    <Popover
      opened={opened}
      onChange={setOpened}
      width={300}
      position="bottom"
      withArrow
      shadow="md"
    >
      <Popover.Target>
        <Tooltip
          openDelay={500}
          label={t("assetObject.table.tooltip.rename", "Rename dataset")}
        >
          <ActionIcon
            variant="light"
            color="gray"
            onClick={() => setOpened((o) => !o)}
          >
            <IconEdit size="1em" />
          </ActionIcon>
        </Tooltip>
      </Popover.Target>
      <Popover.Dropdown>
        <Stack spacing="xs">
          <Text size="sm" weight={500}>
            {t("assetObject.rename.title", "Rename dataset")}
          </Text>
          <TextInput
            placeholder={assetObject.humanName}
            value={newName}
            onChange={(e) => setNewName(e.currentTarget.value)}
            size="sm"
            description={t(
              "assetObject.rename.description",
              "Leave empty to use the default name derived from the file",
            )}
          />
          <Group position="right" spacing="xs">
            <Button
              size="xs"
              variant="subtle"
              color="gray"
              onClick={handleCancel}
              leftIcon={<IconX size="0.9em" />}
            >
              {t("assetObject.rename.cancel", "Cancel")}
            </Button>
            <Button
              size="xs"
              onClick={handleSave}
              loading={isLoading}
              leftIcon={<IconCheck size="0.9em" />}
            >
              {t("assetObject.rename.save", "Save")}
            </Button>
          </Group>
        </Stack>
      </Popover.Dropdown>
    </Popover>
  );
};

export const AssetObjectsTable: React.FC<{
  asset: AssetModel;
  onDeleted?: () => void;
  onRenamed?: () => void;
}> = ({ asset, onDeleted, onRenamed }) => {
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
    [asset.data.id],
  );

  return (
    <>
      <LoadingOverlay visible={isLoading} overlayBlur={2} />
      <Table>
        <thead>{ths}</thead>
        <tbody>
          {asset
            .getObjects()
            .sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime())
            .map((assetObject) => (
              <tr key={assetObject.data.id}>
                <td>
                  <HoverCard width={280} shadow="md">
                    <HoverCard.Target>
                      <span>{assetObject.humanName}</span>
                    </HoverCard.Target>
                    <HoverCard.Dropdown>
                      <Text size="sm" color="dimmed">
                        {t("assetObject.table.key", "Dataset key")}
                      </Text>
                      <Code>{assetObject.data.key}</Code>
                    </HoverCard.Dropdown>
                  </HoverCard>
                </td>
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
                        "Go to details page",
                      )}
                    >
                      <ActionIcon
                        component={Link}
                        to={routes.assetObjectShow(
                          asset.data.id,
                          assetObject.data.id,
                        )}
                        variant="light"
                        color="blue"
                      >
                        <IconEye size="1em" />
                      </ActionIcon>
                    </Tooltip>
                    <RenamePopover
                      assetObject={assetObject}
                      assetId={asset.data.id}
                      onRenamed={onRenamed}
                    />
                    <Tooltip
                      openDelay={500}
                      label={t(
                        "assetObject.table.tooltip.delete",
                        "Delete file",
                      )}
                    >
                      <ActionIcon
                        variant="light"
                        color="red"
                        onClick={() => {
                          onDeleteClick({ objectId: assetObject.data.id }).then(
                            () => {
                              onDeleted && onDeleted();
                            },
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
