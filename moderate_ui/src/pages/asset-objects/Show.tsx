import { LoadingOverlay } from "@mantine/core";
import {
  IResourceComponentsProps,
  useParsed,
  useShow,
  useTranslate,
} from "@refinedev/core";
import React from "react";

export const AssetObjectShow: React.FC<IResourceComponentsProps> = () => {
  const translate = useTranslate();
  const { params } = useParsed();
  const { queryResult } = useShow({ resource: "asset", id: params?.id });
  const { data, isLoading } = queryResult;
  const asset = data?.data;

  return (
    <>
      <LoadingOverlay visible={isLoading} overlayBlur={2} />
      <div>
        This is the show page for asset object with id: {params?.objectId}
      </div>
    </>
  );
};
