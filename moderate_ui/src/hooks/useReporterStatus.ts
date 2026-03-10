import { useCallback, useEffect, useRef, useState } from "react";
import { getReporterStatus, ReporterStatus } from "../api/validation";

/**
 * Default refresh interval in milliseconds (30 seconds).
 */
const DEFAULT_REFRESH_INTERVAL = 30000;

/**
 * Return type for the useReporterStatus hook.
 */
export interface UseReporterStatusReturn {
  /** Current reporter status */
  reporterStatus: ReporterStatus | null;
  /** Whether the initial fetch is in progress */
  isLoading: boolean;
  /** Error message if fetch failed */
  error: string | null;
  /** Manually refresh the status */
  refetch: () => Promise<void>;
}

/**
 * Custom hook for fetching and auto-refreshing DIVA Reporter health status.
 *
 * Features:
 * - Fetches reporter status on mount
 * - Auto-refreshes every 30 seconds
 * - Cleans up interval on unmount
 */
export function useReporterStatus(
  refreshInterval: number = DEFAULT_REFRESH_INTERVAL,
): UseReporterStatusReturn {
  const [reporterStatus, setReporterStatus] = useState<ReporterStatus | null>(
    null,
  );
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const isMountedRef = useRef(true);

  const fetchStatus = useCallback(async () => {
    try {
      const result = await getReporterStatus();
      if (isMountedRef.current) {
        setReporterStatus(result);
        setError(null);
      }
    } catch (err) {
      if (isMountedRef.current) {
        setError(
          err instanceof Error
            ? err.message
            : "Failed to fetch reporter status",
        );
      }
    }
  }, []);

  const refetch = useCallback(async () => {
    setIsLoading(true);
    await fetchStatus();
    if (isMountedRef.current) {
      setIsLoading(false);
    }
  }, [fetchStatus]);

  useEffect(() => {
    isMountedRef.current = true;

    // Initial fetch
    fetchStatus().finally(() => {
      if (isMountedRef.current) {
        setIsLoading(false);
      }
    });

    // Set up periodic refresh
    const intervalId = setInterval(fetchStatus, refreshInterval);

    return () => {
      isMountedRef.current = false;
      clearInterval(intervalId);
    };
  }, [fetchStatus, refreshInterval]);

  return { reporterStatus, isLoading, error, refetch };
}
