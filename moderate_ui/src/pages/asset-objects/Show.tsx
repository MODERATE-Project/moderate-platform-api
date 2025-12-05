import {
  Anchor,
  Box,
  Breadcrumbs,
  Button,
  Card,
  Group,
  LoadingOverlay,
  Stack,
  Tabs,
  Text,
  ThemeIcon,
  Tooltip,
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
  IconDatabase,
  IconDownload,
  IconFileCheck,
  IconFileText,
  IconHome,
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

      await queryResult.refetch();
    },
    [assetModel, assetObjectModel, open, t, queryResult],
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

  const breadcrumbs = useMemo(() => {
    if (!assetModel || !assetObjectModel) return [];

    return [
      {
        title: t("dashboard.title", "Home"),
        href: routes.home(),
        icon: <IconHome size={14} />,
      },
      {
        title: t("assets.assets", "Assets"),
        href: routes.assetList(),
        icon: <IconDatabase size={14} />,
      },
      {
        title: assetModel.data.name,
        href: routes.assetShow(assetModel.data.id),
      },
      { title: assetObjectModel.humanName, href: null },
    ].map((item, index) =>
      item.href ? (
        <Anchor
          component={Link}
          to={item.href}
          key={index}
          size="sm"
          sx={{ display: "flex", alignItems: "center", gap: 4 }}
        >
          {item.icon} {item.title}
        </Anchor>
      ) : (
        <Text
          key={index}
          size="sm"
          color="dimmed"
          sx={{ display: "flex", alignItems: "center", gap: 4 }}
        >
          {item.icon} {item.title}
        </Text>
      ),
    );
  }, [assetModel, assetObjectModel, t]);

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
        <Stack spacing="xl">
          {/* Header Section */}
          <Stack spacing="xs">
            <Breadcrumbs separator="→" mb="xs">
              {breadcrumbs}
            </Breadcrumbs>

            <Group position="apart" align="flex-start">
              <Box>
                <Group align="center" spacing="xs">
                  <ThemeIcon size="lg" variant="light" color="blue">
                    <IconTable size={20} />
                  </ThemeIcon>
                  <EditableTitle
                    title={assetObjectModel.humanName}
                    onSave={handleNameUpdate}
                    isOwner={isOwner}
                  />
                </Group>

                <Text color="dimmed" size="sm" mt={4} ml={42}>
                  {t("assetObjects.partOfAsset", "Part of asset")}:{" "}
                  <Anchor
                    component={Link}
                    to={routes.assetShow(assetModel.data.id)}
                    weight={500}
                  >
                    {assetModel.data.name}
                  </Anchor>
                </Text>
              </Box>

              <Group spacing="sm">
                <Tooltip
                  label={t(
                    "assetObjects.actions.explore",
                    "Explore data in new tab",
                  )}
                >
                  <Button
                    component={Link}
                    to={routes.assetObjectExplore(
                      assetModel.data.id,
                      assetObjectModel.data.id,
                    )}
                    target="_blank"
                    variant="default"
                    leftIcon={<IconReportSearch size={18} />}
                  >
                    {t("assetObjects.actions.explore", "Explore")}
                  </Button>
                </Tooltip>

                <Tooltip
                  label={t("assetObjects.actions.download", "Download file")}
                >
                  <Button
                    variant="default"
                    leftIcon={<IconDownload size={18} />}
                    onClick={handleDownload}
                  >
                    {t("assetObjects.actions.download", "Download")}
                  </Button>
                </Tooltip>

                <Tooltip
                  label={t(
                    "assetObjects.actions.copyDownloadUrl",
                    "Copy download URL",
                  )}
                >
                  <Button
                    variant="default"
                    color={clipboard.copied ? "green" : "gray"}
                    leftIcon={
                      clipboard.copied ? (
                        <IconCheck size={18} />
                      ) : (
                        <IconClipboard size={18} />
                      )
                    }
                    onClick={handleCopyUrl}
                    loading={isCopyUrlLoading}
                    loaderProps={{ size: "xs" }}
                  >
                    {t("assetObjects.actions.copyDownloadUrl", "Copy URL")}
                  </Button>
                </Tooltip>

                <Tooltip
                  label={t(
                    "assetObjects.actions.verifyIntegrity",
                    "Verify data integrity",
                  )}
                >
                  <Button
                    variant="light"
                    color="green"
                    leftIcon={<IconFileCheck size={18} />}
                    onClick={handleCheckIntegrity}
                  >
                    {t(
                      "assetObjects.actions.verifyIntegrity",
                      "Verify Integrity",
                    )}
                  </Button>
                </Tooltip>
              </Group>
            </Group>
          </Stack>

          {/* Main Content */}
          <Card withBorder p="lg" radius="md" shadow="sm">
            <Tabs defaultValue="description" keepMounted={false}>
              <Tabs.List>
                <Tabs.Tab value="description" icon={<IconFileText size={16} />}>
                  {t("assetObjects.description", "Description")}
                </Tabs.Tab>

                <Tabs.Tab value="metadata" icon={<IconTable size={16} />}>
                  {t("assetObjects.metadata", "Metadata")}
                </Tabs.Tab>

                <Tabs.Tab
                  value="profile"
                  icon={<IconChartAreaLine size={16} />}
                >
                  {t("assetObjects.profile", "Profile")}
                </Tabs.Tab>
              </Tabs.List>

              <Box pt="xl">
                <Tabs.Panel value="description">
                  <AssetObjectDescriptionTab
                    assetObjectModel={assetObjectModel}
                    isOwner={isOwner}
                    onSave={handleDescriptionSave}
                  />
                </Tabs.Panel>

                <Tabs.Panel value="metadata">
                  <AssetObjectMetadataTab assetObjectModel={assetObjectModel} />
                </Tabs.Panel>

                <Tabs.Panel value="profile">
                  <AssetObjectProfileTab
                    isLoading={isProfileLoading}
                    profile={profile}
                  />
                </Tabs.Panel>
              </Box>
            </Tabs>
          </Card>
        </Stack>
      )}
    </>
  );
};
