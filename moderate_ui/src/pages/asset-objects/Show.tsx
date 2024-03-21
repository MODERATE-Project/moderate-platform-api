import { Group, LoadingOverlay, Menu, Paper, Tabs, Title } from "@mantine/core";
import {
  IResourceComponentsProps,
  useParsed,
  useShow,
  useTranslate,
} from "@refinedev/core";
import {
  IconChartAreaLine,
  IconDownload,
  IconFileCheck,
  IconFileText,
  IconReportSearch,
  IconTable,
} from "@tabler/icons";
import React, { useMemo } from "react";
import { Link } from "react-router-dom";
import { EllipsisButton } from "../../components/EllipsisButton";
import { KeyValuesStack } from "../../components/KeyValuesStack";

export const AssetObjectShow: React.FC<IResourceComponentsProps> = () => {
  const { params } = useParsed();
  const { queryResult } = useShow({ resource: "asset", id: params?.id });
  const { data, isLoading } = queryResult;
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

  return (
    <>
      <LoadingOverlay visible={isLoading} overlayBlur={2} />
      <Paper p="md">
        {assetObject && (
          <>
            <Group position="apart" mb="md">
              <Title order={3}>{assetObject.key}</Title>
              <EllipsisButton>
                <Menu.Item
                  component={Link}
                  to={`/assets/${params?.id}/objects/explore/${assetObject.id}`}
                  icon={<IconReportSearch size="1em" color="blue" />}
                >
                  {t("assetObjects.actions.explore", "Explore")}
                </Menu.Item>

                <Menu.Item icon={<IconDownload size="1em" color="blue" />}>
                  {t("assetObjects.actions.download", "Download")}
                </Menu.Item>

                <Menu.Item icon={<IconFileCheck size="1em" color="blue" />}>
                  {t(
                    "assetObjects.actions.verifyIntegrity",
                    "Verify integrity"
                  )}
                </Menu.Item>
              </EllipsisButton>
            </Group>
            <Tabs defaultValue="metadata">
              <Tabs.List>
                <Tabs.Tab value="metadata" icon={<IconTable size={14} />}>
                  {t("assetObjects.metadata", "Metadata")}
                </Tabs.Tab>

                <Tabs.Tab value="description" icon={<IconFileText size={14} />}>
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
                {assetObject && <KeyValuesStack obj={assetObject} />}
              </Tabs.Panel>

              <Tabs.Panel value="description" pt="md">
                Description
              </Tabs.Panel>

              <Tabs.Panel value="profile" pt="md">
                Profile
              </Tabs.Panel>
            </Tabs>
          </>
        )}
      </Paper>
    </>
  );
};
