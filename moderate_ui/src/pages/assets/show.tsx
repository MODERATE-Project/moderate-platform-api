import { Alert, Box, ThemeIcon, Title } from "@mantine/core";
import { useKeycloak } from "@react-keycloak/web";
import {
  IResourceComponentsProps,
  useGetIdentity,
  useShow,
  useTranslate,
} from "@refinedev/core";
import { Show } from "@refinedev/mantine";
import { IconExclamationCircle, IconFileUpload } from "@tabler/icons-react";
import React, { useCallback, useMemo } from "react";
import { Asset, AssetAccessLevel, AssetModel } from "../../api/types";
import {
  buildKeycloakAuthProvider,
  IIdentity,
} from "../../auth-provider/keycloak";
import { AssetObjectDropzone } from "../../components/AssetObjectDropzone";
import { AssetObjectsTable } from "../../components/AssetObjectsTable";
import { KeyValuesStack } from "../../components/KeyValuesStack";

export const AssetShow: React.FC<IResourceComponentsProps> = () => {
  const t = useTranslate();
  const { query } = useShow();
  const { data, isLoading, refetch } = query;

  const { data: identity } = useGetIdentity<IIdentity>();
  const { keycloak, initialized } = useKeycloak();

  const isAdmin = useMemo(() => {
    if (!initialized) {
      return false;
    }

    const authProvider = buildKeycloakAuthProvider({ keycloak });
    return authProvider.isAdmin();
  }, [initialized, keycloak]);

  const isOwner = useMemo(() => {
    return data?.data?.username === identity?.username || isAdmin;
  }, [identity, data, isAdmin]);

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

  const omitFields = useMemo(() => {
    const fields = ["objects", "id"];
    if (record?.access_level === AssetAccessLevel.PUBLIC && !isOwner) {
      fields.push("username");
    }
    return fields;
  }, [record, isOwner]);

  return (
    <Show
      isLoading={isLoading}
      contentProps={{ mb: "-sm", pt: "md" }}
      title={record && <Title order={3}>{record.name}</Title>}
      goBack={null}
    >
      {record && <KeyValuesStack obj={record} omitFields={omitFields} />}
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
        <AssetObjectsTable
          asset={asset}
          onDeleted={onRecordChanged}
          onRenamed={onRecordChanged}
        />
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
