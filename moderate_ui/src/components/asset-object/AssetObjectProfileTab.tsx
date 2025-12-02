import { Alert, Skeleton, Title } from "@mantine/core";
import { useTranslate } from "@refinedev/core";
import { IconZoomQuestion } from "@tabler/icons-react";
import React from "react";
import { AssetObjectProfileResult } from "../../api/assets";
import { AssetObjectProfile } from "./AssetObjectProfile";

interface AssetObjectProfileTabProps {
  isLoading: boolean;
  profile?: AssetObjectProfileResult;
}

/**
 * Tab component for displaying asset object profile/profiling data
 */
export const AssetObjectProfileTab: React.FC<AssetObjectProfileTabProps> = ({
  isLoading,
  profile,
}) => {
  const t = useTranslate();

  if (isLoading) {
    return (
      <>
        <Skeleton height={20} mb="md" />
        <Skeleton height={20} mb="md" />
        <Skeleton height={20} />
      </>
    );
  }

  if (profile?.profile) {
    return <AssetObjectProfile profile={profile} />;
  }

  return (
    <Alert
      icon={<IconZoomQuestion size={32} />}
      title={
        <Title order={3}>
          {t("assetObjects.profileEmptyTitle", "No profile found")}
        </Title>
      }
      color="gray"
    >
      {t(
        "assetObjects.profileEmptyMessage",
        "We have not yet profiled this dataset. Please check back again in a few hours.",
      )}
    </Alert>
  );
};
