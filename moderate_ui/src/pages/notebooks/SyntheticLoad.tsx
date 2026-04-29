import { Alert, Button, Code, Group, Stack, Text } from "@mantine/core";
import { useClipboard } from "@mantine/hooks";
import { IconClipboard, IconInfoCircle } from "@tabler/icons-react";
import React, { useCallback, useState } from "react";
import { Link } from "react-router-dom";
import { downloadAssetObjects } from "../../api/assets";
import {
  AssetObjectPicker,
  DatasetSelectOption,
} from "../../components/AssetObjectPicker";
import { NotebookContainer } from "../../components/NotebookContainer";

const SYNTHETIC_LOAD_URL_EXPIRATION_SECS = 3600;

export const NotebookSyntheticLoad: React.FC = () => {
  const clipboard = useClipboard({ timeout: 1500 });
  const [selectedDataset, setSelectedDataset] = useState<
    DatasetSelectOption | undefined
  >(undefined);
  const [isCopyingUrl, setIsCopyingUrl] = useState(false);
  const [copyError, setCopyError] = useState<string | undefined>(undefined);

  const onDatasetSelect = useCallback(
    (dataset: DatasetSelectOption | undefined) => {
      setSelectedDataset(dataset);
      setCopyError(undefined);
    },
    [],
  );

  const copySelectedDatasetUrl = useCallback(async () => {
    if (!selectedDataset) {
      return;
    }

    setIsCopyingUrl(true);
    setCopyError(undefined);

    try {
      const downloadItems = await downloadAssetObjects({
        assetId: selectedDataset.asset.data.id,
        objectId: selectedDataset.assetObject.data.id,
        expirationSecs: SYNTHETIC_LOAD_URL_EXPIRATION_SECS,
      });

      const selectedItem = downloadItems.find(
        (item) => item.key === selectedDataset.assetObject.data.key,
      );

      if (!selectedItem) {
        throw new Error("Selected dataset was not returned by the API.");
      }

      clipboard.copy(selectedItem.download_url);
    } catch (error) {
      console.error(error);
      setCopyError(
        "Could not prepare a download URL for this dataset. Check that you have download access and try again.",
      );
    } finally {
      setIsCopyingUrl(false);
    }
  }, [clipboard, selectedDataset]);

  return (
    <NotebookContainer
      notebookSrc="/notebook-synthetic-load"
      title={<Text fz="lg">Synthetic load model</Text>}
      description={
        <>
          <Text mt="sm" mb="sm" size="sm" color="dimmed">
            This hosted Marimo notebook is interactive for the current session:
            you can adjust form values and run the workflow, but source-code
            edits are not saved through the platform UI.
          </Text>
          <Text mt="sm" mb="sm" size="sm" color="dimmed">
            Please see the original repository for further details:{" "}
            <Link
              target="_blank"
              to="https://github.com/MODERATE-Project/Synthetic-Load-Profiles"
            >
              MODERATE-Project/Synthetic-Load-Profiles
            </Link>
          </Text>
          <Stack spacing="xs" mb="md">
            <Alert
              icon={<IconInfoCircle size="1rem" />}
              color="blue"
              variant="light"
            >
              Search the catalogue for a CSV or ZIP test dataset, copy its
              temporary download URL, then paste it into the notebook&apos;s
              Test Data field before clicking <Code>Load Files</Code>. The
              default model and training-data URLs can stay unchanged.
            </Alert>
            <AssetObjectPicker
              fileFormat={["csv", "zip"]}
              onSelect={onDatasetSelect}
              showFormatInfo={false}
            />
            <Group spacing="xs">
              <Button
                leftIcon={<IconClipboard size="1em" />}
                disabled={!selectedDataset}
                loading={isCopyingUrl}
                onClick={copySelectedDatasetUrl}
              >
                {clipboard.copied
                  ? "Copied test data URL"
                  : "Copy test data URL"}
              </Button>
              {selectedDataset && (
                <Text size="sm" color="dimmed">
                  Selected: {selectedDataset.assetObject.humanName}
                </Text>
              )}
            </Group>
            {copyError && (
              <Alert color="red" variant="light">
                {copyError}
              </Alert>
            )}
          </Stack>
        </>
      }
    />
  );
};
