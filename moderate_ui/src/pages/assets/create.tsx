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
import { uploadObject } from "../../api/assets";
import { AssetAccessLevel } from "../../api/types";

export const AssetCreate = () => {
  const t = useTranslate();

  const [uploadingFile, setUploadingFile] = useState<
    { name: string; progress: number } | undefined
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
      console.debug("transformValues", values);
      return values;
    },
    refineCoreProps: {
      redirect: false,
      onMutationSuccess: async (data, variables) => {
        const assetId = data.data.id;

        if (!assetId) {
          return;
        }

        for (const file of variables.files as File[]) {
          setUploadingFile({ name: file.name, progress: 0 });

          await uploadObject({
            assetId,
            file,
            onProgress: (progress) => {
              setUploadingFile({ name: file.name, progress });
            },
          });

          setUploadingFile(undefined);
        }

        go({
          to: {
            resource: "asset",
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
              <code>{uploadingFile?.name}</code>
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
          label={t("asset.fields.name")}
          {...getInputProps("name")}
        />
        <Select
          mt="sm"
          label={t("asset.fields.access_level")}
          {...getInputProps("access_level")}
          data={Object.values(AssetAccessLevel).map((val) => ({
            value: val,
            label: _.capitalize(val),
          }))}
        />
        <Textarea
          mt="sm"
          label={t("asset.fields.description")}
          {...getInputProps("description")}
          autosize
          minRows={3}
        />
        <FileInput
          mt="sm"
          label={t("asset.fields.files")}
          {...getInputProps("files")}
          icon={<IconUpload size={14} />}
          multiple
        />
      </Create>
    </>
  );
};
