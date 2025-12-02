import {
  Alert,
  Box,
  Button,
  Group,
  LoadingOverlay,
  Text,
  Title,
} from "@mantine/core";
import { useTranslate } from "@refinedev/core";
import {
  IconDeviceFloppy,
  IconEyeEdit,
  IconMessageQuestion,
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
    if (!editableDescription) {
      return;
    }

    setIsLoadingDescription(true);
    onSave(editableDescription).finally(() => {
      setIsLoadingDescription(false);
    });
  }, [editableDescription, onSave]);

  if (isOwner) {
    return (
      <Box style={{ position: "relative" }}>
        <LoadingOverlay visible={isLoadingDescription} overlayBlur={2} />
        <Group position="apart" mb="xs">
          <Text fz="sm" color="dimmed">
            <IconEyeEdit size="1em" />{" "}
            {t(
              "assetObjects.description.editableReason",
              "You can edit this description because you are either the dataset owner or a platform administrator",
            )}
          </Text>
          <Button
            compact
            variant="subtle"
            leftIcon={<IconDeviceFloppy size="1em" />}
            onClick={handleDescriptionSave}
            disabled={isLoadingDescription}
          >
            {t("assetObjects.actions.descriptionSave", "Save")}
          </Button>
        </Group>
        <RichEditor
          content={assetObjectModel.description}
          onUpdate={onDescriptionUpdate}
        />
      </Box>
    );
  }

  if (assetObjectModel.description) {
    return (
      <div
        dangerouslySetInnerHTML={{
          __html: DOMPurify.sanitize(assetObjectModel.description),
        }}
      />
    );
  }

  return (
    <Alert
      icon={<IconMessageQuestion size={32} />}
      title={
        <Title order={3}>
          {t("assetObjects.descriptionEmptyTitle", "No description")}
        </Title>
      }
      color="gray"
    >
      {t(
        "assetObjects.descriptionEmptyMessage",
        "The owner of this dataset has not provided a description yet.",
      )}
    </Alert>
  );
};
