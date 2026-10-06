import { useCustom } from "@refinedev/core";
import { useEffect, useMemo } from "react";
import {
  PLATFORM_APPLICATIONS_URL,
  PlatformApplicationStatus,
} from "../api/platformApplications";
import {
  PlatformApplication,
  platformApplications,
} from "../data/platformApplications";

export interface ConfiguredPlatformApplication extends PlatformApplication {
  url: string | null;
  sourceUrl: string | null;
  online: boolean | null;
}

export interface UsePlatformApplicationsReturn {
  applications: ConfiguredPlatformApplication[];
  isLoading: boolean;
  isError: boolean;
}

/**
 * Merges the links and availability reported by the API into the static
 * presentation metadata, in UI order. Applications the API does not list
 * are left out. Components calling this hook share one cached request.
 */
export function usePlatformApplications(): UsePlatformApplicationsReturn {
  const { data, isLoading, isError } = useCustom<PlatformApplicationStatus[]>({
    url: PLATFORM_APPLICATIONS_URL,
    method: "get",
    errorNotification: false,
  });

  const statuses = useMemo(
    (): PlatformApplicationStatus[] => data?.data ?? [],
    [data],
  );

  useEffect(() => {
    const knownIds = new Set(platformApplications.map(({ id }) => id));

    statuses
      .filter(({ id }) => !knownIds.has(id))
      .forEach(({ id }) =>
        console.warn(`Platform application "${id}" has no UI metadata`),
      );
  }, [statuses]);

  const applications = useMemo((): ConfiguredPlatformApplication[] => {
    const statusById = new Map(statuses.map((status) => [status.id, status]));

    return platformApplications.flatMap((application) => {
      const status = statusById.get(application.id);

      return status
        ? [
            {
              ...application,
              url: status.url,
              sourceUrl: status.source_url,
              online: status.online,
            },
          ]
        : [];
    });
  }, [statuses]);

  return { applications, isLoading, isError };
}
