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
