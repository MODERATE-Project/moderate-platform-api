import { Loader, LoadingOverlay, Paper, Stack, Text } from "@mantine/core";
import { useParsed, useShow, useTranslate } from "@refinedev/core";
import { useEffect, useMemo, useState } from "react";
import { fetchPygwalkerHtml } from "../../api/visualization";

export const AssetObjectExploratoryDashboard: React.FC = () => {
  const { params } = useParsed();
  const { queryResult } = useShow({ resource: "asset", id: params?.id });
  const { data, isLoading } = queryResult;
  const [isDownloadingDashboard, setIsDownloadingDashboard] = useState(false);
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
        console.log(response);
        setDashboardHtml(response.data);
      })
      .catch((err) => {
        console.error(err);
      })
      .then(() => {
        setIsDownloadingDashboard(false);
      });
  }, [assetObject, setIsDownloadingDashboard]);

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
      {dashboardHtml && (
        <Paper p="md">
          <div dangerouslySetInnerHTML={{ __html: dashboardHtml }}></div>
        </Paper>
      )}
    </>
  );
};
