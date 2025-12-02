import {
  Button,
  Group,
  LoadingOverlay,
  Paper,
  Stack,
  Tabs,
  Text,
  Title,
} from "@mantine/core";
import { useKeycloak } from "@react-keycloak/web";
import {
  IResourceComponentsProps,
  useGetIdentity,
  useNotification,
  useParsed,
  useShow,
  useTranslate,
} from "@refinedev/core";
import {
  IconChartAreaLine,
  IconCheck,
  IconClipboard,
  IconDownload,
  IconFileCheck,
  IconFileText,
  IconReportSearch,
  IconTable,
} from "@tabler/icons-react";
import _ from "lodash";
import React, { useCallback, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { updateAssetObject } from "../../api/assets";
import { Asset, AssetModel } from "../../api/types";
import {
  buildKeycloakAuthProvider,
  IIdentity,
} from "../../auth-provider/keycloak";
import {
  AssetObjectDescriptionTab,
  AssetObjectMetadataTab,
  AssetObjectProfileTab,
  EditableTitle,
  IntegrityModal,
} from "../../components/asset-object";
import { LoadingOverlayWithMessage } from "../../components/LoadingOverlayWithMessage";
import {
  useAssetObjectDownload,
  useAssetObjectIntegrity,
  useAssetObjectProfile,
} from "../../hooks";
import { ResourceNames } from "../../types";
import { catchErrorAndShow } from "../../utils";
import { routes } from "../../utils/routes";

export const AssetObjectShow: React.FC<IResourceComponentsProps> = () => {
  const { params } = useParsed();

  const { queryResult } = useShow({
    resource: ResourceNames.ASSET,
    id: params?.id,
  });

  const { data, isLoading } = queryResult;
  const t = useTranslate();
  const { open } = useNotification();

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

  const [assetModel, assetObjectModel] = useMemo(() => {
    const asset = data?.data;

    if (!asset) {
      return [undefined, undefined];
    }

    const assetModel = new AssetModel(asset as Asset);
    const assetObjectModel = assetModel.getObject(params?.objectId);

    if (!assetObjectModel) {
      throw new Error("Asset object not found");
    }

    return [assetModel, assetObjectModel];
  }, [data, params]);

  // Use custom hooks for async operations
  const {
    isPreparingDownload,
    isCopyUrlLoading,
    clipboard,
    download,
    copyUrl,
  } = useAssetObjectDownload(assetModel, assetObjectModel);

  const { isChecking, result, isModalVisible, closeModal, check } =
    useAssetObjectIntegrity(assetObjectModel);

  const { isLoading: isProfileLoading, profile } =
    useAssetObjectProfile(assetObjectModel);

  const [isUpdatingName, setIsUpdatingName] = useState(false);

  const handleNameUpdate = useCallback(
    async (newName: string) => {
      if (!assetModel || !assetObjectModel) {
        return;
      }

      setIsUpdatingName(true);

      try {
        await updateAssetObject({
          assetId: assetModel.data.id,
          objectId: assetObjectModel.data.id,
          updateBody: {
            name: newName,
          },
        });

        open?.({
          message: t("assetObjects.nameUpdateSuccess", "Updated name"),
          type: "success",
        });

        await queryResult.refetch();
      } catch (error) {
        _.partial(
          catchErrorAndShow,
          open,
          t("assetObjects.errorUpdatingName", "Error updating name"),
        )(error);
      } finally {
        setIsUpdatingName(false);
      }
    },
    [assetModel, assetObjectModel, open, t, queryResult],
  );

  const handleDescriptionSave = useCallback(
    async (description: string) => {
      if (!assetModel || !assetObjectModel) {
        return;
      }

      await updateAssetObject({
        assetId: assetModel.data.id,
        objectId: assetObjectModel.data.id,
        updateBody: {
          description,
        },
      });

      open?.({
        message: t(
          "assetObjects.descriptionUpdateSuccess",
          "Updated description",
        ),
        type: "success",
      });
    },
    [assetModel, assetObjectModel, open, t],
  );

  const handleDownload = useCallback(() => {
    download()
      .then(() => {
        open?.({
          message: t("assetObjects.downloadStarted", "Download started"),
          type: "success",
        });
      })
      .catch(
        _.partial(
          catchErrorAndShow,
          open,
          t("assetObjects.errorDownloading", "Download error"),
        ),
      );
  }, [download, open, t]);

  const handleCopyUrl = useCallback(() => {
    copyUrl().catch(
      _.partial(
        catchErrorAndShow,
        open,
        t("assetObjects.errorDownloading", "Download error"),
      ),
    );
  }, [copyUrl, open, t]);

  const handleCheckIntegrity = useCallback(() => {
    check().catch(
      _.partial(
        catchErrorAndShow,
        open,
        t("assetObjects.integrityCheckFailed", "Integrity check error"),
      ),
    );
  }, [check, open, t]);

  return (
    <>
      <LoadingOverlay visible={isLoading || isUpdatingName} overlayBlur={2} />
      <LoadingOverlayWithMessage
        visible={isPreparingDownload}
        message={t(
          "assetObjects.loadingDownload",
          "We are preparing your download. A new tab will open shortly.",
        )}
      />
      <LoadingOverlayWithMessage
        visible={isChecking}
        message={t(
          "assetObjects.loadingIntegrity",
          "We are checking the integrity of this dataset object. This may take a while.",
        )}
      />
      {!!result && (
        <IntegrityModal
          integrityResult={result}
          opened={isModalVisible}
          close={closeModal}
        />
      )}
      {!!assetObjectModel && !!assetModel && (
        <Stack>
          <EditableTitle
            title={assetObjectModel.humanName}
            onSave={handleNameUpdate}
            isOwner={isOwner}
          />
          <Text color="dimmed">
            {t("assetObjects.partOfAsset", "This dataset is part of")}{" "}
            <Text component="span" fw={800}>
              {assetModel.data.name}
            </Text>
          </Text>
          <Paper p="md">
            <Stack>
              <Group position="apart">
                <Title order={4}>
                  {t("assetObjects.datasetDetails", "Dataset details")}
                </Title>
                <Group position="right">
                  <Button
                    component={Link}
                    to={routes.assetObjectExplore(
                      assetModel.data.id,
                      assetObjectModel.data.id,
                    )}
                    target="_blank"
                    variant="light"
                    leftIcon={<IconReportSearch size="1.3em" />}
                  >
                    {t("assetObjects.actions.explore", "Explore")}
                  </Button>
                  <Button
                    variant="light"
                    leftIcon={<IconDownload size="1.3em" />}
                    onClick={handleDownload}
                  >
                    {t("assetObjects.actions.download", "Download")}
                  </Button>
                  <Button
                    variant="light"
                    color={clipboard.copied ? "green" : "teal"}
                    leftIcon={
                      clipboard.copied ? (
                        <IconCheck size="1.3em" />
                      ) : (
                        <IconClipboard size="1.3em" />
                      )
                    }
                    onClick={handleCopyUrl}
                    loading={isCopyUrlLoading}
                    loaderProps={{ size: "xs" }}
                  >
                    {t("assetObjects.actions.copyDownloadUrl", "Copy URL")}
                  </Button>
                  <Button
                    variant="light"
                    color="green"
                    leftIcon={<IconFileCheck size="1.3em" />}
                    onClick={handleCheckIntegrity}
                  >
                    {t(
                      "assetObjects.actions.verifyIntegrity",
                      "Verify integrity",
                    )}
                  </Button>
                </Group>
              </Group>
              <Tabs defaultValue="description">
                <Tabs.List>
                  <Tabs.Tab
                    value="description"
                    icon={<IconFileText size={14} />}
                  >
                    {t("assetObjects.description", "Description")}
                  </Tabs.Tab>

                  <Tabs.Tab value="metadata" icon={<IconTable size={14} />}>
                    {t("assetObjects.metadata", "Metadata")}
                  </Tabs.Tab>

                  <Tabs.Tab
                    value="profile"
                    icon={<IconChartAreaLine size={14} />}
                  >
                    {t("assetObjects.profile", "Profile")}
                  </Tabs.Tab>
                </Tabs.List>

                <Tabs.Panel value="description" pt="md">
                  <AssetObjectDescriptionTab
                    assetObjectModel={assetObjectModel}
                    isOwner={isOwner}
                    onSave={handleDescriptionSave}
                  />
                </Tabs.Panel>

                <Tabs.Panel value="metadata" pt="md">
                  <AssetObjectMetadataTab assetObjectModel={assetObjectModel} />
                </Tabs.Panel>

                <Tabs.Panel value="profile" pt="md">
                  <AssetObjectProfileTab
                    isLoading={isProfileLoading}
                    profile={profile}
                  />
                </Tabs.Panel>
              </Tabs>
            </Stack>
          </Paper>
        </Stack>
      )}
    </>
  );
};
