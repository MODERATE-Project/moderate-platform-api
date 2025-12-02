import { Select, Stack, Text, Textarea, TextInput } from "@mantine/core";
import { useTranslate } from "@refinedev/core";
import { Edit, useForm } from "@refinedev/mantine";
import { AssetAccessLevel } from "../../api/types";

export const AssetEdit = () => {
  const t = useTranslate();

  const { getInputProps, saveButtonProps } = useForm({
    initialValues: {
      uuid: "",
      name: "",
      description: "",
      created_at: "",
      id: "",
      access_level: "",
      username: "",
    },
  });

  return (
    <Edit saveButtonProps={saveButtonProps}>
      <TextInput
        mt="sm"
        description={t(
          "asset.fields.nameDescription",
          "A descriptive name for this asset",
        )}
        label={t("asset.fields.name", "Asset name")}
        {...getInputProps("name")}
      />
      <Textarea
        mt="sm"
        description={t(
          "asset.fields.descriptionDescription",
          "A longer description of what this asset is and what it contains",
        )}
        label={t("asset.fields.description", "Description")}
        {...getInputProps("description")}
      />
      <Select
        mt="sm"
        label={t("asset.fields.accessLevel", "Access level")}
        description={
          <Stack spacing={2}>
            <Text size="xs" color="dimmed">
              {t(
                "asset.fields.accessLevelPublic",
                "Public: Visible and downloadable by everyone",
              )}
            </Text>
            <Text size="xs" color="dimmed">
              {t(
                "asset.fields.accessLevelVisible",
                "Visible: Searchable by everyone, but only downloadable by you",
              )}
            </Text>
            <Text size="xs" color="dimmed">
              {t(
                "asset.fields.accessLevelPrivate",
                "Private: Only visible and downloadable by you",
              )}
            </Text>
          </Stack>
        }
        data={Object.values(AssetAccessLevel).map((val) => ({
          value: val,
          label: val.charAt(0).toUpperCase() + val.slice(1).toLowerCase(),
        }))}
        {...getInputProps("access_level")}
      />
    </Edit>
  );
};
