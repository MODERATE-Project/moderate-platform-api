import axios from "axios";
import { buildApiUrl } from "./utils";

export async function fetchPygwalkerHtml({ objectId }: { objectId: string }) {
  return axios.get(buildApiUrl("visualization", "object", objectId));
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
        (progressEvent.loaded * 100) / progressEvent.total
      );

      console.debug("Upload progress:", percentCompleted, "%");

      if (onProgress) {
        onProgress(percentCompleted);
      }
    },
  };

  return await axios.post(
    buildApiUrl("asset", assetId.toString(), "object"),
    data,
    config
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
