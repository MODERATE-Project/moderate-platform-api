import React from "react";
import { AssetObjectModel } from "../../api/types";
import { KeyValuesStack } from "../KeyValuesStack";

interface AssetObjectMetadataTabProps {
  assetObjectModel: AssetObjectModel;
}

/**
 * Simple tab component displaying asset object metadata
 */
export const AssetObjectMetadataTab: React.FC<AssetObjectMetadataTabProps> = ({
  assetObjectModel,
}) => {
  return (
    <KeyValuesStack
      obj={assetObjectModel.data}
      omitFields={["description", "id"]}
    />
  );
};
