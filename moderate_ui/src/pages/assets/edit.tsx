import { Select, Textarea, TextInput } from "@mantine/core";
import { useTranslate } from "@refinedev/core";
import { Edit, useForm } from "@refinedev/mantine";
import { useEffect, useMemo } from "react";
import { Asset, AssetAccessLevel, AssetModel } from "../../api/types";

export const AssetEdit = () => {
  const t = useTranslate();

  const {
    getInputProps,
    saveButtonProps,
    refineCore: { query },
  } = useForm({
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

  const assetModel = useMemo(() => {
    const assetData = query?.data?.data;

    if (!assetData) {
      return [undefined, undefined];
    }

    const assetModel = new AssetModel(assetData as Asset);
    return assetModel;
  }, [query]);

  useEffect(() => {
    console.log(assetModel);
  }, [assetModel]);

  return (
    <Edit saveButtonProps={saveButtonProps}>
      <TextInput
        mt="sm"
        description={t(
          "asset.fields.nameDescription",
          "A descriptive name for this asset"
        )}
        label={t("asset.fields.name", "Asset name")}
        {...getInputProps("name")}
      />
      <Textarea
        mt="sm"
        description={t(
          "asset.fields.descriptionDescription",
          "A longer description of what this asset is and what it contains"
        )}
        label={t("asset.fields.description", "Description")}
        {...getInputProps("description")}
      />
      <Select
        mt="sm"
        label={t("asset.fields.accessLevel", "Access level")}
        description={t(
          "asset.fields.accessLevelDescription",
          "Public assets are downloadable by anyone, private assets only by you, and visible assets are searchable but not downloadable by others"
        )}
        data={Object.values(AssetAccessLevel).map((val) => ({
          value: val,
          label: val.charAt(0).toUpperCase() + val.slice(1).toLowerCase(),
        }))}
        {...getInputProps("access_level")}
      />
    </Edit>
  );
};
