import {
  Button,
  Group,
  TextInput,
  Title,
  Tooltip,
  createStyles,
} from "@mantine/core";
import { useTranslate } from "@refinedev/core";
import { IconCheck, IconX } from "@tabler/icons-react";
import React, { useState } from "react";

const useStyles = createStyles(() => ({
  editableTitle: {
    cursor: "pointer",
    "&:hover": {
      opacity: 0.4,
    },
  },
  titleInput: {
    width: "100%",
  },
}));

interface EditableTitleProps {
  title: string;
  onSave: (newTitle: string) => Promise<void>;
  isOwner: boolean;
}

/**
 * Editable title component with inline editing capabilities
 * Shows as regular title for non-owners, clickable with edit UI for owners
 */
export const EditableTitle: React.FC<EditableTitleProps> = ({
  title,
  onSave,
  isOwner,
}) => {
  const { classes } = useStyles();
  const [isEditing, setIsEditing] = useState(false);
  const [editedTitle, setEditedTitle] = useState(title);
  const [isSaving, setIsSaving] = useState(false);
  const t = useTranslate();

  const handleSave = async () => {
    if (editedTitle.trim() === title) {
      setIsEditing(false);
      return;
    }

    setIsSaving(true);

    try {
      await onSave(editedTitle.trim());
      setIsEditing(false);
    } catch (error) {
      setEditedTitle(title);
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    setEditedTitle(title);
    setIsEditing(false);
  };

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === "Enter") {
      handleSave();
    } else if (event.key === "Escape") {
      handleCancel();
    }
  };

  if (!isOwner) {
    return <Title>{title}</Title>;
  }

  if (isEditing) {
    return (
      <Group spacing="xs" align="center" noWrap>
        <TextInput
          value={editedTitle}
          onChange={(e) => setEditedTitle(e.target.value)}
          onKeyDown={handleKeyDown}
          autoFocus
          classNames={{ input: classes.titleInput }}
        />
        <Group spacing={4}>
          <Button
            compact
            variant="subtle"
            color="red"
            onClick={handleCancel}
            disabled={isSaving}
            leftIcon={<IconX size="0.8rem" />}
          >
            {t("common.cancel", "Cancel")}
          </Button>
          <Button
            compact
            variant="subtle"
            color="green"
            onClick={handleSave}
            loading={isSaving}
            leftIcon={<IconCheck size="0.8rem" />}
          >
            {t("common.save", "Save")}
          </Button>
        </Group>
      </Group>
    );
  }

  return (
    <Tooltip
      position="top-start"
      label={t("assetObjects.clickToEdit", "Click to edit name")}
    >
      <Title
        className={classes.editableTitle}
        onClick={() => setIsEditing(true)}
      >
        {title}
      </Title>
    </Tooltip>
  );
};
