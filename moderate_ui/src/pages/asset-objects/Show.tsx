import {
  Alert,
  Button,
  Code,
  Group,
  Loader,
  LoadingOverlay,
  Modal,
  Paper,
  Stack,
  Tabs,
  Text,
  Title,
} from "@mantine/core";
import {
  IResourceComponentsProps,
  useModal,
  useNotification,
  useParsed,
  useShow,
  useTranslate,
} from "@refinedev/core";
import {
  IconAlertCircle,
  IconChartAreaLine,
  IconCheck,
  IconDownload,
  IconFileCheck,
  IconFileText,
  IconMessageQuestion,
  IconReportSearch,
  IconTable,
  IconTableFilled,
} from "@tabler/icons-react";
import _ from "lodash";
import React, { useCallback, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  AssetObjectIntegrityResponse,
  checkAssetObjectIntegrity,
  downloadAssetObjects,
} from "../../api/assets";
import { Asset, AssetModel } from "../../api/types";
import { KeyValuesStack } from "../../components/KeyValuesStack";
import { ResourceNames } from "../../types";
import { catchErrorAndShow } from "../../utils";

interface IntegrityModalProps {
  opened: boolean;
  close: () => void;
  integrityResult: AssetObjectIntegrityResponse;
}

const IntegrityModal: React.FC<IntegrityModalProps> = ({
  opened,
  close,
  integrityResult,
}) => {
  const t = useTranslate();

  const defaultBodyOk = `
    This dataset has passed the integrity check,
    so there's a high degree of confidence that it has not been tampered with
    and is the same version that was originally uploaded.`;

  const defaultBodyFailed = `
    This dataset has failed the integrity check.
    This does not necessarily mean that the dataset has been compromised;
    it could also be that the cryptographic proof has not yet been created on the DLT.
    Please wait a few minutes.
    In any case, you should operate under the assumption that the dataset has been tampered with.
    Please see the error message below for more details:`;

  return (
    <Modal
      opened={opened}
      onClose={close}
      size="lg"
      title={
        <Title order={5}>
          {t("assetObjects.integrityCheck", "Cryptographic integrity check")}
        </Title>
      }
    >
      {!!integrityResult && (
        <Alert
          icon={integrityResult.valid ? <IconCheck /> : <IconAlertCircle />}
          color={integrityResult.valid ? "green" : "red"}
          title={
            integrityResult.valid
              ? t(
                  "assetObjects.integrityTitleOk",
                  "All good: integrity check successful"
                )
              : t("assetObjects.integrityTitleFailed", "Integrity check failed")
          }
        >
          {integrityResult.valid ? (
            <Text>{t("assetObjects.integrityBodyOk", defaultBodyOk)}</Text>
          ) : (
            <>
              <Text mb="md">
                {t("assetObjects.integrityBodyFailed", defaultBodyFailed)}
              </Text>
              <Code>{integrityResult.reason}</Code>
            </>
          )}
        </Alert>
      )}
    </Modal>
  );
};

