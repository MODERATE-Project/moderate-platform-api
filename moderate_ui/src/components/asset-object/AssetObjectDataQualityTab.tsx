import {
  Alert,
  Badge,
  Button,
  Group,
  Loader,
  Paper,
  Progress,
  Skeleton,
  Stack,
  Text,
  ThemeIcon,
  Title,
} from "@mantine/core";
import { useTranslate } from "@refinedev/core";
import {
  IconAlertTriangle,
  IconCheck,
  IconFileOff,
  IconRefresh,
  IconShieldCheck,
  IconX,
} from "@tabler/icons-react";
import React, { useEffect, useState } from "react";
import { getSupportedExtensions } from "../../api/validation";
import { useAssetObjectValidation } from "../../hooks";
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
  const [supportedExtensions, setSupportedExtensions] = useState<string[]>([]);

  const { status, isLoading, isPolling, startValidation, refreshStatus } =
    useAssetObjectValidation({
      assetId,
      objectId,
      usePublicEndpoint,
    });

  // Fetch supported extensions on mount
  useEffect(() => {
    getSupportedExtensions()
      .then(setSupportedExtensions)
      .catch(() => {
        // Default supported extensions if API fails
        setSupportedExtensions(["csv", "json", "parquet"]);
      });
  }, []);

  // Check if file type is supported
  const isSupported = supportedExtensions.includes(
    fileExtension?.toLowerCase() || "",
  );

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
  if (!isSupported || status?.status === "unsupported") {
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
          <Button
            onClick={startValidation}
            loading={isLoading}
            leftIcon={<IconShieldCheck size={18} />}
            size="md"
          >
            {t("validation.startButton", "Validate Now")}
          </Button>
        </Stack>
      </Paper>
    );
  }

  // In progress state
  if (status?.status === "in_progress") {
    return (
      <Stack spacing="md">
        <Paper p="md" withBorder>
          <Group position="apart" mb="sm">
            <Group spacing="sm">
              <Loader size="sm" />
              <Text weight={500}>
                {t("validation.inProgressTitle", "Validation in Progress")}
              </Text>
            </Group>
            <Badge
              color="blue"
              variant="light"
              leftSection={<Loader size={12} />}
            >
              {isPolling
                ? t("validation.polling", "Updating...")
                : t("validation.processing", "Processing")}
            </Badge>
          </Group>

          {status.processed_rows !== undefined && (
            <Stack spacing="xs">
              <Progress value={100} animate color="blue" />
              <Text size="sm" color="dimmed">
                {t("validation.processedRows", "Processed rows:")}{" "}
                {status.processed_rows?.toLocaleString() || 0}
              </Text>
            </Stack>
          )}
        </Paper>

        {/* Show partial results while processing */}
        {status.entries.length > 0 && (
          <Stack spacing="sm">
            <Text size="sm" color="dimmed">
              {t(
                "validation.partialResults",
                "Partial results (updating live):",
              )}
            </Text>
            <ValidationResultsTable entries={status.entries} />
          </Stack>
        )}
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
          variant="light"
          color="red"
          leftIcon={<IconRefresh size={18} />}
        >
          {t("validation.retryButton", "Retry Validation")}
        </Button>
      </Alert>
    );
  }

  // Complete state
  if (status?.status === "complete") {
    const statusBadge = getOverallStatusBadge(status.overall_pass_rate);

    return (
      <Stack spacing="md">
        {/* Summary header */}
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
                    {t("validation.completeTitle", "Validation Complete")}
                  </Title>
                  <Badge color={statusBadge.color} variant="filled">
                    {statusBadge.label}
                  </Badge>
                </Group>
                <Text size="sm" color="dimmed">
                  {t("validation.overallPassRate", "Overall pass rate:")}
                  <Text span weight={600} ml={4}>
                    {status.overall_pass_rate.toFixed(2)}%
                  </Text>
                </Text>
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
          <Group mt="md" spacing="xl">
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
          >
            {t("validation.revalidateButton", "Re-validate")}
          </Button>
        </Group>
      </Stack>
    );
  }

  // Fallback (shouldn't reach here)
  return (
    <Alert color="gray">
      {t("validation.unknownState", "Unknown validation state")}
    </Alert>
  );
};
