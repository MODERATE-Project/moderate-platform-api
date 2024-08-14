import { Alert, Box, ThemeIcon, Title } from "@mantine/core";
import {
  IResourceComponentsProps,
  useShow,
  useTranslate,
} from "@refinedev/core";
import { Show } from "@refinedev/mantine";
import { IconExclamationCircle, IconFileUpload } from "@tabler/icons-react";
import React, { useCallback, useMemo } from "react";
import { Asset, AssetModel } from "../../api/types";
import { AssetObjectDropzone } from "../../components/AssetObjectDropzone";
import { AssetObjectsTable } from "../../components/AssetObjectsTable";
import { KeyValuesStack } from "../../components/KeyValuesStack";

export const AssetShow: React.FC<IResourceComponentsProps> = () => {
  const t = useTranslate();
  const { query } = useShow();
  const { data, isLoading, refetch } = query;

  const asset = useMemo(() => {
    const theRecord = data?.data;

    if (!theRecord) {
      return;
    }

    const asset = new AssetModel(theRecord as Asset);

    return asset;
  }, [data?.data]);

  const onRecordChanged = useCallback(() => {
    refetch();
  }, [refetch]);

  const record = data?.data;

  return (
    <Show
      isLoading={isLoading}
      contentProps={{ mb: "-sm", pt: "md" }}
      title={record && <Title order={3}>{record.name}</Title>}
      goBack={null}
    >
      {record && <KeyValuesStack obj={record} omitFields={["objects", "id"]} />}
      <Title order={5} my="md">
        <ThemeIcon size="md" variant="light" color="gray" mr="xs">
          <IconFileUpload size="1em" />
        </ThemeIcon>
        {t("asset.fields.objects", "Dataset files uploaded to this asset")}
      </Title>
      {asset && (
        <Box mb="md">
          <AssetObjectDropzone asset={asset} onUploaded={onRecordChanged} />
        </Box>
      )}
      {asset && asset?.getObjects().length > 0 ? (
        <AssetObjectsTable asset={asset} onDeleted={onRecordChanged} />
      ) : (
        <Alert
          p="xs"
          mb="sm"
          icon={<IconExclamationCircle size="1em" />}
          color="gray"
          variant="light"
        >
          {t("asset.noObjects", "No objects uploaded to this asset yet")}
        </Alert>
      )}
    </Show>
  );
};
