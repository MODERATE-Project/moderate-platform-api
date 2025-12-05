import {
  Alert,
  Box,
  Button,
  Center,
  Group,
  LoadingOverlay,
  Paper,
  Stack,
  Text,
  ThemeIcon,
  TypographyStylesProvider,
} from "@mantine/core";
import { useTranslate } from "@refinedev/core";
import {
  IconDeviceFloppy,
  IconInfoCircle,
  IconMessageQuestion,
  IconPencil,
  IconX,
} from "@tabler/icons-react";
import { EditorOptions } from "@tiptap/react";
import DOMPurify from "dompurify";
import React, { useCallback, useState } from "react";
import { AssetObjectModel } from "../../api/types";
import { RichEditor } from "../RichEditor";

interface AssetObjectDescriptionTabProps {
  assetObjectModel: AssetObjectModel;
  isOwner: boolean;
  onSave: (description: string) => Promise<void>;
}

export const AssetObjectDescriptionTab: React.FC<
  AssetObjectDescriptionTabProps
> = ({ assetObjectModel, isOwner, onSave }) => {
  const t = useTranslate();
  const [isEditing, setIsEditing] = useState(false);
  const [editableDescription, setEditableDescription] = useState<
    string | undefined
  >(undefined);
  const [isLoadingDescription, setIsLoadingDescription] = useState(false);

  const onDescriptionUpdate: EditorOptions["onUpdate"] = useCallback(
    ({ editor }) => {
      setEditableDescription(editor.getHTML());
    },
    [],
  );

  const handleDescriptionSave = useCallback(() => {
    if (editableDescription === undefined) {
      return;
    }

    setIsLoadingDescription(true);
    onSave(editableDescription).finally(() => {
      setIsLoadingDescription(false);
      setIsEditing(false);
    });
  }, [editableDescription, onSave]);

  const handleCancel = useCallback(() => {
    setIsEditing(false);
    setEditableDescription(undefined);
  }, []);

  // Owner View - Edit Mode
  if (isOwner && isEditing) {
    const hasChanges =
      editableDescription !== undefined &&
      editableDescription !== assetObjectModel.description;

    return (
      <Stack spacing="md" pos="relative">
        <LoadingOverlay visible={isLoadingDescription} overlayBlur={2} />

        <Alert
          icon={<IconInfoCircle size="1rem" />}
          color="blue"
          variant="light"
        >
          <Group position="apart" align="center">
            <Text size="sm">
              {t(
                "assetObjects.description.editingMode",
                "You are currently editing the description.",
              )}
            </Text>
            <Group spacing="xs">
              <Button
                size="xs"
                variant="default"
                leftIcon={<IconX size="1rem" />}
                onClick={handleCancel}
                disabled={isLoadingDescription}
              >
                {t("common.cancel", "Cancel")}
              </Button>
              <Button
                size="xs"
                variant="filled"
                color="blue"
                leftIcon={<IconDeviceFloppy size="1rem" />}
                onClick={handleDescriptionSave}
                disabled={isLoadingDescription || !hasChanges}
              >
                {t("assetObjects.actions.descriptionSave", "Save Changes")}
              </Button>
            </Group>
          </Group>
        </Alert>

        <Box
          sx={(theme) => ({
            border: `1px solid ${theme.colors.gray[4]}`,
            borderRadius: theme.radius.sm,
            "& .mantine-RichTextEditor-root": {
              border: "none",
            },
          })}
        >
          <RichEditor
            content={assetObjectModel.description}
            onUpdate={onDescriptionUpdate}
          />
        </Box>
      </Stack>
    );
  }

  // Read-Only View (Owner & Non-Owner)
  if (assetObjectModel.description) {
    return (
      <Stack spacing="sm">
        {isOwner && (
          <Group position="right">
            <Button
              variant="light"
              size="xs"
              leftIcon={<IconPencil size="1rem" />}
              onClick={() => setIsEditing(true)}
            >
              {t("assetObjects.actions.editDescription", "Edit Description")}
            </Button>
          </Group>
        )}
        <Paper p="xl" radius="md" bg="gray.0">
          <TypographyStylesProvider>
            <div
              dangerouslySetInnerHTML={{
                __html: DOMPurify.sanitize(assetObjectModel.description),
              }}
            />
          </TypographyStylesProvider>
        </Paper>
      </Stack>
    );
  }

  // Empty State
  return (
    <Center py="xl">
      <Stack align="center" spacing="sm">
        <ThemeIcon size={64} radius="xl" variant="light" color="gray">
          <IconMessageQuestion size={40} />
        </ThemeIcon>
        <Text size="lg" weight={500} color="dimmed">
          {t("assetObjects.descriptionEmptyTitle", "No description provided")}
        </Text>
        <Text size="sm" color="dimmed" align="center" maw={400}>
          {t(
            "assetObjects.descriptionEmptyMessage",
            "The owner of this dataset has not provided a description yet.",
          )}
        </Text>
        {isOwner && (
          <Button
            mt="md"
            variant="light"
            leftIcon={<IconPencil size="1rem" />}
            onClick={() => setIsEditing(true)}
          >
            {t("assetObjects.actions.addDescription", "Add Description")}
          </Button>
        )}
      </Stack>
    </Center>
  );
};
