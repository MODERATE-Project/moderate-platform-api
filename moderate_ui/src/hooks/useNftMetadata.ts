import { useEffect, useState } from "react";
import { NftMetadata, getAssetNftMetadata } from "../api/assets";
import { AssetObjectModel } from "../api/types";

export const useNftMetadata = (assetObjectModel?: AssetObjectModel) => {
  const [isLoading, setIsLoading] = useState(false);
  const [nftMetadata, setNftMetadata] = useState<NftMetadata | null>(null);

  useEffect(() => {
    if (!assetObjectModel) {
      setNftMetadata(null);
      return;
    }

    let cancelled = false;
    setIsLoading(true);
    setNftMetadata(null);

    getAssetNftMetadata({ objectKeyOrId: assetObjectModel.data.id })
      .then((data) => {
        if (cancelled) return;
        setNftMetadata(data);
        setIsLoading(false);
      })
      .catch(() => {
        if (cancelled) return;
        setNftMetadata(null);
        setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [assetObjectModel]);

  return { isLoading, nftMetadata };
};
