import { uploadObject } from "../api/assets";

export interface UploadProgress {
  fileName: string;
  progress: number;
}

/**
 * Upload multiple files sequentially to an asset with progress tracking
 * @param assetId - The ID of the asset to upload files to
 * @param files - Array of files to upload
 * @param onProgress - Optional callback to track upload progress
 */
export const uploadMultipleFiles = async (
  assetId: string,
  files: File[],
  onProgress?: (progress: UploadProgress) => void,
): Promise<void> => {
  for (const file of files) {
    onProgress?.({ fileName: file.name, progress: 0 });

    await uploadObject({
      assetId,
      file,
      onProgress: (progress) => {
        onProgress?.({ fileName: file.name, progress });
      },
    });
  }

  // Clear progress after all uploads complete
  onProgress?.({ fileName: "", progress: 0 });
};
