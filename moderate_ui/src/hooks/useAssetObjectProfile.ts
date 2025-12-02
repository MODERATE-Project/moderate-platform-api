import { useNotification } from "@refinedev/core";
import _ from "lodash";
import { useEffect, useState } from "react";
import { AssetObjectProfileResult, getAssetObjectProfile } from "../api/assets";
import { AssetObjectModel } from "../api/types";
import { catchErrorAndShow } from "../utils";

/**
 * Custom hook for fetching asset object profile data
 * Automatically fetches profile on mount or when assetObjectModel changes
 */
export const useAssetObjectProfile = (assetObjectModel?: AssetObjectModel) => {
  const [isLoading, setIsLoading] = useState(false);
  const [profile, setProfile] = useState<AssetObjectProfileResult>();
  const { open } = useNotification();

  useEffect(() => {
    if (!assetObjectModel) {
      return;
    }

    setIsLoading(true);

    getAssetObjectProfile({ objectId: assetObjectModel.data.id })
      .then(setProfile)
      .catch(_.partial(catchErrorAndShow, open, undefined))
      .then(() => {
        setIsLoading(false);
      });
  }, [assetObjectModel, open]);

  return {
    isLoading,
    profile,
  };
};
