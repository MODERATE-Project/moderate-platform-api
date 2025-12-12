import { WorkflowJob } from "../api/types";

/**
 * Configurable threshold for marking jobs as abandoned.
 * Change this value to adjust when jobs should be considered "abandoned".
 *
 * Examples:
 *   1 * 60 * 60 * 1000 = 1 hour
 *   12 * 60 * 60 * 1000 = 12 hours
 *   24 * 60 * 60 * 1000 = 24 hours (default)
 */
export const ABANDONED_JOB_THRESHOLD_MS = 24 * 60 * 60 * 1000; // 24 hours

/**
 * Check if a job should be marked as abandoned.
 * A job is considered abandoned if it's been running longer than ABANDONED_JOB_THRESHOLD_MS.
 */
export function isJobAbandoned(job: WorkflowJob): boolean {
  // Job is only abandoned if it's still running
  if (job.finalised_at) {
    return false;
  }

  const formatDate = (dateStr: string) => {
    const d = dateStr.endsWith("Z") ? dateStr : dateStr + "Z";
    return new Date(d);
  };

  const createdDate = formatDate(job.created_at);
  const now = Date.now();
  const elapsedMs = now - createdDate.getTime();

  return elapsedMs > ABANDONED_JOB_THRESHOLD_MS;
}

/**
 * Get the elapsed time for a job in milliseconds.
 */
export function getJobElapsedMs(job: WorkflowJob): number {
  const formatDate = (dateStr: string) => {
    const d = dateStr.endsWith("Z") ? dateStr : dateStr + "Z";
    return new Date(d);
  };

  const createdDate = formatDate(job.created_at);
  const endDate = job.finalised_at ? formatDate(job.finalised_at) : new Date();
  return endDate.getTime() - createdDate.getTime();
}
