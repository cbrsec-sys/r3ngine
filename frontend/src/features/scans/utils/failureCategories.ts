import type { ScanActivity } from '../types';

/**
 * Operator-facing wording for the categories produced by `classify_failure()`
 * in `web/reNgine/failure_reasons.py`. Keep the keys in sync with that module.
 *
 * A `Map` rather than an object literal: the key arrives from the API, so it
 * must not be able to reach a prototype member (security rule 5.1).
 */
const FAILURE_CATEGORY_LABELS = new Map<string, string>([
  ['temporal_cancelled', 'Cancelled'],
  ['heartbeat_timeout', 'Heartbeat timeout'],
  ['activity_timeout', 'Time limit exceeded'],
  ['worker_restart', 'Worker restart'],
  ['missing_configuration', 'Missing configuration'],
  ['proxy_failure', 'Proxy failure'],
  ['database_error', 'Datastore error'],
  ['network_error', 'Network error'],
  ['tool_failure', 'Tool failure'],
  ['unknown', 'Unclassified failure'],
]);

/**
 * Causes that are usually environmental rather than a problem with the task
 * itself — a reboot, a dead proxy, a flaky link. Re-running the tier is worth a
 * try for these; for the rest the operator has to fix something first.
 */
const TRANSIENT_FAILURE_CATEGORIES = new Set<string>([
  'heartbeat_timeout',
  'activity_timeout',
  'worker_restart',
  'proxy_failure',
  'database_error',
  'network_error',
]);

/** Human label for a failure category, or `null` when the API sent none. */
export const getFailureCategoryLabel = (category?: string | null): string | null => {
  if (!category) return null;
  return FAILURE_CATEGORY_LABELS.get(category) ?? 'Unclassified failure';
};

export const isTransientFailureCategory = (category?: string | null): boolean =>
  !!category && TRANSIENT_FAILURE_CATEGORIES.has(category);

export type TierStatus = 'FAILED' | 'RUNNING' | 'PENDING' | 'COMPLETE' | 'EMPTY';

export interface TierSummary {
  status: TierStatus;
  total: number;
  failedCount: number;
  runningCount: number;
  pendingCount: number;
  successCount: number;
  /** Distinct failure categories seen in the group, in first-seen order. */
  failureCategories: string[];
  /** True when every failure in the group looks environmental. */
  allFailuresTransient: boolean;
}

/** Roll a tier group's activities up into one status the header can show. */
export const summariseTier = (activities: ScanActivity[]): TierSummary => {
  const failureCategories: string[] = [];
  let failedCount = 0;
  let runningCount = 0;
  let pendingCount = 0;
  let successCount = 0;
  let transientFailures = 0;

  activities.forEach((activity) => {
    if (activity.status === 'FAILED' || activity.status === 'ABORTED') {
      failedCount += 1;
      const category = activity.failure_category;
      if (category && !failureCategories.includes(category)) {
        failureCategories.push(category);
      }
      if (isTransientFailureCategory(category)) transientFailures += 1;
    } else if (activity.status === 'RUNNING') {
      runningCount += 1;
    } else if (activity.status === 'PENDING') {
      pendingCount += 1;
    } else if (activity.status === 'SUCCESS') {
      successCount += 1;
    }
  });

  // A single failed row makes the whole tier read as failed: that is the
  // question the operator opens the timeline with.
  const status: TierStatus = activities.length === 0
    ? 'EMPTY'
    : failedCount > 0
      ? 'FAILED'
      : runningCount > 0
        ? 'RUNNING'
        : successCount === activities.length
          ? 'COMPLETE'
          : 'PENDING';

  return {
    status,
    total: activities.length,
    failedCount,
    runningCount,
    pendingCount,
    successCount,
    failureCategories,
    allFailuresTransient: failedCount > 0 && transientFailures === failedCount,
  };
};
