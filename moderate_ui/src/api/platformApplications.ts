import { buildApiUrl } from "./utils";

/**
 * Links and availability of a platform application, as reported by the API.
 * `online` is null when the application has no live URL to check.
 */
export interface PlatformApplicationStatus {
  id: string;
  url: string | null;
  source_url: string | null;
  online: boolean | null;
}

export const PLATFORM_APPLICATIONS_URL = buildApiUrl(
  "platform-application",
  "public",
);
