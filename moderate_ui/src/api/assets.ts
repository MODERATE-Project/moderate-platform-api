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
