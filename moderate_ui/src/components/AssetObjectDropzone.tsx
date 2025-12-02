import {
  Group,
  Loader,
  LoadingOverlay,
  Progress,
  Stack,
  Text,
} from "@mantine/core";
import { Dropzone } from "@mantine/dropzone";
import { useNotification, useTranslate } from "@refinedev/core";
import { IconFile } from "@tabler/icons";
import { IconUpload, IconX } from "@tabler/icons-react";
import React, { useState } from "react";
import { AssetModel } from "../api/types";
import { catchErrorAndShow } from "../utils";
import { uploadMultipleFiles, UploadProgress } from "../utils/upload";

export const AssetObjectDropzone: React.FC<{
  asset: AssetModel;
  maxSize?: number;
  maxFiles?: number;
  onUploaded?: () => void;
}> = ({ asset, maxSize = 50 * 1024 ** 2, maxFiles = 20, onUploaded }) => {
  const t = useTranslate();
  const [isLoading, setIsLoading] = useState(false);

  const [uploadingFile, setUploadingFile] = useState<
    UploadProgress | undefined
  >(undefined);

  const { open } = useNotification();

  const validExts = ["csv", "json", "parquet"];

  return (
    <Dropzone
      onDrop={(filesWithPath) => {
        if (filesWithPath.length + asset.getObjects().length > maxFiles) {
          open &&
            open({
              description: t(
                "asset.dropFiles.tooManyFiles",
                "Too many dataset files",
              ),
              message: t(
                "asset.dropFiles.tooManyFilesDescription",
                "Maximum file limit reached for this asset",
              ),
              type: "error",
            });

          return;
        }

        setIsLoading(true);

        uploadMultipleFiles(
          String(asset.data.id),
          filesWithPath,
          (progress) => {
            setUploadingFile(progress);
          },
        )
          .catch(
            (err) =>
              open &&
              catchErrorAndShow(
                open,
                t("asset.dropFiles.uploadError", "Error uploading file"),
                err,
              ),
          )
          .then(() => {
            setIsLoading(false);
            setUploadingFile(undefined);
            onUploaded && onUploaded();
          });
      }}
      onReject={(fileRejections) => {
        const errMsgs = fileRejections
          .flatMap((fr) => fr.errors)
          .flatMap((error) => error.message);

        open &&
          open({
            description: t(
              "asset.dropFiles.rejectedFile",
              "Unable to upload file",
            ),
            message: errMsgs && errMsgs.length > 0 ? errMsgs[0] : "",
            type: "error",
          });
      }}
      validator={(file: File) => {
        if (file.name) {
          const ext = file.name.split(".").pop();
          const isValidExt = ext && validExts.includes(ext);

          if (!isValidExt) {
            return {
              code: "invalid-extension",
              message: `Invalid file extension. Supported extensions: ${validExts.join(
                ", ",
              )}`,
            };
          }
        }

        return null;
      }}
      maxSize={maxSize}
      loading={isLoading}
    >
      <LoadingOverlay
        visible={isLoading}
        overlayBlur={5}
        loader={
          <Group>
            <Loader />
            {uploadingFile && (
              <Stack spacing="xs">
                <Text color="dimmed">
                  {t("asset.dropFiles.uploading", "Uploading")}{" "}
                  <code>{uploadingFile.fileName}</code>
                </Text>
                <Progress
                  value={uploadingFile.progress}
                  animate
                  label={`${uploadingFile.progress}%`}
                  size="xl"
                />
              </Stack>
            )}
          </Group>
        }
      />
      <Group position="center" style={{ pointerEvents: "none" }}>
        <Dropzone.Accept>
          <IconUpload size="3em" stroke={1.5} />
        </Dropzone.Accept>
        <Dropzone.Reject>
          <IconX size="3em" stroke={1.5} />
        </Dropzone.Reject>
        <Dropzone.Idle>
          <IconFile size="3em" stroke={1.5} />
        </Dropzone.Idle>
        <div>
          <Text size="xl" inline>
            {t("asset.dropFiles.title", "Drop files here or click to select")}
          </Text>
          <Text size="sm" color="dimmed" inline mt={7}>
            {t(
              "asset.dropFiles.description",
              "The dataset files will be uploaded to the MODERATE platform and attached to the current asset",
            )}
          </Text>
        </div>
      </Group>
    </Dropzone>
  );
};
