import axios from "axios";
import { buildApiUrl } from "./utils";

/**
 * Status of a validation job.
 */
export type ValidationStatus =
  | "not_started"
  | "in_progress"
  | "complete"
  | "failed"
  | "unsupported";

/**
 * A single validation entry from DIVA Quality Reporter.
 */
export interface ValidationEntry {
  validator: string;
  rule: string;
  feature: string;
  valid: number;
  fail: number;
}

/**
 * Computed properties for a validation entry.
 */
export interface ValidationEntryWithStats extends ValidationEntry {
  total: number;
  passRate: number;
}

/**
 * Complete validation result from the API.
 */
export interface ValidationResult {
  status: ValidationStatus;
  entries: ValidationEntry[];
  total_valid: number;
  total_fail: number;
  overall_pass_rate: number;
  error_message?: string;
  processed_rows?: number;
  is_mock?: boolean;
}

/**
 * Response from starting a validation job.
 */
export interface StartValidationResponse {
  dataset_id: string;
  message: string;
}

/**
 * Add computed stats to validation entries.
 */
export function addEntryStats(
  entries: ValidationEntry[],
): ValidationEntryWithStats[] {
  return entries.map((entry) => {
    const total = entry.valid + entry.fail;
    const passRate = total > 0 ? (entry.valid / total) * 100 : 0;
    return {
      ...entry,
      total,
      passRate,
    };
  });
}

/**
 * Start data quality validation for an asset object.
 */
export async function startValidation({
  assetId,
  objectId,
}: {
  assetId: string | number;
  objectId: string | number;
}): Promise<StartValidationResponse> {
  const url = buildApiUrl(
    "asset",
    assetId.toString(),
    "object",
    objectId.toString(),
    "validate",
  );

  const response = await axios.post(url);
  return response.data;
}

/**
 * Get current validation status and results.
 */
export async function getValidationStatus({
  assetId,
  objectId,
  usePublicEndpoint,
}: {
  assetId: string | number;
  objectId: string | number;
  usePublicEndpoint?: boolean;
}): Promise<ValidationResult> {
  const urlParts = ["asset"];

  if (usePublicEndpoint) {
    urlParts.push("public");
  }

  urlParts.push(assetId.toString());
  urlParts.push("object");
  urlParts.push(objectId.toString());
  urlParts.push("validation-status");

  const url = buildApiUrl(...urlParts);
  const response = await axios.get(url);
  return response.data;
}

/**
 * Get list of supported file extensions for validation.
 */
export async function getSupportedExtensions(): Promise<string[]> {
  const url = buildApiUrl("asset", "validation", "supported-extensions");
  const response = await axios.get(url);
  return response.data;
}
