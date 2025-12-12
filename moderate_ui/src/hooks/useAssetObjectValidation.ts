import { useNotification } from "@refinedev/core";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ValidationResult,
  ValidationStatus,
  getValidationStatus,
  startValidation,
} from "../api/validation";
import { catchErrorAndShow } from "../utils";

/**
 * Default polling interval in milliseconds
 */
const DEFAULT_POLL_INTERVAL = 3000;

/**
 * Options for the useAssetObjectValidation hook
 */
export interface UseAssetObjectValidationOptions {
  assetId: number | string;
  objectId: number | string;
  pollInterval?: number;
  usePublicEndpoint?: boolean;
}

/**
 * Return type for the useAssetObjectValidation hook
 */
export interface UseAssetObjectValidationReturn {
  /** Current validation status and results */
  status: ValidationResult | null;
  /** Whether an initial load or action is in progress */
  isLoading: boolean;
  /** Whether polling is actively running */
  isPolling: boolean;
  /** Error message if something went wrong */
  error: string | null;
  /** Start validation for the asset object */
  startValidation: () => Promise<void>;
  /** Manually refresh the status */
  refreshStatus: () => Promise<void>;
  /** Stop polling */
  stopPolling: () => void;
}

/**
 * Check if validation status indicates polling should continue
 */
function shouldPoll(status: ValidationStatus | undefined): boolean {
  return status === "in_progress";
}

/**
 * Custom hook for managing asset object validation
 *
 * Features:
 * - Fetches initial validation status on mount
 * - Starts validation via API
 * - Auto-polls when status is "in_progress"
 * - Stops polling when validation completes or fails
 */
export const useAssetObjectValidation = ({
  assetId,
  objectId,
  pollInterval = DEFAULT_POLL_INTERVAL,
  usePublicEndpoint,
}: UseAssetObjectValidationOptions): UseAssetObjectValidationReturn => {
  const [status, setStatus] = useState<ValidationResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isPolling, setIsPolling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { open } = useNotification();
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const isMountedRef = useRef(true);

  // Clean up on unmount
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  // Fetch validation status
  const fetchStatus = useCallback(async () => {
    try {
      const result = await getValidationStatus({
        assetId,
        objectId,
        usePublicEndpoint,
      });

      if (isMountedRef.current) {
        setStatus(result);
        setError(null);
        return result;
      }
    } catch (err) {
      if (isMountedRef.current) {
        const errorMessage =
          err instanceof Error ? err.message : "Failed to fetch status";
        setError(errorMessage);
        catchErrorAndShow(open, undefined, err);
      }
    }
    return null;
  }, [assetId, objectId, usePublicEndpoint, open]);

  // Start polling
  const startPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      return; // Already polling
    }

    setIsPolling(true);

    pollIntervalRef.current = setInterval(async () => {
      const result = await fetchStatus();

      if (result && !shouldPoll(result.status) && isMountedRef.current) {
        // Stop polling when validation is no longer in progress
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current);
          pollIntervalRef.current = null;
        }
        setIsPolling(false);
      }
    }, pollInterval);
  }, [fetchStatus, pollInterval]);

  // Stop polling
  const stopPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    setIsPolling(false);
  }, []);

  // Start validation
  const handleStartValidation = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      await startValidation({ assetId, objectId });

      // Immediately fetch status after starting
      const result = await fetchStatus();

      // Start polling if validation is in progress
      if (result && shouldPoll(result.status)) {
        startPolling();
      }
    } catch (err) {
      if (isMountedRef.current) {
        const errorMessage =
          err instanceof Error ? err.message : "Failed to start validation";
        setError(errorMessage);
        catchErrorAndShow(open, undefined, err);
      }
    } finally {
      if (isMountedRef.current) {
        setIsLoading(false);
      }
    }
  }, [assetId, objectId, fetchStatus, startPolling, open]);

  // Refresh status manually
  const refreshStatus = useCallback(async () => {
    setIsLoading(true);
    const result = await fetchStatus();

    // Start polling if validation is in progress
    if (result && shouldPoll(result.status)) {
      startPolling();
    }

    if (isMountedRef.current) {
      setIsLoading(false);
    }
  }, [fetchStatus, startPolling]);

  // Fetch initial status on mount
  useEffect(() => {
    setIsLoading(true);

    fetchStatus()
      .then((result) => {
        // Auto-start polling if validation is already in progress
        if (result && shouldPoll(result.status)) {
          startPolling();
        }
      })
      .finally(() => {
        if (isMountedRef.current) {
          setIsLoading(false);
        }
      });

    // Cleanup polling on unmount or when dependencies change
    return () => {
      stopPolling();
    };
  }, [fetchStatus, startPolling, stopPolling]);

  return {
    status,
    isLoading,
    isPolling,
    error,
    startValidation: handleStartValidation,
    refreshStatus,
    stopPolling,
  };
};
