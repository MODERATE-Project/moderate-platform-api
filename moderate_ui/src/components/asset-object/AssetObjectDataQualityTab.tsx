import {
  Alert,
  Badge,
  Button,
  Group,
  Loader,
  Paper,
  Skeleton,
  Stack,
  Text,
  ThemeIcon,
  Title,
} from "@mantine/core";
import { useNotification, useTranslate } from "@refinedev/core";
import {
  IconAlertTriangle,
  IconCheck,
  IconFileOff,
  IconRefresh,
  IconShieldCheck,
  IconX,
} from "@tabler/icons-react";
import React, { useEffect, useState } from "react";
import {
  getAssetObjectRowCount,
  getSupportedExtensions,
} from "../../api/validation";
import { useAssetObjectValidation } from "../../hooks";
import { catchErrorAndShow } from "../../utils";
import { ValidationResultsTable } from "./ValidationResultsTable";

interface AssetObjectDataQualityTabProps {
  assetId: number | string;
  objectId: number | string;
  fileExtension: string;
  usePublicEndpoint?: boolean;
}

/**
 * Get badge color and variant based on overall pass rate
 */
function getOverallStatusBadge(passRate: number): {
  color: string;
  label: string;
} {
  if (passRate >= 99) return { color: "green", label: "Excellent" };
  if (passRate >= 95) return { color: "teal", label: "Good" };
  if (passRate >= 80) return { color: "yellow", label: "Fair" };
  return { color: "red", label: "Poor" };
}

/**
 * Tab component for displaying data quality validation status and results
 *
 * States:
 * - Loading: Initial fetch in progress
 * - Unsupported: File type not supported for validation
 * - Not Started: No validation has been run yet
 * - In Progress: Validation is running (with polling)
 * - Complete: Validation finished successfully
 * - Failed: Validation encountered an error
 */
export const AssetObjectDataQualityTab: React.FC<
  AssetObjectDataQualityTabProps
