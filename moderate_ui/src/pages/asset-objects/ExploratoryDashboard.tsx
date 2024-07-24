import {
  Alert,
  Box,
  Code,
  Loader,
  LoadingOverlay,
  Paper,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import {
  useNotification,
  useParsed,
  useShow,
  useTranslate,
} from "@refinedev/core";
import { IconFlask, IconGraphOff } from "@tabler/icons-react";
import { useEffect, useMemo, useState } from "react";
import { fetchPygwalkerHtml } from "../../api/assets";
import { ResourceNames } from "../../types";

export const AssetObjectExploratoryDashboard: React.FC = () => {
  const { params } = useParsed();

  const { queryResult } = useShow({
    resource: ResourceNames.ASSET,
    id: params?.id,
  });

  const { data, isLoading } = queryResult;
  const { open } = useNotification();
  const [isDownloadingDashboard, setIsDownloadingDashboard] = useState(false);
  const [alertClosed, setAlertClosed] = useState(false);

  const [error, setError] = useState<{ [k: string]: any } | undefined>(
    undefined
  );

  const [dashboardHtml, setDashboardHtml] = useState<string | undefined>(
    undefined
  );

  const t = useTranslate();

  const assetObject = useMemo((): { [key: string]: any } | undefined => {
    const asset = data?.data;

    if (!asset) {
      return undefined;
    }

    return asset?.objects.find(
      (item: { [key: string]: any }) => item.id == params?.objectId
    );
  }, [data, params]);

  useEffect(() => {
    if (!assetObject) {
      return;
    }

    setIsDownloadingDashboard(true);

    fetchPygwalkerHtml({ objectId: assetObject.id })
      .then((response) => {
        setDashboardHtml(response.data);
      })
      .catch((err) => {
        setError(err);
      })
      .then(() => {
        setIsDownloadingDashboard(false);
      });
  }, [assetObject, setIsDownloadingDashboard, open, t]);

  return (
    <>
      <LoadingOverlay
        visible={isLoading || isDownloadingDashboard}
        loader={
          <Stack justify="center" align="center">
            <Loader size="xl" />
            <Text color="dimmed">
              {t(
                "assetObjects.dashboard.loadingMessage",
                "We're preparing the dashboard to explore the dataset. Please wait, this process may take several minutes, depending on your connection."
              )}
            </Text>
          </Stack>
        }
      />
      {error && (
        <Alert
          mt="xl"
          icon={<IconGraphOff size={32} />}
          title={
            <Title order={3}>
              {t("assetObjects.dashboard.error", "Unable to display dashboard")}
            </Title>
          }
          color="red"
        >
          {t(
            "assetObjects.dashboard.noResultsDescription",
            "It is likely that the dataset is too large to be displayed in the exploratory dashboard. Please check the error message below."
          )}
          {error?.response?.data?.detail && (
            <Box mt="sm" mb={0}>
              <Code>{error.response.data.detail}</Code>
            </Box>
          )}
        </Alert>
      )}
      {dashboardHtml && (
        <>
          {!alertClosed && (
            <Alert
              icon={<IconFlask size="1rem" />}
              title={t(
                "assetObjects.dashboard.experimentAlertTitle",
                "Experimental feature"
              )}
              color="yellow"
              withCloseButton
              onClose={() => setAlertClosed(true)}
            >
              {t(
                "assetObjects.dashboard.experimentAlertMessage",
                "This feature is experimental. You may experience some performance issues while using it."
              )}
            </Alert>
          )}
          <Paper p="md">
            <div dangerouslySetInnerHTML={{ __html: dashboardHtml }}></div>
          </Paper>
        </>
      )}
    </>
  );
};
