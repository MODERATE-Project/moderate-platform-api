import {
  Accordion,
  ActionIcon,
  Badge,
  Box,
  Code,
  Group,
  Skeleton,
  Spoiler,
  Stack,
  Text,
  Title,
  Tooltip,
  createStyles,
} from "@mantine/core";
import {
  IconChevronDown,
  IconChevronUp,
  IconClock,
  IconDownload,
  IconExternalLink,
  IconEye,
  IconHistory,
  IconTerminal,
  IconVariable,
} from "@tabler/icons-react";
import React, { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { getJob, listJobs } from "../api/job";
import { WorkflowJob, WorkflowJobType } from "../api/types";
import { isJobAbandoned } from "../utils/jobs";
import { getAssetObjectById } from "../api/assets";
import { AssetObjectModel } from "../api/types";
import { routes } from "../utils/routes";

const useStyles = createStyles((theme) => ({
  jobItem: {
    padding: theme.spacing.sm,
    borderRadius: theme.radius.sm,
    border: `1px solid ${
      theme.colorScheme === "dark" ? theme.colors.dark[4] : theme.colors.gray[3]
    }`,
    backgroundColor:
      theme.colorScheme === "dark" ? theme.colors.dark[6] : theme.white,
    "&:hover": {
      backgroundColor:
        theme.colorScheme === "dark"
          ? theme.colors.dark[5]
          : theme.colors.gray[0],
    },
    transition: "background-color 150ms ease",
  },
  mainRow: {
    display: "flex",
    alignItems: "center",
    gap: theme.spacing.sm,
    flexWrap: "nowrap",
    [theme.fn.smallerThan("sm")]: {
      flexWrap: "wrap",
      gap: theme.spacing.xs,
    },
  },
  infoSection: {
    flex: 1,
    minWidth: 0,
    display: "flex",
    alignItems: "center",
    gap: theme.spacing.xs,
    [theme.fn.smallerThan("sm")]: {
      flexBasis: "100%",
      order: 1,
    },
  },
  metaSection: {
    display: "flex",
    alignItems: "center",
    gap: theme.spacing.xs,
    flexShrink: 0,
    [theme.fn.smallerThan("sm")]: {
      order: 3,
      flexBasis: "100%",
      justifyContent: "space-between",
    },
  },
  actionsSection: {
    display: "flex",
    alignItems: "center",
    gap: 4,
    flexShrink: 0,
    [theme.fn.smallerThan("sm")]: {
      order: 2,
    },
  },
  truncatedText: {
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  errorSection: {
    marginTop: theme.spacing.xs,
    padding: theme.spacing.xs,
    backgroundColor:
      theme.colorScheme === "dark"
        ? theme.colors.dark[7]
        : theme.colors.gray[0],
    borderRadius: theme.radius.sm,
  },
}));

interface JobHistoryItemProps {
  job: WorkflowJob;
  onResume: (job: WorkflowJob) => void;
}

const JobHistoryItem: React.FC<JobHistoryItemProps> = ({ job, onResume }) => {
  const { classes } = useStyles();
  const { t } = useTranslation();
  const isRunning = !job.finalised_at;
  const hasError = job.results?.error;
  const isAbandoned = isJobAbandoned(job);
  const [assetObject, setAssetObject] = useState<any>(null);
  const [isLoadingAsset, setIsLoadingAsset] = useState(false);

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

  const formatTimestamp = (dateStr: string): string => {
    const date = new Date(dateStr.endsWith("Z") ? dateStr : dateStr + "Z");
    return date.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const getStatusBadge = (): React.ReactNode => {
    if (isAbandoned) {
      return (
        <Badge size="sm" color="orange" variant="light">
          {t("Abandoned")}
        </Badge>
      );
    }
    if (isRunning) {
      return (
        <Badge size="sm" color="blue" variant="light">
          {t("Running")}
        </Badge>
      );
    }
    if (hasError) {
      return (
        <Badge size="sm" color="red" variant="light">
          {t("Failed")}
        </Badge>
      );
    }
    return (
      <Badge size="sm" color="green" variant="light">
        {t("Completed")}
      </Badge>
    );
  };

  const assetName = assetObject?.asset?.name;
  const objectName = assetObject
    ? new AssetObjectModel(assetObject).humanName
    : null;
  const analysisVariable = job.arguments?.analysis_variable;
  const assetId = assetObject?.asset_id;
  const objectId = assetObject?.id;

  const assetObjectDetailsUrl =
    assetId && objectId ? routes.assetObjectShow(assetId, objectId) : null;

  return (
    <Box className={classes.jobItem}>
      {/* Main row */}
      <div className={classes.mainRow}>
        {/* Info section: Name + Variable */}
        <div className={classes.infoSection}>
          {isLoadingAsset ? (
            <Stack spacing={4}>
              <Skeleton height={16} width={150} />
              <Skeleton height={12} width={100} />
            </Stack>
          ) : (
            <Stack spacing={0} style={{ minWidth: 0 }}>
              <Group spacing="xs" noWrap>
                <Tooltip
                  label={objectName || t("Loading...")}
                  position="top-start"
                  withinPortal
                  disabled={!objectName}
                >
                  <Text
                    size="sm"
                    weight={500}
                    className={classes.truncatedText}
                  >
                    {objectName || t("Loading...")}
                  </Text>
                </Tooltip>
                {analysisVariable && (
                  <Tooltip label={t("Analysis variable")} withinPortal>
                    <Badge
                      size="xs"
                      variant="outline"
                      color="gray"
                      leftSection={<IconVariable size={10} />}
                    >
                      {analysisVariable}
                    </Badge>
                  </Tooltip>
                )}
              </Group>
              {assetName && (
                <Text
                  size="xs"
                  color="dimmed"
                  className={classes.truncatedText}
                >
                  {assetName}
                </Text>
              )}
            </Stack>
          )}
        </div>

        {/* Actions section */}
        <div className={classes.actionsSection}>
          {assetObjectDetailsUrl && (
            <Tooltip label={t("View dataset")} withinPortal>
              <ActionIcon
                component="a"
                href={assetObjectDetailsUrl}
                target="_blank"
                size="sm"
                variant="subtle"
                color="gray"
                onClick={(e: React.MouseEvent) => e.stopPropagation()}
              >
                <IconExternalLink size={16} />
              </ActionIcon>
            </Tooltip>
          )}
          {isRunning && !isAbandoned && (
            <Tooltip label={t("View progress")} withinPortal>
              <ActionIcon
                size="sm"
                variant="light"
                color="blue"
                onClick={(e) => {
                  e.stopPropagation();
                  onResume(job);
                }}
              >
                <IconEye size={16} />
              </ActionIcon>
            </Tooltip>
          )}
          {!isRunning && !hasError && job.extended_results?.download_url && (
            <Tooltip label={t("Download results")} withinPortal>
              <ActionIcon
                component="a"
                href={job.extended_results.download_url}
                target="_blank"
                size="sm"
                variant="light"
                color="green"
                onClick={(e: React.MouseEvent) => e.stopPropagation()}
              >
                <IconDownload size={16} />
              </ActionIcon>
            </Tooltip>
          )}
          {!isRunning && job.extended_results?.error_logs_download_url && (
            <Tooltip label={t("Download error logs")} withinPortal>
              <ActionIcon
                component="a"
                href={job.extended_results.error_logs_download_url}
                target="_blank"
                size="sm"
                variant="light"
                color="red"
                onClick={(e: React.MouseEvent) => e.stopPropagation()}
              >
                <IconDownload size={16} />
              </ActionIcon>
            </Tooltip>
          )}
        </div>

        {/* Meta section: Timestamp + Badge */}
        <div className={classes.metaSection}>
          <Group spacing={4} noWrap>
            <IconClock size={12} style={{ opacity: 0.5 }} />
            <Text size="xs" color="dimmed">
              {formatTimestamp(job.created_at)}
            </Text>
          </Group>
          {getStatusBadge()}
        </div>
      </div>

      {/* Error section with Spoiler */}
      {hasError && (
        <Spoiler
          maxHeight={0}
          showLabel={
            <Group spacing={4} mt="xs">
              <IconChevronDown size={14} />
              <Text size="xs" color="red">
                {t("Show error details")}
              </Text>
            </Group>
          }
          hideLabel={
            <Group spacing={4} mt="xs">
              <IconChevronUp size={14} />
              <Text size="xs" color="red">
                {t("Hide error details")}
              </Text>
            </Group>
          }
        >
          <Box className={classes.errorSection}>
            <Group spacing={4} mb={4}>
              <IconTerminal size={12} />
              <Text size="xs" weight={500} color="red">
                {t("Error")}
              </Text>
            </Group>
            <Code block style={{ fontSize: "0.7rem", whiteSpace: "pre-wrap" }}>
              {job.results?.error}
            </Code>
          </Box>
        </Spoiler>
      )}
    </Box>
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
          if (job.finalised_at) {
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
  const failedJobs = completedJobs.filter((job) => job.results?.error);
  const successfulJobs = completedJobs.filter((job) => !job.results?.error);

  // Auto-expand if there are running, abandoned or failed jobs
  const defaultValue =
    runningJobs.length > 0 || abandonedJobs.length > 0 || failedJobs.length > 0
      ? "history"
      : undefined;

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
            {failedJobs.length > 0 && (
              <Badge color="red" size="sm" variant="filled">
                {failedJobs.length} {t("failed")}
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
                      "Jobs running for too long without completion. These may have encountered an issue.",
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

              {failedJobs.length > 0 && (
                <>
                  <Title
                    order={6}
                    color="red"
                    mt={
                      runningJobs.length > 0 || abandonedJobs.length > 0
                        ? "sm"
                        : 0
                    }
                  >
                    {t("Failed")}
                  </Title>
                  <Text size="xs" color="dimmed" mb="xs">
                    {t("Jobs that encountered errors during execution.")}
                  </Text>
                  {failedJobs.map((job) => (
                    <JobHistoryItem
                      key={job.id}
                      job={job}
                      onResume={onResumeJob}
                    />
                  ))}
                </>
              )}

              {successfulJobs.length > 0 && (
                <>
                  <Title
                    order={6}
                    color="green"
                    mt={
                      runningJobs.length > 0 ||
                      abandonedJobs.length > 0 ||
                      failedJobs.length > 0
                        ? "sm"
                        : 0
                    }
                  >
                    {t("Successful")}
                  </Title>
                  <Text size="xs" color="dimmed" mb="xs">
                    {t("Successfully completed jobs.")}
                  </Text>
                  {successfulJobs.map((job) => (
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
