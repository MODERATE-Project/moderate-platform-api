import {
  FileInput,
  Loader,
  LoadingOverlay,
  Select,
  Stack,
  Text,
  TextInput,
  Textarea,
} from "@mantine/core";
import { isNotEmpty } from "@mantine/form";
import { useGo, useTranslate } from "@refinedev/core";
import { Create, useForm } from "@refinedev/mantine";
import { IconUpload } from "@tabler/icons-react";
import _ from "lodash";
import { useState } from "react";
import { AssetAccessLevel } from "../../api/types";
import { ResourceNames } from "../../types";
import { uploadMultipleFiles, UploadProgress } from "../../utils/upload";

export const AssetCreate = () => {
  const t = useTranslate();

  const [uploadingFile, setUploadingFile] = useState<
    UploadProgress | undefined
  >(undefined);

  const go = useGo();

  const {
    getInputProps,
    saveButtonProps,
    refineCore: { formLoading },
  } = useForm({
    initialValues: {
      name: "",
      description: "",
      access_level: AssetAccessLevel.PRIVATE,
      files: [],
    },
    validate: {
      name: isNotEmpty(),
      description: isNotEmpty(),
      access_level: isNotEmpty(),
      files: isNotEmpty(),
    },
    transformValues: (values) => {
      return values;
    },
    refineCoreProps: {
      redirect: false,
      onMutationSuccess: async (data, variables) => {
        const assetId = data.data.id;

        if (!assetId) {
          return;
        }

        await uploadMultipleFiles(
          String(assetId),
          variables.files as File[],
          (progress) => {
            setUploadingFile(progress);
          },
        );

        setUploadingFile(undefined);

        go({
          to: {
            resource: ResourceNames.ASSET,
            action: "show",
            id: assetId,
          },
        });
      },
    },
  });

  return (
    <>
      <LoadingOverlay
        visible={uploadingFile !== undefined}
        loader={
          <Stack justify="center" align="center">
            <Loader size="xl" />
            <Text color="dimmed">
              {t("asset.form.uploading", "Uploading")}{" "}
              <code>{uploadingFile?.fileName}</code>
            </Text>
            <Text fz="xl" fw={700}>
              {uploadingFile?.progress}%
            </Text>
          </Stack>
        }
      />
      <Create isLoading={formLoading} saveButtonProps={saveButtonProps}>
        <TextInput
          mt="sm"
          description={t(
            "asset.fields.nameDescription",
            "A descriptive name for this asset",
          )}
          label={t("asset.fields.name", "Asset name")}
          {...getInputProps("name")}
        />
        <Select
          mt="sm"
          description={t(
            "asset.fields.accessLevelDescription",
            "Public assets are downloadable by anyone, private assets only by you, and visible assets are searchable but not downloadable by others",
          )}
          label={t("asset.fields.accessLevel", "Access level")}
          {...getInputProps("access_level")}
          data={Object.values(AssetAccessLevel).map((val) => ({
            value: val,
            label: _.capitalize(val),
          }))}
        />
        <Textarea
          mt="sm"
          description={t(
            "asset.fields.descriptionDescription",
            "A longer description of what this asset is and what it contains",
          )}
          label={t("asset.fields.description", "Description")}
          {...getInputProps("description")}
          autosize
          minRows={3}
        />
        <FileInput
          mt="sm"
          description={t(
            "asset.fields.filesDescription",
            'These files will be attached to this asset as individual datasets or "asset objects"',
          )}
          label={t("asset.fields.files", "Attached files")}
          {...getInputProps("files")}
          icon={<IconUpload size={14} />}
          multiple
        />
      </Create>
    </>
  );
};
