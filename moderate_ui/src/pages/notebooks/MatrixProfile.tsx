import {
  ActionIcon,
  Alert,
  Button,
  Card,
  Code,
  Group,
  Loader,
  Progress,
  Select,
  Stack,
  Stepper,
  Text,
  ThemeIcon,
  Timeline,
  Title,
} from "@mantine/core";
import {
  IconAlertCircle,
  IconBrandGithub,
  IconCheck,
  IconDownload,
  IconExclamationCircle,
  IconHourglass,
  IconPlayerPlay,
  IconTerminal,
  IconVariable,
} from "@tabler/icons-react";
import React, { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { getAssetObjectById, getAssetObjectColumns } from "../../api/assets";
import { createMatrixProfileJob, getJob } from "../../api/job";
import { AssetModel, AssetObjectModel, WorkflowJob } from "../../api/types";
import { AssetObjectCard } from "../../components/AssetObjectCard";
import {
  AssetObjectPicker,
  DatasetSelectOption,
} from "../../components/AssetObjectPicker";
import { MatrixProfileJobHistory } from "../../components/MatrixProfileJobHistory";

const MatrixProfileWorkflowAnalysisVariableStep: React.FC<{
  selectedAsset: DatasetSelectOption;
  variableInputValue: string;
  setVariableInputValue: (value: string) => void;
  setAnalysisVariable: (value: string) => void;
}> = ({
  selectedAsset,
  variableInputValue,
  setVariableInputValue,
  setAnalysisVariable,
}) => {
  const { t } = useTranslation();
  const [columns, setColumns] = useState<string[]>([]);
  const [isLoadingColumns, setIsLoadingColumns] = useState(false);
  const [columnsError, setColumnsError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    setIsLoadingColumns(true);
    setColumnsError(null);
    setColumns([]);

    getAssetObjectColumns({
      assetId: selectedAsset.asset.data.id,
      objectId: selectedAsset.assetObject.data.id,
    })
      .then((response) => {
        if (isMounted) {
          setColumns(response.columns);
        }
      })
      .catch((err) => {
        if (isMounted) {
          console.error("Failed to fetch columns", err);
          setColumnsError(
            t(
              "Failed to load column names from the dataset. Please try again.",
            ),
          );
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsLoadingColumns(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [selectedAsset, t]);

  const columnOptions = columns.map((col) => ({ value: col, label: col }));

  return (
    <Stack>
      <AssetObjectCard
        asset={selectedAsset.asset.data}
        assetObject={selectedAsset.assetObject.data}
      />
      {columnsError && (
        <Alert
          icon={<IconAlertCircle size="1rem" />}
          title={t("Error")}
          color="red"
          variant="light"
        >
          {columnsError}
        </Alert>
      )}
      <Select
        icon={
          isLoadingColumns ? <Loader size="xs" /> : <IconVariable size="1em" />
        }
        label={t("Analysis Variable")}
        placeholder={
          isLoadingColumns
            ? t("Loading columns...")
            : t("Select the column for analysis")
        }
        description={t(
          "The variable name used for the analysis (i.e., the column in the CSV containing the electrical load under analysis).",
        )}
        data={columnOptions}
        value={variableInputValue}
        onChange={(value) => setVariableInputValue(value || "")}
        searchable
        disabled={isLoadingColumns || columns.length === 0}
        nothingFound={t("No columns found")}
      />
      <Button
        leftIcon={<IconCheck size="1em" />}
        disabled={variableInputValue === ""}
        onClick={() => {
          setAnalysisVariable(variableInputValue);
        }}
      >
        {t("Confirm variable")}
      </Button>
    </Stack>
  );
};

const MatrixProfileWorkflowResultsStep: React.FC<{
  selectedAsset: DatasetSelectOption;
  workflowJob: WorkflowJob | undefined;
  onJobSubmit: () => void;
  isJobRunning: boolean;
  elapsedTime: number;
}> = ({
  selectedAsset,
  workflowJob,
  onJobSubmit,
  isJobRunning,
  elapsedTime,
}) => {
  const { t } = useTranslation();

  const formatElapsedTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  };

  return (
    <Stack>
      <AssetObjectCard
        asset={selectedAsset.asset.data}
        assetObject={selectedAsset.assetObject.data}
      />
      {!workflowJob && (
        <Button
          leftIcon={<IconPlayerPlay size="1em" />}
          onClick={onJobSubmit}
          loading={isJobRunning}
        >
          {t("Run workflow")}
        </Button>
      )}
      {workflowJob && (
        <>
          <Title mt="md" order={3}>
            {t("Job results")}
          </Title>
          {isJobRunning && (
            <Card withBorder p="lg" radius="md">
              <Stack spacing="md">
                <Group>
                  <ThemeIcon color="blue" variant="light" size="lg">
                    <IconHourglass size="1.2em" />
                  </ThemeIcon>
                  <Stack spacing={2}>
                    <Text weight={500}>{t("Processing your dataset...")}</Text>
                    <Text size="sm" color="dimmed">
                      {t(
                        "This may take several minutes depending on data size.",
                      )}
                    </Text>
                  </Stack>
                </Group>

                <Progress value={100} animate size="sm" color="blue" />

                {elapsedTime > 0 && (
                  <Text size="xs" color="dimmed" align="center">
                    {t("Elapsed time:")} {formatElapsedTime(elapsedTime)}
                  </Text>
                )}

                <Timeline active={1} bulletSize={20} lineWidth={2}>
                  <Timeline.Item title={t("Job submitted")} color="green">
                    <Text color="dimmed" size="xs">
                      {new Date(
                        workflowJob.created_at.endsWith("Z")
                          ? workflowJob.created_at
                          : workflowJob.created_at + "Z",
                      ).toLocaleTimeString()}
                    </Text>
                  </Timeline.Item>
                  <Timeline.Item title={t("Processing")} color="blue">
                    <Text color="dimmed" size="xs">
                      {t("Analyzing time series data...")}
                    </Text>
                  </Timeline.Item>
                  <Timeline.Item title={t("Complete")} color="gray" />
                </Timeline>
              </Stack>
            </Card>
          )}
          {!isJobRunning &&
            workflowJob.results &&
            !workflowJob.results?.error && (
              <Group>
                <ThemeIcon color="green" variant="light">
                  <IconCheck size="1em" />
                </ThemeIcon>
                <Text>
                  {t(
                    "The job has finished running. You can find the results below.",
                  )}
                </Text>
              </Group>
            )}
          {!isJobRunning && workflowJob.results?.error && (
            <>
              <Group>
                <ThemeIcon color="red" variant="light">
                  <IconExclamationCircle size="1em" />
                </ThemeIcon>
                <Text>
                  {t("An error occurred during the workflow execution.")}
                </Text>
              </Group>
              <Card shadow="sm" p="lg" radius="md" withBorder>
                <Group mb="xs">
                  <IconTerminal size="1em" />
                  <Text weight={500} color="red">
                    {t("Error details")}
                  </Text>
                </Group>
                <Text size="sm" color="dimmed">
                  <Code block>{workflowJob.results?.error}</Code>
                </Text>
              </Card>
            </>
          )}
          {workflowJob && workflowJob.extended_results?.download_url && (
            <Button
              leftIcon={<IconDownload size="1em" />}
              component="a"
              href={workflowJob.extended_results.download_url}
              target="_blank"
              color="green"
            >
              {t("Download the output HTML report")}
            </Button>
          )}
        </>
      )}
    </Stack>
  );
};

interface Props {
  jobIntervalMs?: number;
}

export const MatrixProfileWorkflow: React.FC<Props> = ({
  jobIntervalMs = 10000,
}) => {
  const { t } = useTranslation();

  const [activeStep, setActiveStep] = useState(0);

  const [selectedAsset, setSelectedAsset] = useState<
    DatasetSelectOption | undefined
  >(undefined);

  const [variableInputValue, setVariableInputValue] = useState<string>("");

  const [analysisVariable, setAnalysisVariable] = useState<string | undefined>(
    undefined,
  );

  const [workflowJob, setWorkflowJob] = useState<WorkflowJob | undefined>(
    undefined,
  );

  const [isJobRunning, setIsJobRunning] = useState<boolean>(false);

  const [refreshHistoryTrigger, setRefreshHistoryTrigger] = useState(0);

  const [elapsedTime, setElapsedTime] = useState<number>(0);

  // Flag to prevent step management effect from running during resume
  const [isResuming, setIsResuming] = useState<boolean>(false);

  // Ref for scrolling to workflow results when resuming a job
  const workflowResultsRef = useRef<HTMLDivElement>(null);

  const onDatasetSelect = useCallback(
    (item: DatasetSelectOption | undefined) => {
      setSelectedAsset(item);
    },
    [],
  );

  const onJobSubmit = useCallback(() => {
    if (!selectedAsset || !analysisVariable) {
      return;
    }

    setIsJobRunning(true);

    createMatrixProfileJob({
      assetObject: selectedAsset.assetObject,
      analysisVariable,
    })
      .then((res) => {
        setWorkflowJob(res);
      })
      .catch((err) => {
        console.error("Job creation failed", err);
      });
  }, [selectedAsset, analysisVariable]);

  useEffect(() => {
    if (!workflowJob || workflowJob.finalised_at) {
      return;
    }

    const intervalId = setInterval(() => {
      getJob({ jobId: workflowJob.id, withExtendedResults: true })
        .then((updatedJob) => {
          setWorkflowJob(updatedJob);
        })
        .catch((err) => {
          console.error("Failed to fetch job status", err);
          clearInterval(intervalId);
        });
    }, jobIntervalMs);

    return () => clearInterval(intervalId);
  }, [workflowJob, jobIntervalMs]);

  useEffect(() => {
    if (workflowJob && workflowJob.finalised_at) {
      setIsJobRunning(false);
      // Refresh job history when job completes
      setRefreshHistoryTrigger((prev) => prev + 1);
    }
  }, [workflowJob]);

  // Track elapsed time when job is running
  useEffect(() => {
    if (!workflowJob || workflowJob.finalised_at) {
      setElapsedTime(0);
      return;
    }

    const createdAt = workflowJob.created_at.endsWith("Z")
      ? workflowJob.created_at
      : workflowJob.created_at + "Z";
    const startTime = new Date(createdAt).getTime();

    const updateElapsed = (): void => {
      const now = Date.now();
      setElapsedTime(Math.floor((now - startTime) / 1000));
    };

    updateElapsed();
    const intervalId = setInterval(updateElapsed, 1000);

    return () => clearInterval(intervalId);
  }, [workflowJob]);

  // Handler for resuming a running job from history
  const handleResumeJob = useCallback(async (job: WorkflowJob) => {
    // Set flag to prevent step management effect from interfering
    setIsResuming(true);

    let assetOption: DatasetSelectOption | undefined;

    if (job.arguments?.uploaded_s3_object_id) {
      try {
        const object = await getAssetObjectById(
          job.arguments.uploaded_s3_object_id,
        );
        if (object && object.asset) {
          const assetModel = new AssetModel(object.asset);
          const assetObjectModel = new AssetObjectModel(object);
          assetOption = {
            value: object.id.toString(),
            label: assetObjectModel.humanName,
            group: assetModel.data.name,
            asset: assetModel,
            assetObject: assetObjectModel,
          };
        }
      } catch (e) {
        console.error("Failed to fetch asset for resumed job", e);
        setIsResuming(false);
        return;
      }
    }

    if (assetOption) {
      setSelectedAsset(assetOption);
    }

    // Set analysis variable from job arguments
    if (job.arguments?.analysis_variable) {
      setAnalysisVariable(job.arguments.analysis_variable);
      setVariableInputValue(job.arguments.analysis_variable);
    }

    setWorkflowJob(job);
    setIsJobRunning(!job.finalised_at);

    // Move to the processing step
    setActiveStep(2);

    // Clear resuming flag after state is set
    setIsResuming(false);

    // Scroll to the workflow results section after state updates
    setTimeout(() => {
      workflowResultsRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }, 100);
  }, []);

  useEffect(() => {
    // Skip step management when resuming a job
    if (isResuming) {
      return;
    }

    if (selectedAsset === undefined) {
      setActiveStep(0);
      setAnalysisVariable(undefined);
      setWorkflowJob(undefined);
      return;
    }

    if (selectedAsset && analysisVariable === undefined) {
      setActiveStep(1);
      setWorkflowJob(undefined);
      return;
    }

    if (selectedAsset && analysisVariable && workflowJob === undefined) {
      setActiveStep(2);
      return;
    }
  }, [selectedAsset, analysisVariable, workflowJob, isResuming]);

  return (
    <Stack>
      <Group mt="xl" mb="lg" position="left" style={{ flexWrap: "nowrap" }}>
        <Stack>
          <Title>{t("Contextual Matrix Profile Calculation Tool")}</Title>
          <Text color="dimmed">
            <Group>
              <span>
                {t(
                  "An algorithm designed to identify patterns and anomalies in time series data",
                )}
              </span>
              <ActionIcon
                variant="light"
                color="indigo"
                component="a"
                href="https://github.com/MODERATE-Project/matrix-profile"
                target="_blank"
              >
                <IconBrandGithub size="1em" />
              </ActionIcon>
            </Group>
          </Text>
        </Stack>
      </Group>
      <MatrixProfileJobHistory
        onResumeJob={handleResumeJob}
        refreshTrigger={refreshHistoryTrigger}
      />
      <div ref={workflowResultsRef}>
        <Stepper active={activeStep} breakpoint="sm">
          <Stepper.Step
            label={t("Dataset")}
            description={t("Pick a CSV dataset")}
          >
            <AssetObjectPicker
              onSelect={onDatasetSelect}
              fileFormat="csv"
              showFormatInfo={true}
            />
          </Stepper.Step>
          <Stepper.Step
            label={t("Variable")}
            description={
              analysisVariable ? (
                <Code>{analysisVariable}</Code>
              ) : (
                t("Input the analysis variable")
              )
            }
          >
            {selectedAsset && (
              <MatrixProfileWorkflowAnalysisVariableStep
                {...{
                  selectedAsset,
                  variableInputValue,
                  setVariableInputValue,
                  setAnalysisVariable,
                }}
              />
            )}
          </Stepper.Step>
          <Stepper.Step
            label={t("Processing")}
            description={t("Wait for the job to finish")}
            loading={isJobRunning}
          >
            {selectedAsset && analysisVariable && (
              <MatrixProfileWorkflowResultsStep
                {...{
                  selectedAsset,
                  workflowJob,
                  onJobSubmit,
                  isJobRunning,
                  elapsedTime,
                }}
              />
            )}
          </Stepper.Step>
        </Stepper>
      </div>
    </Stack>
  );
};