export const AssetObjectShow: React.FC<IResourceComponentsProps> = () => {
  const { params } = useParsed();

  const { queryResult } = useShow({
    resource: ResourceNames.ASSET,
    id: params?.id,
  });

  const { data, isLoading } = queryResult;
  const t = useTranslate();
  const { open } = useNotification();

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

  const [isPreparingDownload, setIsPreparingDownload] =
    useState<boolean>(false);

  const downloadObject = useCallback(() => {
    if (!assetModel) {
      return;
    }

    setIsPreparingDownload(true);

    downloadAssetObjects({
      assetId: assetModel.data.id,
    })
      .then((downloadItems) => {
        const theItem = downloadItems.find((item) => {
          return item.key === assetObjectModel.data.key;
        });

        if (!theItem) {
          throw new Error("Dataset not found");
        }

        open &&
          open({
            message: t("assetObjects.downloadStarted", "Download started"),
            type: "success",
          });

        window.open(theItem.download_url, "_blank");
      })
      .catch(
        _.partial(
          catchErrorAndShow,
          open,
          t("assetObjects.errorDownloading", "Download error")
        )
      )
      .then(() => {
        setIsPreparingDownload(false);
      });
  }, [assetModel, assetObjectModel, open, t]);

  const [isCheckingIntegrity, setIsCheckingIntegrity] =
    useState<boolean>(false);

  const [integrityResult, setIntegrityResult] = useState<
    AssetObjectIntegrityResponse | undefined
  >(undefined);

  const {
    visible: isModalVisible,
    show: showModal,
    close: closeModal,
  } = useModal();

  const checkIntegrity = useCallback(() => {
    if (!assetObjectModel) {
      return;
    }

    setIsCheckingIntegrity(true);

    checkAssetObjectIntegrity({
      objectKeyOrId: assetObjectModel.data.id,
    })
      .then((response) => {
        setIntegrityResult(response);
        showModal();
      })
      .catch(
        _.partial(
          catchErrorAndShow,
          open,
          t("assetObjects.integrityCheckFailed", "Integrity check error")
        )
      )
      .then(() => {
        setIsCheckingIntegrity(false);
      });
  }, [assetObjectModel, open, t, showModal]);

  return (
    <>
      <LoadingOverlay visible={isLoading} overlayBlur={2} />
      <LoadingOverlay
        visible={isPreparingDownload}
        loader={
          <Stack justify="center" align="center">
            <Loader size="xl" />
            <Text color="dimmed">
              {t(
                "assetObjects.loadingDownload",
                "We are preparing your download. A new tab will open shortly."
              )}
            </Text>
          </Stack>
        }
      />
      <LoadingOverlay
        visible={isCheckingIntegrity}
        loader={
          <Stack justify="center" align="center">
            <Loader size="xl" />
            <Text color="dimmed">
              {t(
                "assetObjects.loadingIntegrity",
                "We are checking the integrity of this dataset object. This may take a while."
              )}
            </Text>
          </Stack>
        }
      />
      {!!integrityResult && (
        <IntegrityModal
          integrityResult={integrityResult}
          opened={isModalVisible}
          close={closeModal}
        />
      )}
      {!!assetObjectModel && (
        <Stack>
          <Title>
            <IconTableFilled color="purple" size="1em" />{" "}
            {assetObjectModel.humanName}
          </Title>
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
                    to={`/assets/${assetModel.data.id}/objects/explore/${assetObjectModel.data.id}`}
                    target="_blank"
                    variant="light"
                    leftIcon={<IconReportSearch size="1em" />}
                  >
                    {t("assetObjects.actions.explore", "Explore")}
                  </Button>
                  <Button
                    variant="light"
                    leftIcon={<IconDownload size="1em" />}
                    onClick={downloadObject}
                  >
                    {t("assetObjects.actions.download", "Download")}
                  </Button>
                  <Button
                    variant="light"
                    color="green"
                    leftIcon={<IconFileCheck size="1em" />}
                    onClick={checkIntegrity}
                  >
                    {t(
                      "assetObjects.actions.verifyIntegrity",
                      "Verify integrity"
                    )}
                  </Button>
                </Group>
              </Group>
              <Tabs defaultValue="metadata">
                <Tabs.List>
                  <Tabs.Tab value="metadata" icon={<IconTable size={14} />}>
                    {t("assetObjects.metadata", "Metadata")}
                  </Tabs.Tab>

                  <Tabs.Tab
                    value="description"
                    icon={<IconFileText size={14} />}
                  >
                    {t("assetObjects.description", "Description")}
                  </Tabs.Tab>

                  <Tabs.Tab
                    value="profile"
                    icon={<IconChartAreaLine size={14} />}
                  >
                    {t("assetObjects.profile", "Profile")}
                  </Tabs.Tab>
                </Tabs.List>

                <Tabs.Panel value="metadata" pt="md">
                  {assetObjectModel && (
                    <KeyValuesStack obj={assetObjectModel.data} />
                  )}
                </Tabs.Panel>

                <Tabs.Panel value="description" pt="md">
                  {assetObjectModel.description ? (
                    assetObjectModel.description
                  ) : (
                    <Alert
                      icon={<IconMessageQuestion size={32} />}
                      title={
                        <Title order={3}>
                          {t(
                            "assetObjects.descriptionEmptyTitle",
                            "No description"
                          )}
                        </Title>
                      }
                      color="gray"
                    >
                      {t(
                        "assetObjects.descriptionEmptyMessage",
                        "The owner of this dataset has not provided a description yet."
                      )}
                    </Alert>
                  )}
                </Tabs.Panel>

                <Tabs.Panel value="profile" pt="md">
                  {t("assetObjects.profile", "Profile")}
                </Tabs.Panel>
              </Tabs>
            </Stack>
          </Paper>
        </Stack>
      )}
    </>
  );
};
