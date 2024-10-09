import {
  ActionIcon,
  Button,
  Code,
  Group,
  Skeleton,
  Stack,
  Stepper,
  Text,
  TextInput,
  ThemeIcon,
  Title,
} from "@mantine/core";
import {
  IconBrandGithub,
  IconCheck,
  IconDownload,
  IconExclamationCircle,
  IconHourglass,
  IconPlayerPlay,
  IconVariable,
} from "@tabler/icons-react";
import React, { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { createMatrixProfileJob, getJob } from "../../api/job";
import { WorkflowJob } from "../../api/types";
import { AssetObjectCard } from "../../components/AssetObjectCard";
import {
  AssetObjectPicker,
  DatasetSelectOption,
} from "../../components/AssetObjectPicker";

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
    undefined
  );

  const [workflowJob, setWorkflowJob] = useState<WorkflowJob | undefined>(
    undefined
  );

  const [isJobRunning, setIsJobRunning] = useState<boolean>(false);

  const onDatasetSelect = useCallback(
    (item: DatasetSelectOption | undefined) => {
      setSelectedAsset(item);
    },
    []
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
        console.debug("Job created", res);
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
          console.debug("Job refreshed", updatedJob);
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
      console.log("Job finished");
      setIsJobRunning(false);
    }
  }, [workflowJob]);

  useEffect(() => {
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
  }, [selectedAsset, analysisVariable, workflowJob]);

  return (
    <Stack>
      <Group mt="xl" mb="lg" position="left" style={{ flexWrap: "nowrap" }}>
        <Stack>
          <Title>{t("Contextual Matrix Profile Calculation Tool")}</Title>
          <Text color="dimmed">
            <Group>
              <span>
                {t(
                  "An algorithm designed to identify patterns and anomalies in time series data"
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
      <Stepper active={activeStep} breakpoint="sm">
        <Stepper.Step label={t("Dataset")} description={t("Pick a dataset")}>
          <AssetObjectPicker onSelect={onDatasetSelect} />
        </Stepper.Step>
        <Stepper.Step
          label={t("Variable")}
          description={t("Input the analysis variable")}
        >
          {selectedAsset && (
            <Stack>
              <AssetObjectCard
                asset={selectedAsset.asset.data}
                assetObject={selectedAsset.assetObject.data}
              />
              <TextInput
                icon={<IconVariable size="1em" />}
                placeholder={t(
                  "Input the column variable from your dataset that will be the focus of the analysis"
                )}
                description={t(
                  "The variable name used for the analysis (i.e., the column in the CSV containing the electrical load under analysis)."
                )}
                value={variableInputValue}
                onChange={(event) =>
                  setVariableInputValue(event.currentTarget.value)
                }
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
          )}
        </Stepper.Step>
        <Stepper.Step
          label={t("Processing")}
          description={t("Wait for the job to finish")}
          loading={isJobRunning}
        >
          {selectedAsset && analysisVariable && (
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
                  {t("Run workflow on variable ")}&nbsp;
                  <Code>{analysisVariable}</Code>
                </Button>
              )}
              {workflowJob && (
                <>
                  <Title mt="md" order={3}>
                    {t("Job results")}
                  </Title>
                  {isJobRunning && (
                    <Group>
                      <ThemeIcon color="gray" variant="light">
                        <IconHourglass size="1em" />
                      </ThemeIcon>
                      <Text>
                        {t(
                          "The job has been queued. Please wait a few minutes; this may take a while."
                        )}
                      </Text>
                    </Group>
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
                            "The job has finished running. You can find the results below."
                          )}
                        </Text>
                      </Group>
                    )}
                  {!isJobRunning && workflowJob.results?.error && (
                    <Group>
                      <ThemeIcon color="red" variant="light">
                        <IconExclamationCircle size="1em" />
                      </ThemeIcon>
                      <Text>
                        {t("An error occurred during the workflow execution.")}
                      </Text>
                    </Group>
                  )}
                  {isJobRunning && <Skeleton height={80} mt={6} radius="md" />}
                  {workflowJob &&
                    workflowJob.extended_results?.download_url && (
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
          )}
        </Stepper.Step>
      </Stepper>
    </Stack>
  );
};
