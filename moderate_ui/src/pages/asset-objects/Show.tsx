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
        Lorem ipsum dolor sit amet consectetur adipisicing elit. Blanditiis
        iusto officia facilis quaerat, quasi facere iure cumque alias deleniti
        error temporibus quos similique quas consequuntur tempore? Consequuntur
        vero obcaecati nostrum.
      </div>
    </>
  );
};
