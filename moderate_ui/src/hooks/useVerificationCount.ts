import { useEffect, useState } from "react";
import {
  VerificationCountItem,
  getObjectVerificationCount,
} from "../api/assets";
import { AssetObjectModel } from "../api/types";

// Retry window must exceed the backend's _CACHE_FETCH_TIMEOUT (15 s).
// 6 × 3 s = 18 s covers the full cold-start fetch window with margin.
const _MAX_RETRIES = 6;
const _RETRY_DELAY_MS = 3000;

export const useVerificationCount = (assetObjectModel?: AssetObjectModel) => {
  const [isLoading, setIsLoading] = useState(false);
  const [verificationCount, setVerificationCount] =
    useState<VerificationCountItem | null>(null);
  const [fetchFailed, setFetchFailed] = useState(false);

  useEffect(() => {
    if (!assetObjectModel) {
      return;
    }

    let cancelled = false;
    setIsLoading(true);
    setFetchFailed(false);

    const tryFetch = (attempt: number) => {
      getObjectVerificationCount({ objectKeyOrId: assetObjectModel.data.id })
        .then((data) => {
          if (cancelled) return;

          if (data === null && attempt < _MAX_RETRIES) {
            // Backend cache is warming up after a cold start — retry shortly
            setTimeout(() => {
              if (!cancelled) tryFetch(attempt + 1);
            }, _RETRY_DELAY_MS);
            return;
          }

          setVerificationCount(data);
          setIsLoading(false);
        })
        .catch(() => {
          if (cancelled) return;
          setFetchFailed(true);
          setVerificationCount(null);
          setIsLoading(false);
        });
    };

    tryFetch(0);

    return () => {
      cancelled = true;
    };
  }, [assetObjectModel]);

  return { isLoading, verificationCount, fetchFailed };
};