> = ({ assetId, objectId, fileExtension, usePublicEndpoint }) => {
  const t = useTranslate();
  const { open } = useNotification();
  const [supportedExtensions, setSupportedExtensions] = useState<string[]>([]);
  const [supportedExtensionsLoadFailed, setSupportedExtensionsLoadFailed] =
    useState(false);
  const [rowCount, setRowCount] = useState<number | null>(null);

  const { status, isLoading, isPolling, startValidation, refreshStatus } =
    useAssetObjectValidation({
      assetId,
      objectId,
      usePublicEndpoint,
    });

  // Fetch supported extensions and row count on mount
  useEffect(() => {
    getSupportedExtensions()
      .then((extensions) => {
        setSupportedExtensions(extensions);
        setSupportedExtensionsLoadFailed(false);
      })
      .catch((err) => {
        setSupportedExtensions([]);
        setSupportedExtensionsLoadFailed(true);
        catchErrorAndShow(open, undefined, err);
      });

    getAssetObjectRowCount({ assetId, objectId })
      .then((res) => setRowCount(res.row_count))
      .catch((err) => {
        catchErrorAndShow(open, undefined, err);
      });
  }, [assetId, objectId, open]);

  // Check if file type is supported
  const isSupported = supportedExtensions.includes(
    fileExtension?.toLowerCase() || "",
  );
  const hasRunningOrCompletedValidation =
    status?.status === "in_progress" || status?.status === "complete";
  const disableValidationActions =
    supportedExtensionsLoadFailed && !hasRunningOrCompletedValidation;

  // Loading state
  if (isLoading && !status) {
    return (
      <Stack spacing="md">
        <Skeleton height={20} />
        <Skeleton height={20} />
        <Skeleton height={100} />
      </Stack>
    );
  }

  // Unsupported file type
  if (
    status?.status === "unsupported" ||
    (!supportedExtensionsLoadFailed && !isSupported)
  ) {
    return (
      <Alert
        icon={<IconFileOff size={24} />}
        title={t("validation.unsupportedTitle", "File Type Not Supported")}
        color="gray"
      >
        <Text size="sm">
          {t(
            "validation.unsupportedMessage",
            "Data quality validation is only available for tabular data formats.",
          )}
          {fileExtension && (
            <Text span ml={4}>
              {t(
                "validation.currentFormatUnuspported",
                `The current file format (.${fileExtension}) is not supported.`,
              )}
            </Text>
          )}
        </Text>
        <Text size="sm" mt="xs" color="dimmed">
          {t("validation.supportedFormats", "Supported formats:")}{" "}
          {supportedExtensions.join(", ")}
        </Text>
      </Alert>
    );
  }

  // Not started state
  if (status?.status === "not_started") {
    return (
      <Paper p="lg" withBorder>
        <Stack align="center" spacing="md">
          <ThemeIcon size={60} radius="xl" variant="light" color="blue">
            <IconShieldCheck size={32} />
          </ThemeIcon>
          <Title order={4}>
            {t("validation.notStartedTitle", "Data Quality Validation")}
          </Title>
          <Text color="dimmed" align="center" sx={{ maxWidth: 400 }}>
            {t(
              "validation.notStartedMessage",
              "Run validation to check your data for missing values, data type consistency, and other quality metrics.",
            )}
          </Text>
          {disableValidationActions && (
            <Alert
              icon={<IconAlertTriangle size={16} />}
              color="yellow"
              title={t(
                "validation.extensionsUnavailableTitle",
                "Validation temporarily unavailable",
              )}
              w="100%"
            >
              {t(
                "validation.extensionsUnavailableMessage",
                "Supported file formats could not be loaded. Please refresh and try again.",
              )}
            </Alert>
          )}
          <Button
            onClick={startValidation}
            loading={isLoading}
            disabled={disableValidationActions}
            leftIcon={<IconShieldCheck size={18} />}
            size="md"
          >
            {t("validation.startButton", "Validate Now")}
          </Button>
        </Stack>
      </Paper>
    );
  }

  // Results state (in progress or complete)
  if (status?.status === "in_progress" || status?.status === "complete") {
    const statusBadge = getOverallStatusBadge(status.overall_pass_rate);
    const lastRequestedDate = status.last_requested_at
      ? new Date(status.last_requested_at).toLocaleString()
      : undefined;

    return (
      <Stack spacing="md">
        {status.is_mock && (
          <Alert
            icon={<IconAlertTriangle size={24} />}
            title={t("validation.mockTitle", "Demonstration Mode")}
            color="orange"
          >
            {t(
              "validation.mockMessage",
              "This validation is running in demonstration mode using simulated data. The results shown are for illustration purposes only.",
            )}
          </Alert>
        )}

        <Paper p="md" withBorder>
          <Group position="apart">
            <Group spacing="md">
              <ThemeIcon
                size={48}
                radius="xl"
                color={statusBadge.color}
                variant="light"
              >
                {status.overall_pass_rate >= 95 ? (
                  <IconCheck size={24} />
                ) : status.overall_pass_rate >= 80 ? (
                  <IconAlertTriangle size={24} />
                ) : (
                  <IconX size={24} />
                )}
              </ThemeIcon>
              <Stack spacing={4}>
                <Group spacing="sm">
                  <Title order={4}>
                    {t("validation.resultsTitle", "Validation Results")}
                  </Title>
                  <Badge color={statusBadge.color} variant="filled">
                    {statusBadge.label}
                  </Badge>
                  {isPolling && (
                    <Badge
                      color="blue"
                      variant="light"
                      leftSection={<Loader size={10} />}
                    >
                      {t("validation.updating", "Updating")}
                    </Badge>
                  )}
                </Group>

                <Group spacing="xl">
                  <Text size="sm" color="dimmed">
                    {t("validation.lastRequested", "Last requested:")}
                    <Text span weight={500} ml={4}>
                      {lastRequestedDate || "-"}
                    </Text>
                  </Text>

                  <Text size="sm" color="dimmed">
                    {t("validation.overallPassRate", "Pass rate:")}
                    <Text span weight={600} ml={4}>
                      {status.overall_pass_rate.toFixed(2)}%
                    </Text>
                  </Text>
                </Group>
              </Stack>
            </Group>

            <Button
              variant="subtle"
              leftIcon={<IconRefresh size={18} />}
              onClick={refreshStatus}
              loading={isLoading}
            >
              {t("validation.refreshButton", "Refresh")}
            </Button>
          </Group>

          {/* Stats row */}
          <Group mt="xl" spacing="xl" position="apart">
            <Group spacing="xl">
              <Stack spacing={0}>
                <Text size="xs" color="dimmed" transform="uppercase">
                  {t("validation.totalValid", "Valid")}
                </Text>
                <Text size="lg" weight={600} color="green">
                  {status.total_valid.toLocaleString()}
                </Text>
              </Stack>
              <Stack spacing={0}>
                <Text size="xs" color="dimmed" transform="uppercase">
                  {t("validation.totalFail", "Failed")}
                </Text>
                <Text
                  size="lg"
                  weight={600}
                  color={status.total_fail > 0 ? "red" : "dimmed"}
                >
                  {status.total_fail.toLocaleString()}
                </Text>
              </Stack>
              <Stack spacing={0}>
                <Text size="xs" color="dimmed" transform="uppercase">
                  {t("validation.rulesChecked", "Rules Checked")}
                </Text>
                <Text size="lg" weight={600}>
                  {status.entries.length}
                </Text>
              </Stack>
            </Group>

            <Group spacing="xl" align="flex-end">
              {rowCount !== null && (
                <Stack spacing={0} align="flex-end">
                  <Text size="xs" color="dimmed" transform="uppercase">
                    {t("validation.totalRows", "Total Rows")}
                  </Text>
                  <Text size="lg" weight={600}>
                    {rowCount.toLocaleString()}
                  </Text>
                </Stack>
              )}
              {status.processed_rows != null && (
                <Stack spacing={0} align="flex-end">
                  <Text size="xs" color="dimmed" transform="uppercase">
                    {t("validation.processedRows", "Processed")}
                  </Text>
                  <Text size="lg" weight={600}>
                    {status.processed_rows.toLocaleString()}
                  </Text>
                </Stack>
              )}
            </Group>
          </Group>
        </Paper>

        {/* Results table */}
        <Stack spacing="sm">
          <Title order={5}>
            {t("validation.detailedResults", "Detailed Results")}
          </Title>
          <ValidationResultsTable entries={status.entries} />
        </Stack>

        {/* Re-validate button */}
        <Group position="center" mt="md">
          <Button
            variant="light"
            leftIcon={<IconShieldCheck size={18} />}
            onClick={startValidation}
            loading={isLoading}
            disabled={isPolling || isLoading}
          >
            {t("validation.revalidateButton", "Re-validate")}
          </Button>
        </Group>
      </Stack>
    );
  }

  // Failed state
  if (status?.status === "failed") {
    return (
      <Alert
        icon={<IconAlertTriangle size={24} />}
        title={t("validation.failedTitle", "Validation Failed")}
        color="red"
      >
        <Text size="sm" mb="md">
          {status.error_message ||
            t(
              "validation.failedMessage",
              "An error occurred during validation.",
            )}
        </Text>
        <Button
          onClick={startValidation}
          loading={isLoading}
          disabled={disableValidationActions}
          variant="light"
          color="red"
          leftIcon={<IconRefresh size={18} />}
        >
          {t("validation.retryButton", "Retry Validation")}
        </Button>
      </Alert>
    );
  }

  // Fallback (shouldn't reach here)
  return (
    <Alert color="gray">
      {t("validation.unknownState", "Unknown validation state")}
    </Alert>
  );
};
