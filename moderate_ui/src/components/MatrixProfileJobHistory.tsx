import {
  Accordion,
  Badge,
  Button,
  Card,
  Code,
  Group,
  Skeleton,
  Stack,
  Text,
  ThemeIcon,
  Title,
} from "@mantine/core";
import {
  IconCheck,
  IconClock,
  IconDownload,
  IconExclamationCircle,
  IconHistory,
  IconHourglass,
  IconAlertTriangle,
  IconExternalLink,
  IconTerminal,
} from "@tabler/icons-react";
import React, { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { getJob, listJobs } from "../api/job";
import { WorkflowJob, WorkflowJobType } from "../api/types";
import { isJobAbandoned } from "../utils/jobs";
import { getAssetObjectById } from "../api/assets";
import { AssetObjectModel } from "../api/types";
import { routes } from "../utils/routes";

interface JobHistoryItemProps {
  job: WorkflowJob;
  onResume: (job: WorkflowJob) => void;
}

const JobHistoryItem: React.FC<JobHistoryItemProps> = ({ job, onResume }) => {
  const { t } = useTranslation();
  const isRunning = !job.finalised_at;
  const hasError = job.results?.error;
  const isAbandoned = isJobAbandoned(job);
  const [assetObject, setAssetObject] = useState<any>(null);
  const [isLoadingAsset, setIsLoadingAsset] = useState(false);
  const [showError, setShowError] = useState(false);

  useEffect(() => {
    if (!job.arguments?.uploaded_s3_object_id) {
      return;
    }

    setIsLoadingAsset(true);
    getAssetObjectById(job.arguments.uploaded_s3_object_id)
      .then((obj) => {
        setAssetObject(obj);
      })
      .catch((err) => {
        console.error("Failed to fetch asset object for job", err);
      })
      .finally(() => {
        setIsLoadingAsset(false);
      });
  }, [job]);

  const formatDate = (dateStr: string) => {
    return new Date(dateStr);
  };

  const createdDate = formatDate(job.created_at);
  const finalisedDate = job.finalised_at ? formatDate(job.finalised_at) : null;

  const getStatusBadge = (): React.ReactNode => {
    if (isAbandoned) {
      return (
        <Badge
          color="orange"
          variant="light"
          leftSection={<IconAlertTriangle size={12} />}
        >
          {t("Abandoned")}
        </Badge>
      );
    }
    if (isRunning) {
      return (
        <Badge
          color="blue"
          variant="light"
          leftSection={<IconHourglass size={12} />}
        >
          {t("Running")}
        </Badge>
      );
    }
    if (hasError) {
      return (
        <Badge color="red" variant="light">
          {t("Failed")}
        </Badge>
      );
    }
    return (
      <Badge color="green" variant="light">
        {t("Completed")}
      </Badge>
    );
  };

  const getStatusIcon = (): React.ReactNode => {
    if (isAbandoned) {
      return <IconAlertTriangle size="1rem" />;
    }
    if (isRunning) {
      return <IconHourglass size="1rem" />;
    }
    if (hasError) {
      return <IconExclamationCircle size="1rem" />;
    }
    return <IconCheck size="1rem" />;
  };

  const assetName = assetObject?.asset?.name || t("Loading...");
  const objectName = assetObject
    ? new AssetObjectModel(assetObject).humanName
    : t("Loading...");
  const analysisVariable = job.arguments?.analysis_variable || t("Unknown");
  const assetId = assetObject?.asset_id;
  const objectId = assetObject?.id;

  // Build link to asset object details page using the correct route helper
  const assetObjectDetailsUrl =
    assetId && objectId ? routes.assetObjectShow(assetId, objectId) : null;

  return (
    <Card withBorder p="md" radius="md">
      <Stack spacing="sm">
        {/* Header: Status Icon + Title + Badge */}
        <Group position="apart" align="flex-start" noWrap>
          <Group spacing="sm" noWrap style={{ flex: 1, minWidth: 0 }}>
            <ThemeIcon
              size="lg"
              variant="light"
              color={
                isAbandoned
                  ? "orange"
                  : isRunning
                    ? "blue"
                    : hasError
                      ? "red"
                      : "green"
              }
            >
              {getStatusIcon()}
            </ThemeIcon>
            <Stack spacing={4} style={{ flex: 1, minWidth: 0 }}>
              {isLoadingAsset ? (
                <>
                  <Skeleton height={20} width="70%" />
                  <Skeleton height={16} width="50%" mt={4} />
                </>
              ) : (
                <>
                  {/* Asset and Object Name */}
                  <Group spacing="xs" noWrap style={{ minWidth: 0 }}>
                    <Text
                      size="sm"
                      weight={600}
                      color="dark"
                      style={{
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                        flex: 1,
                      }}
                      title={assetName}
                    >
                      {assetName}
                    </Text>
                  </Group>
                  <Text
                    size="sm"
                    color="dimmed"
                    style={{
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                    title={objectName}
                  >
                    {objectName}
                  </Text>
                </>
              )}
            </Stack>
          </Group>
          {getStatusBadge()}
        </Group>

        {/* Analysis Variable */}
        {!isLoadingAsset && (
          <Group spacing="xs" pl={44}>
            <Text size="xs" color="dimmed" weight={500}>
              {t("Variable")}:
            </Text>
            <Badge size="sm" variant="dot" color="gray">
              {analysisVariable}
            </Badge>
          </Group>
        )}

        {/* Footer: Timestamp + Actions */}
        <Group position="apart" align="center" pl={44}>
          <Group spacing="xs" noWrap>
            <IconClock size="0.875rem" style={{ opacity: 0.5 }} />
            <Text size="xs" color="dimmed">
              {createdDate.toLocaleString()}
              {finalisedDate && ` → ${finalisedDate.toLocaleString()}`}
            </Text>
          </Group>

          <Group spacing="xs" noWrap>
            {assetObjectDetailsUrl && (
              <Button
                component="a"
                href={assetObjectDetailsUrl}
                target="_blank"
                size="xs"
                variant="light"
                color="blue"
                leftIcon={<IconExternalLink size={14} />}
                onClick={(e) => e.stopPropagation()}
              >
                {t("View Dataset")}
              </Button>
            )}
            {isRunning && !isAbandoned && (
              <Button
                size="xs"
                variant="light"
                color="blue"
                leftIcon={<IconHourglass size={14} />}
                onClick={(e) => {
                  e.stopPropagation();
                  onResume(job);
                }}
              >
                {t("View Progress")}
              </Button>
            )}
            {!isRunning && !hasError && job.extended_results?.download_url && (
              <Button
                size="xs"
                variant="light"
                color="green"
                leftIcon={<IconDownload size={14} />}
                component="a"
                href={job.extended_results.download_url}
                target="_blank"
                onClick={(e) => e.stopPropagation()}
              >
                {t("Get Results")}
              </Button>
            )}
            {!isRunning && hasError && (
              <Button
                size="xs"
                variant="light"
                color="red"
                leftIcon={<IconExclamationCircle size={14} />}
                onClick={(e) => {
                  e.stopPropagation();
                  setShowError(!showError);
                }}
              >
                {showError ? t("Hide Error") : t("View Error")}
              </Button>
            )}
          </Group>
        </Group>

        {/* Expandable error details section */}
        {showError && hasError && (
          <Card shadow="sm" p="sm" radius="md" withBorder ml={44}>
            <Group mb="xs" spacing="xs">
              <IconTerminal size="1em" />
              <Text weight={500} size="sm" color="red">
                {t("Error details")}
              </Text>
            </Group>
            <Code block style={{ fontSize: "0.75rem", whiteSpace: "pre-wrap" }}>
              {job.results?.error}
            </Code>
          </Card>
        )}
      </Stack>
    </Card>
  );
};

interface MatrixProfileJobHistoryProps {
  onResumeJob: (job: WorkflowJob) => void;
  refreshTrigger?: number;
}

export const MatrixProfileJobHistory: React.FC<
  MatrixProfileJobHistoryProps
> = ({ onResumeJob, refreshTrigger }) => {
  const { t } = useTranslation();
  const [jobs, setJobs] = useState<WorkflowJob[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchJobs = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const result = await listJobs({
        jobType: WorkflowJobType.MATRIX_PROFILE,
        limit: 10,
      });

      // Fetch extended results for completed jobs to get download URLs
      const jobsWithExtendedResults = await Promise.all(
        result.map(async (job) => {
          if (job.finalised_at && !job.results?.error) {
            try {
              return await getJob({
                jobId: job.id,
                withExtendedResults: true,
              });
            } catch {
              return job;
            }
          }
          return job;
        }),
      );

      setJobs(jobsWithExtendedResults);
    } catch (err) {
      console.error("Failed to fetch job history", err);
      setError(t("Failed to load job history"));
    } finally {
      setIsLoading(false);
    }
  }, [t]);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs, refreshTrigger]);

  const runningJobs = jobs.filter(
    (job) => !job.finalised_at && !isJobAbandoned(job),
  );
  const abandonedJobs = jobs.filter(
    (job) => !job.finalised_at && isJobAbandoned(job),
  );
  const completedJobs = jobs.filter((job) => job.finalised_at);

  // Auto-expand if there are running or abandoned jobs
  const defaultValue =
    runningJobs.length > 0 || abandonedJobs.length > 0 ? "history" : undefined;

  return (
    <Accordion
      variant="contained"
      defaultValue={defaultValue}
      chevronPosition="right"
    >
      <Accordion.Item value="history">
        <Accordion.Control icon={<IconHistory size="1rem" />}>
          <Group spacing="xs">
            <Text>{t("Recent Runs")}</Text>
            {runningJobs.length > 0 && (
              <Badge color="blue" size="sm" variant="filled">
                {runningJobs.length} {t("running")}
              </Badge>
            )}
            {abandonedJobs.length > 0 && (
              <Badge color="orange" size="sm" variant="filled">
                {abandonedJobs.length} {t("abandoned")}
              </Badge>
            )}
          </Group>
        </Accordion.Control>
        <Accordion.Panel>
          {isLoading ? (
            <Stack spacing="sm">
              <Skeleton height={60} />
              <Skeleton height={60} />
            </Stack>
          ) : error ? (
            <Text color="red" size="sm">
              {error}
            </Text>
          ) : jobs.length === 0 ? (
            <Text color="dimmed" size="sm" align="center" py="md">
              {t("No previous runs found")}
            </Text>
          ) : (
            <Stack spacing="sm">
              {runningJobs.length > 0 && (
                <>
                  <Title order={6} color="blue">
                    {t("In Progress")}
                  </Title>
                  <Text size="xs" color="dimmed" mb="xs">
                    {t(
                      "Jobs currently being processed. Click 'View Progress' to monitor.",
                    )}
                  </Text>
                  {runningJobs.map((job) => (
                    <JobHistoryItem
                      key={job.id}
                      job={job}
                      onResume={onResumeJob}
                    />
                  ))}
                </>
              )}
              {abandonedJobs.length > 0 && (
                <>
                  <Title order={6} color="orange">
                    {t("Abandoned")}
                  </Title>
                  <Text size="xs" color="dimmed" mb="xs">
                    {t(
                      "Jobs running for over 24 hours without completion. These may have encountered an issue.",
                    )}
                  </Text>
                  {abandonedJobs.map((job) => (
                    <JobHistoryItem
                      key={job.id}
                      job={job}
                      onResume={onResumeJob}
                    />
                  ))}
                </>
              )}
              {completedJobs.length > 0 && (
                <>
                  <Title
                    order={6}
                    color="dimmed"
                    mt={
                      runningJobs.length > 0 || abandonedJobs.length > 0
                        ? "sm"
                        : 0
                    }
                  >
                    {t("Completed")}
                  </Title>
                  <Text size="xs" color="dimmed" mb="xs">
                    {t(
                      "Finished jobs. Download results or view details for successfully completed runs.",
                    )}
                  </Text>
                  {completedJobs.slice(0, 5).map((job) => (
                    <JobHistoryItem
                      key={job.id}
                      job={job}
                      onResume={onResumeJob}
                    />
                  ))}
                </>
              )}
            </Stack>
          )}
        </Accordion.Panel>
      </Accordion.Item>
    </Accordion>
  );
};
