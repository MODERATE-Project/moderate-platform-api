import { useModal } from "@refinedev/core";
import { useCallback, useState } from "react";
import {
  AssetObjectIntegrityResponse,
  checkAssetObjectIntegrity,
} from "../api/assets";
import { AssetObjectModel } from "../api/types";

/**
 * Custom hook for handling asset object integrity checks
 */
export const useAssetObjectIntegrity = (
  assetObjectModel?: AssetObjectModel,
) => {
  const [isChecking, setIsChecking] = useState(false);
  const [result, setResult] = useState<AssetObjectIntegrityResponse>();
  const {
    visible: isModalVisible,
    show: showModal,
    close: closeModal,
  } = useModal();

  const check = useCallback(async () => {
    if (!assetObjectModel) {
      throw new Error("Asset object model not provided");
    }

    setIsChecking(true);
    try {
      const response = await checkAssetObjectIntegrity({
        objectKeyOrId: assetObjectModel.data.id,
      });
      setResult(response);
      showModal();
      return response;
    } finally {
      setIsChecking(false);
    }
  }, [assetObjectModel, showModal]);

  return {
    isChecking,
    result,
    isModalVisible,
    showModal,
    closeModal,
    check,
  };
};
