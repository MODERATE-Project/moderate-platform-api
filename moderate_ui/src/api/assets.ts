import axios from "axios";
import { Asset, UploadedS3Object } from "./types";
import { buildApiUrl } from "./utils";

export async function fetchPygwalkerHtml({ objectId }: { objectId: string }) {
  return axios.get(buildApiUrl("visualization", "object", objectId));
}

interface AssetObjectWithAssetId {
  id: number;
  asset_id: number;
  key: string;
  name: string | null;
  description: string | null;
  created_at: string;
  series_id: string | null;
  sha256_hash: string;
  proof_id: string | null;
  meta: { [k: string]: unknown } | null;
  tags: { [k: string]: unknown } | null;
}

export async function getAssetObjectById(
  objectId: number | string,
): Promise<UploadedS3Object | undefined> {
  // Step 1: Fetch the object using filters
  const params = {
    filters: JSON.stringify([{ field: "id", operator: "eq", value: objectId }]),
    limit: "1",
  };
  const objectResponse = await axios.get(buildApiUrl("asset", "object"), {
    params,
  });
  const objects = objectResponse.data as AssetObjectWithAssetId[];

  if (!objects || objects.length === 0) {
    return undefined;
  }

  const obj = objects[0];

  // Step 2: Fetch the parent asset using asset_id
  const assetResponse = await axios.get(
    buildApiUrl("asset", obj.asset_id.toString()),
  );
  const asset = assetResponse.data as Asset;

  // Step 3: Combine into UploadedS3Object format
  return {
    ...obj,
    asset: asset,
  };
}

export async function uploadObject({
  assetId,
  file,
  onProgress,
}: {
  assetId: string | number;
  file: File;
  onProgress?: (progress: number) => void;
}): Promise<{ [k: string]: any }> {
  const data = new FormData();
  data.append("obj", file);

  const config = {
    onUploadProgress: function (progressEvent: { [k: string]: any }) {
      const percentCompleted = Math.round(
        (progressEvent.loaded * 100) / progressEvent.total,
      );

      if (onProgress) {
        onProgress(percentCompleted);
      }
    },
  };

  return await axios.post(
    buildApiUrl("asset", assetId.toString(), "object"),
    data,
    config,
  );
}

export async function searchAssets({
  searchQuery,
  excludeMine,
  usePublicEndpoint,
}: {
  searchQuery: string;
  excludeMine?: boolean;
  usePublicEndpoint?: boolean;
}): Promise<{ [k: string]: any }[]> {
  const urlParts = ["asset"];

  if (usePublicEndpoint) {
    urlParts.push("public");
  }

  urlParts.push("search");
  const url = buildApiUrl(...urlParts);

  const params = {};

  if (searchQuery) {
    Object.assign(params, { query: searchQuery });
  }

  if (excludeMine) {
    Object.assign(params, { exclude_mine: excludeMine });
  }

  const response = await axios.get(url, { params });

  return response.data;
}

export async function searchAssetObjects({
  searchQuery,
  excludeMine,
  sort,
  limit,
  offset,
  fileFormat,
  dateFilter,
  usePublicEndpoint,
}: {
  searchQuery: string;
  excludeMine?: boolean;
  sort?: string;
  limit?: number;
  offset?: number;
  fileFormat?: string | string[];
  dateFilter?: "always" | "last_week" | "last_month";
  usePublicEndpoint?: boolean;
}): Promise<{ [k: string]: any }[]> {
  const urlParts = ["asset"];

  if (usePublicEndpoint) {
    urlParts.push("public");
  }

  urlParts.push("objects");
  urlParts.push("search");
  const url = buildApiUrl(...urlParts);

  const params = {};

  if (searchQuery) {
    Object.assign(params, { query: searchQuery });
  }

  if (excludeMine) {
    Object.assign(params, { exclude_mine: excludeMine });
  }

  if (sort) {
    Object.assign(params, { sort: sort });
  }

  if (limit !== undefined) {
    Object.assign(params, { limit: limit });
  }

  if (offset !== undefined) {
    Object.assign(params, { offset: offset });
  }

  if (fileFormat) {
    // Convert array to comma-separated string, or use string as-is
    const formatStr = Array.isArray(fileFormat)
      ? fileFormat.join(",")
      : fileFormat;
    Object.assign(params, { file_format: formatStr });
  }

  if (dateFilter && dateFilter !== "always") {
    const now = new Date();
    let dateFrom: Date;

    if (dateFilter === "last_week") {
      dateFrom = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    } else if (dateFilter === "last_month") {
      dateFrom = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
    } else {
      dateFrom = now; // fallback (shouldn't happen)
    }

    // Convert to ISO string format
    Object.assign(params, { date_from: dateFrom.toISOString() });
  }

  const response = await axios.get(url, { params });

  return response.data;
}

export interface DownloadAssetObjectItem {
  key: string;
  download_url: string;
}

export async function downloadAssetObjects({
  assetId,
  usePublicEndpoint,
}: {
  assetId: string | number;
  usePublicEndpoint?: boolean;
}): Promise<DownloadAssetObjectItem[]> {
  const urlParts = ["asset"];

  if (usePublicEndpoint) {
    urlParts.push("public");
  }

  urlParts.push(assetId.toString());
  urlParts.push("download-urls");
  const url = buildApiUrl(...urlParts);

  const response = await axios.get(url);

  return response.data;
}

export interface AssetObjectIntegrityResponse {
  valid: boolean;
  reason: string;
}

export async function checkAssetObjectIntegrity({
  objectKeyOrId,
}: {
  objectKeyOrId: string | number;
}): Promise<AssetObjectIntegrityResponse> {
  const url = buildApiUrl("asset", "proof", "integrity");

  const params = {
    object_key_or_id: objectKeyOrId,
  };

  const response = await axios.get(url, { params });

  return response.data;
}

export interface AssetObjectProfile {
  name: string;
  fullyQualifiedName: string;
  updatedAt: string;
  columns: { [k: string]: any }[];
  profile: { [k: string]: any };
  fileFormat: string;
}

export interface AssetObjectProfileResult {
  profile?: AssetObjectProfile;
  reason?: string;
}

export async function getAssetObjectProfile({
  objectId,
}: {
  objectId: number | string;
}): Promise<AssetObjectProfileResult> {
  const url = buildApiUrl("asset", "object", objectId.toString(), "profile");
  const response = await axios.get(url);
  return response.data;
}

export async function updateAssetObject({
  assetId,
  objectId,
  updateBody,
}: {
  assetId: string | number;
  objectId: string | number;
  updateBody: { [k: string]: string | { [k: string]: any } | null };
}): Promise<{ [k: string]: any }> {
  const url = buildApiUrl(
    "asset",
    assetId.toString(),
    "object",
    objectId.toString(),
  );

  const response = await axios.patch(url, updateBody);
  return response.data;
}

export async function deleteAssetObject({
  assetId,
  objectId,
}: {
  assetId: string | number;
  objectId: string | number;
}): Promise<{ [k: string]: any }> {
  const url = buildApiUrl(
    "asset",
    assetId.toString(),
    "object",
    objectId.toString(),
  );

  const response = await axios.delete(url);
  return response.data;
}

export interface AssetObjectColumnsResponse {
  columns: string[];
}

export async function getAssetObjectColumns({
  assetId,
  objectId,
}: {
  assetId: string | number;
  objectId: string | number;
}): Promise<AssetObjectColumnsResponse> {
  const url = buildApiUrl(
    "asset",
    assetId.toString(),
    "object",
    objectId.toString(),
    "columns",
  );
  const response = await axios.get(url);
  return response.data;
}
