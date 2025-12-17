import axios from "axios";
import { AssetObjectModel, WorkflowJob, WorkflowJobType } from "./types";
import { buildApiUrl } from "./utils";

export async function createMatrixProfileJob({
  assetObject,
  analysisVariable,
}: {
  assetObject: AssetObjectModel;
  analysisVariable: string;
}): Promise<WorkflowJob> {
  const data = {
    job_type: WorkflowJobType.MATRIX_PROFILE,
    arguments: {
      uploaded_s3_object_id: assetObject.data.id,
      analysis_variable: analysisVariable,
    },
  };

  const response = await axios.post(buildApiUrl("job"), data);
  return response.data;
}

export async function getJob({
  jobId,
  withExtendedResults,
}: {
  jobId: number | string;
  withExtendedResults?: string | boolean;
}): Promise<WorkflowJob> {
  const params: { [k: string]: string } = {};

  if (withExtendedResults) {
    params.with_extended_results = "true";
  }

  const response = await axios.get(buildApiUrl("job", jobId.toString()), {
    params,
  });

  return response.data;
}

export interface ListJobsParams {
  jobType?: WorkflowJobType;
  limit?: number;
  offset?: number;
  withExtendedResults?: boolean;
}

export async function listJobs({
  jobType,
  limit = 10,
  offset = 0,
  withExtendedResults,
}: ListJobsParams = {}): Promise<WorkflowJob[]> {
  const params: Record<string, string> = {};

  if (limit !== undefined) {
    params.limit = limit.toString();
  }

  if (offset !== undefined) {
    params.offset = offset.toString();
  }

  // Filter by job type at database level
  // Backend handles enum normalization (converts "matrix_profile" → MATRIX_PROFILE)
  if (jobType !== undefined) {
    params.filters = JSON.stringify([
      { field: "job_type", operator: "eq", value: jobType },
    ]);
  }

  // Sort by created_at descending (most recent first)
  params.sorts = JSON.stringify([{ field: "created_at", order: "desc" }]);

  // Request extended results (e.g., download URLs) for completed jobs
  if (withExtendedResults) {
    params.with_extended_results = "true";
  }

  const response = await axios.get(buildApiUrl("job"), { params });

  return response.data;
}
