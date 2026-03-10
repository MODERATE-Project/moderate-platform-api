import { Alert, Badge, Group, Text, Tooltip } from "@mantine/core";
import { useTranslate } from "@refinedev/core";
import {
  IconAlertTriangle,
  IconCheck,
  IconLoader,
  IconPlugConnected,
  IconPlugConnectedX,
} from "@tabler/icons-react";
import React from "react";
import { ReporterStatus } from "../../api/validation";

interface ReporterStatusIndicatorProps {
  reporterStatus: ReporterStatus | null;
  compact?: boolean;
}

/**
 * Displays Data Quality service availability and impact on validation.
 */
export const ReporterStatusIndicator: React.FC<
  ReporterStatusIndicatorProps
> = ({ reporterStatus, compact = false }) => {
  const t = useTranslate();

  if (!reporterStatus) {
    return null;
  }

  const { state, kafka_connected, last_error, validation_pending_messages } =
    reporterStatus;

  if (state === "healthy") {
    return (
      <Tooltip
        label={t(
          "reporter.healthyTooltip",
          "Data Quality service is available and validation can run now.",
        )}
      >
        <Badge
          color="green"
          variant="light"
          size={compact ? "sm" : "md"}
          leftSection={<IconCheck size={12} />}
        >
          {t("reporter.healthy", "Validation ready")}
        </Badge>
      </Tooltip>
    );
  }

  if (state === "starting") {
    return (
      <Tooltip
        label={t(
          "reporter.startingTooltip",
          "Data Quality service is starting up. Validation requests may take a moment.",
        )}
      >
        <Badge
          color="blue"
          variant="light"
          size={compact ? "sm" : "md"}
          leftSection={<IconLoader size={12} />}
        >
          {t("reporter.starting", "Validation starting")}
        </Badge>
      </Tooltip>
    );
  }

  if (state === "catching_up") {
    const pendingLabel =
      validation_pending_messages != null
        ? ` (${validation_pending_messages} pending)`
        : "";

    return (
      <Tooltip
        label={t(
          "reporter.catchingUpTooltip",
          "Data Quality service is catching up on queued work. New validation requests may take longer.",
        )}
      >
        <Badge
          color="yellow"
          variant="light"
          size={compact ? "sm" : "md"}
          leftSection={<IconLoader size={12} />}
        >
          {t("reporter.catchingUp", "Validation delayed")}
          {pendingLabel}
        </Badge>
      </Tooltip>
    );
  }

  if (state === "stale") {
    if (compact) {
      return (
        <Tooltip
          label={t(
            "reporter.staleTooltip",
            "Data Quality service has not processed recent work. Validation results may be delayed.",
          )}
        >
          <Badge
            color="orange"
            variant="light"
            size="sm"
            leftSection={<IconAlertTriangle size={12} />}
          >
            {t("reporter.stale", "Validation delayed")}
          </Badge>
        </Tooltip>
      );
    }

    return (
      <Alert
        icon={<IconAlertTriangle size={16} />}
        color="orange"
        title={t("reporter.staleTitle", "Validation delayed")}
      >
        <Text size="sm">
          {t(
            "reporter.staleMessage",
            "The Data Quality service has not processed recent work. Validation results may be delayed.",
          )}
        </Text>
      </Alert>
    );
  }

  // Error state
  if (compact) {
    return (
      <Tooltip
        label={
          last_error ||
          t(
            "reporter.errorTooltip",
            "Data Quality service is currently unavailable. Starting a new validation may fail.",
          )
        }
      >
        <Badge
          color="red"
          variant="light"
          size="sm"
          leftSection={
            kafka_connected ? (
              <IconPlugConnected size={12} />
            ) : (
              <IconPlugConnectedX size={12} />
            )
          }
        >
          {t("reporter.error", "Validation unavailable")}
        </Badge>
      </Tooltip>
    );
  }

  return (
    <Alert
      icon={<IconAlertTriangle size={16} />}
      color="red"
      title={t("reporter.errorTitle", "Validation unavailable")}
    >
      <Text size="sm" mb={4}>
        {t(
          "reporter.errorMessage",
          "The Data Quality service is currently unavailable. Starting a new validation may fail.",
        )}
      </Text>
      <Group spacing="xs" mb={4}>
        {kafka_connected ? (
          <Badge color="green" size="xs" variant="light">
            {t("reporter.kafkaConnected", "Kafka Connected")}
          </Badge>
        ) : (
          <Badge color="red" size="xs" variant="light">
            {t("reporter.kafkaDisconnected", "Kafka Disconnected")}
          </Badge>
        )}
      </Group>
      {last_error && (
        <Text size="sm" color="dimmed">
          {last_error}
        </Text>
      )}
    </Alert>
  );
};
