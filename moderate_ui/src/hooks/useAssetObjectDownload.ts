import { useClipboard } from "@mantine/hooks";
import { useCallback, useState } from "react";
import { downloadAssetObjects } from "../api/assets";
import { AssetModel, AssetObjectModel } from "../api/types";

/**
 * Custom hook for handling asset object downloads and URL copying
 */
export const useAssetObjectDownload = (
  assetModel?: AssetModel,
  assetObjectModel?: AssetObjectModel,
) => {
  const [isPreparingDownload, setIsPreparingDownload] = useState(false);
  const [isCopyUrlLoading, setIsCopyUrlLoading] = useState(false);
  const clipboard = useClipboard({ timeout: 500 });

  const fetchPresignedDownloadUrl = useCallback(async () => {
    if (!assetModel || !assetObjectModel) {
      throw new Error("Asset model or object model not provided");
    }

    const downloadItems = await downloadAssetObjects({
      assetId: assetModel.data.id,
    });

    const theItem = downloadItems.find((item) => {
      return item.key === assetObjectModel.data.key;
    });

    if (!theItem) {
      throw new Error("Dataset not found");
    }

    return theItem.download_url;
  }, [assetModel, assetObjectModel]);

  const download = useCallback(async () => {
    setIsPreparingDownload(true);
    try {
      const downloadUrl = await fetchPresignedDownloadUrl();
      window.open(downloadUrl, "_blank");
      return downloadUrl;
    } finally {
      setIsPreparingDownload(false);
    }
  }, [fetchPresignedDownloadUrl]);

  const copyUrl = useCallback(async () => {
    setIsCopyUrlLoading(true);
    try {
      const downloadUrl = await fetchPresignedDownloadUrl();
      clipboard.copy(downloadUrl);
      return downloadUrl;
    } finally {
      setIsCopyUrlLoading(false);
    }
  }, [fetchPresignedDownloadUrl, clipboard]);

  return {
    isPreparingDownload,
    isCopyUrlLoading,
    clipboard,
    download,
    copyUrl,
  };
};
