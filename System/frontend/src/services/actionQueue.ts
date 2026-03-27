export interface SummaryMap {
  [key: string]: number
}

export interface ActionJobRecord {
  jobId: string
  requestId?: string | null
  batchRef?: string | null
  actionCode?: string | null
  jobStatus?: string | null
  queueStatus?: string | null
  workerId?: string | null
  leaseExpiresAt?: string | null
  eventCount?: number
  acceptedAt?: string | null
  queuedAt?: string | null
  startedAt?: string | null
  finishedAt?: string | null
  recommendedOperation?: string | null
}

export interface ActionDashboardResponse {
  contractVersion?: string
  summary?: SummaryMap
  statusSummary?: SummaryMap
  recoveryStateSummary?: SummaryMap
  latestJobs?: ActionJobRecord[]
  latestJobsTotal?: number
  recentRecoveryEvents?: Array<Record<string, unknown>>
}

export interface ActionMetricsResponse {
  contractVersion?: string
  summary?: SummaryMap
  queueLagMetrics?: Record<string, unknown>
  runDurationMetrics?: Record<string, unknown>
  turnaroundMetrics?: Record<string, unknown>
  lagBuckets?: SummaryMap
  sla?: SummaryMap
  topLaggingJobs?: ActionJobRecord[]
  topLaggingJobsTotal?: number
}

export interface ActionFailureBucketsResponse {
  contractVersion?: string
  summary?: SummaryMap
  reasonSummary?: SummaryMap
  reasonBucketSummary?: SummaryMap
  items?: Array<Record<string, unknown>>
  total?: number
}

export interface ActionWorkerOverviewResponse {
  contractVersion?: string
  summary?: SummaryMap
  nextJobs?: ActionJobRecord[]
  nextJobsTotal?: number
  activeLeases?: ActionJobRecord[]
  activeLeasesTotal?: number
  stalledJobs?: ActionJobRecord[]
  stalledJobsTotal?: number
}


export interface ActionWorkerStaleResponse {
  contractVersion?: string
  summary?: SummaryMap
  items?: ActionJobRecord[]
  total?: number
}

export interface ActionWorkerLeaseAuditResponse {
  contractVersion?: string
  scope?: Record<string, unknown>
  summary?: SummaryMap
  eventTypeSummary?: SummaryMap
  actionCodeSummary?: SummaryMap
  items?: Array<Record<string, unknown>>
  total?: number
}

export interface ActionWorkerCommandAuditResponse {
  contractVersion?: string
  scope?: Record<string, unknown>
  summary?: SummaryMap
  commandTypeSummary?: SummaryMap
  actionCodeSummary?: SummaryMap
  items?: Array<Record<string, unknown>>
  total?: number
}

export interface ActionWorkerCommandAuditDetailResponse {
  contractVersion?: string
  eventId?: string
  commandAudit?: Record<string, unknown>
  job?: ActionJobDetailResponse
  timeline?: Array<Record<string, unknown>>
  timelineTotal?: number
}

export interface ActionBulkCommandResponse {
  contractVersion?: string
  command?: string
  summary?: SummaryMap
  itemStatusSummary?: SummaryMap
  errorReasonSummary?: SummaryMap
  items?: ActionJobRecord[]
  errors?: Array<Record<string, unknown>>
  total?: number
}


export interface ActionBulkCommandHistoryItem {
  bulkCommandId?: string
  eventAt?: string
  command?: string
  commandMode?: string | null
  lineageScope?: string | null
  operator?: string | null
  workerId?: string | null
  scope?: Record<string, unknown>
  summary?: SummaryMap
  resultMode?: string
  itemStatusSummary?: SummaryMap
  errorReasonSummary?: SummaryMap
  total?: number
}

export interface ActionBulkCommandHistoryResponse {
  contractVersion?: string
  scope?: Record<string, unknown>
  summary?: SummaryMap
  commandSummary?: SummaryMap
  resultModeSummary?: SummaryMap
  actionCodeSummary?: SummaryMap
  actionCodeSummary?: SummaryMap
  selectionSummary?: SummaryMap
  reexecuteCommandSummary?: SummaryMap
  commandModeSummary?: SummaryMap
  lineageScopeSummary?: SummaryMap
  pagination?: Record<string, unknown>
  items?: ActionBulkCommandHistoryItem[]
  total?: number
}

export interface ActionBulkCommandRelatedResponse {
  contractVersion?: string
  bulkCommandId?: string
  lineage?: Record<string, unknown>
  summary?: SummaryMap
  commandSummary?: SummaryMap
  resultModeSummary?: SummaryMap
  actionCodeSummary?: SummaryMap
  commandModeSummary?: SummaryMap
  selectionSummary?: SummaryMap
  reexecuteCommandSummary?: SummaryMap
  lineageScopeSummary?: SummaryMap
  operatorSummary?: SummaryMap
  workerIdSummary?: SummaryMap
  reasonSummary?: SummaryMap
  externalRefSummary?: SummaryMap
  requestIdSummary?: SummaryMap
  batchRefSummary?: SummaryMap
  rootBulkCommandSummary?: SummaryMap
  sourceBulkCommandSummary?: SummaryMap
  parentBulkCommandSummary?: SummaryMap
  lineageDepthSummary?: SummaryMap
  childCountSummary?: SummaryMap
  descendantCountSummary?: SummaryMap
  noteSummary?: SummaryMap
  itemStatusSummary?: SummaryMap
  errorReasonSummary?: SummaryMap
  linkedHistoryFilters?: Record<string, unknown>
  linkedTimelineFilters?: Record<string, unknown>
  items?: Array<Record<string, unknown>>
  total?: number
}

export interface ActionBulkCommandTimelineResponse {
  contractVersion?: string
  bulkCommandId?: string
  scope?: Record<string, unknown>
  lineage?: Record<string, unknown>
  summary?: SummaryMap
  commandSummary?: SummaryMap
  resultModeSummary?: SummaryMap
  actionCodeSummary?: SummaryMap
  eventTypeSummary?: SummaryMap
  actionCodeSummary?: SummaryMap
  selectionSummary?: SummaryMap
  reexecuteCommandSummary?: SummaryMap
  commandModeSummary?: SummaryMap
  lineageScopeSummary?: SummaryMap
  lineageSummary?: SummaryMap
  items?: Array<Record<string, unknown>>
  total?: number
}

export interface ActionBulkCommandLineageSummaryResponse {
  contractVersion?: string
  bulkCommandId?: string
  scope?: Record<string, unknown>
  lineage?: Record<string, unknown>
  summary?: SummaryMap
  commandSummary?: SummaryMap
  resultModeSummary?: SummaryMap
  actionCodeSummary?: SummaryMap
  actionCodeSummary?: SummaryMap
  selectionSummary?: SummaryMap
  reexecuteCommandSummary?: SummaryMap
  commandModeSummary?: SummaryMap
  lineageScopeSummary?: SummaryMap
  eventTypeSummary?: SummaryMap
  lineageSummary?: SummaryMap
  linkedHistoryFilters?: Record<string, unknown>
  linkedTimelineFilters?: Record<string, unknown>
  latestResults?: Array<Record<string, unknown>>
  timeline?: Array<Record<string, unknown>>
  timelineSummary?: SummaryMap
  timelineEventTypeSummary?: SummaryMap
  timelineCommandModeSummary?: SummaryMap
  timelineTotal?: number
}

export interface ActionBulkCommandDetailResponse {
  contractVersion?: string
  bulkCommandId?: string
  bulkCommand?: Record<string, unknown>
  failedJobIds?: string[]
  lineage?: Record<string, unknown>
  navigationContext?: Record<string, unknown>
  relatedResults?: Array<Record<string, unknown>>
  secondaryActions?: Record<string, unknown>
}

export interface ActionStaleReleaseResponse {
  contractVersion?: string
  scope?: Record<string, unknown>
  summary?: SummaryMap
  items?: ActionJobRecord[]
  total?: number
}

export interface ActionJobDetailResponse extends ActionJobRecord {
  traceId?: string | null
  idempotencyKey?: string | null
  adapter?: string | null
  eventCount?: number
  timeline?: Array<Record<string, unknown>>
}

export interface ActionJobEventsResponse {
  jobId?: string
  events?: Array<Record<string, unknown>>
  total?: number
}

export interface ActionJobAuditResponse {
  scope?: string
  jobId?: string
  requestId?: string | null
  batchRef?: string | null
  actionCode?: string | null
  jobStatus?: string | null
  queueStatus?: string | null
  recoveryState?: string | null
  recommendedOperation?: string | null
  availableCommands?: string[]
  failureReason?: string | null
  metrics?: Record<string, unknown>
  timeline?: Array<Record<string, unknown>>
  timelineTotal?: number
  eventTypeSummary?: SummaryMap
}

export interface ActionStoreOverviewResponse {
  contractVersion?: string
  summary?: SummaryMap
  batchRefs?: string[]
  latestJobs?: ActionJobRecord[]
  latestJobsTotal?: number
}

function unwrapData<T>(payload: unknown): T {
  const obj = payload as { data?: T }
  return (obj?.data ?? payload) as T
}

async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(`动作队列接口读取失败: ${response.status}`)
  }
  return unwrapData<T>(await response.json())
}

async function postJson<T>(url: string, body?: Record<string, unknown>): Promise<T> {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body || {}),
  })
  if (!response.ok) {
    throw new Error(`动作队列写接口失败: ${response.status}`)
  }
  return unwrapData<T>(await response.json())
}

function withQuery(base: string, params: Record<string, string | number | null | undefined>): string {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    search.set(key, String(value))
  })
  const query = search.toString()
  return query ? `${base}?${query}` : base
}

export const actionQueueApi = {
  getDashboard: async (batchRef?: string): Promise<ActionDashboardResponse> => {
    return fetchJson<ActionDashboardResponse>(withQuery('/api/v1/actions/jobs/dashboard', { batchRef }))
  },
  getMetrics: async (batchRef?: string): Promise<ActionMetricsResponse> => {
    return fetchJson<ActionMetricsResponse>(withQuery('/api/v1/actions/jobs/metrics', { batchRef, limit: 10 }))
  },
  getFailureBuckets: async (batchRef?: string): Promise<ActionFailureBucketsResponse> => {
    return fetchJson<ActionFailureBucketsResponse>(withQuery('/api/v1/actions/jobs/failure-buckets', { batchRef, limit: 10 }))
  },
  getWorkerOverview: async (batchRef?: string): Promise<ActionWorkerOverviewResponse> => {
    return fetchJson<ActionWorkerOverviewResponse>(withQuery('/api/v1/actions/worker/overview', { batchRef, limit: 10 }))
  },
  getWorkerStaleJobs: async (batchRef?: string): Promise<ActionWorkerStaleResponse> => {
    return fetchJson<ActionWorkerStaleResponse>(withQuery('/api/v1/actions/worker/stale-jobs', { batchRef, limit: 10 }))
  },
  getWorkerLeaseAudit: async (batchRef?: string, filters?: { workerId?: string; eventType?: string; actionCode?: string }): Promise<ActionWorkerLeaseAuditResponse> => {
    return fetchJson<ActionWorkerLeaseAuditResponse>(withQuery('/api/v1/actions/worker/lease-audit', { batchRef, workerId: filters?.workerId, eventType: filters?.eventType, actionCode: filters?.actionCode, limit: 10 }))
  },
  getWorkerCommandAudit: async (batchRef?: string, filters?: { workerId?: string; eventType?: string; actionCode?: string }): Promise<ActionWorkerCommandAuditResponse> => {
    return fetchJson<ActionWorkerCommandAuditResponse>(withQuery('/api/v1/actions/worker/command-audit', { batchRef, workerId: filters?.workerId, eventType: filters?.eventType, actionCode: filters?.actionCode, limit: 10 }))
  },
  getWorkerCommandAuditDetail: async (eventId: string): Promise<ActionWorkerCommandAuditDetailResponse> => {
    return fetchJson<ActionWorkerCommandAuditDetailResponse>(`/api/v1/actions/worker/command-audit/${eventId}`)
  },
  executeBulkCommand: async (command: string, jobIds: string[], options?: { workerId?: string; reason?: string; note?: string; externalRef?: string }): Promise<ActionBulkCommandResponse> => {
    return postJson<ActionBulkCommandResponse>('/api/v1/actions/worker/bulk-command', {
      command,
      jobIds,
      operator: 'frontend',
      workerId: options?.workerId,
      reason: options?.reason,
      note: options?.note,
      externalRef: options?.externalRef,
    })
  },
  releaseStaleJobs: async (batchRef?: string): Promise<ActionStaleReleaseResponse> => {
    return postJson<ActionStaleReleaseResponse>('/api/v1/actions/worker/release-stale', { batchRef, operator: 'frontend', limit: 10, reason: 'frontend_release_stale' })
  },
  getBulkCommandHistory: async (filters?: { batchRef?: string; command?: string; workerId?: string; actionCode?: string; resultMode?: string; rootBulkCommandId?: string; reexecuteOf?: string; parentBulkCommandId?: string; hasChildren?: string; lineageDepth?: number; selection?: string; reexecuteCommand?: string; commandMode?: string; sourceBulkCommandId?: string; lineageScope?: string; offset?: number; limit?: number }): Promise<ActionBulkCommandHistoryResponse> => {
    return fetchJson<ActionBulkCommandHistoryResponse>(withQuery('/api/v1/actions/worker/bulk-results', { batchRef: filters?.batchRef, command: filters?.command, workerId: filters?.workerId, actionCode: filters?.actionCode, resultMode: filters?.resultMode, rootBulkCommandId: filters?.rootBulkCommandId, reexecuteOf: filters?.reexecuteOf, parentBulkCommandId: filters?.parentBulkCommandId, hasChildren: filters?.hasChildren, lineageDepth: filters?.lineageDepth, selection: filters?.selection, reexecuteCommand: filters?.reexecuteCommand, commandMode: filters?.commandMode, sourceBulkCommandId: filters?.sourceBulkCommandId, lineageScope: filters?.lineageScope, offset: filters?.offset, limit: filters?.limit ?? 10 }))
  },
  getBulkCommandDetail: async (bulkCommandId: string): Promise<ActionBulkCommandDetailResponse> => {
    return fetchJson<ActionBulkCommandDetailResponse>(`/api/v1/actions/worker/bulk-results/${bulkCommandId}`)
  },
  getBulkCommandRelated: async (bulkCommandId: string): Promise<ActionBulkCommandRelatedResponse> => {
    return fetchJson<ActionBulkCommandRelatedResponse>(withQuery(`/api/v1/actions/worker/bulk-results/${bulkCommandId}/related`, { limit: 20 }))
  },
  getBulkCommandTimeline: async (bulkCommandId: string, filters?: { resultMode?: string; eventType?: string; command?: string; actionCode?: string; lineageDepth?: number; commandMode?: string; sourceBulkCommandId?: string; lineageScope?: string; selection?: string; reexecuteCommand?: string; limit?: number }): Promise<ActionBulkCommandTimelineResponse> => {
    return fetchJson<ActionBulkCommandTimelineResponse>(withQuery(`/api/v1/actions/worker/bulk-results/${bulkCommandId}/timeline`, { resultMode: filters?.resultMode, eventType: filters?.eventType, command: filters?.command, actionCode: filters?.actionCode, lineageDepth: filters?.lineageDepth, commandMode: filters?.commandMode, sourceBulkCommandId: filters?.sourceBulkCommandId, lineageScope: filters?.lineageScope, selection: filters?.selection, reexecuteCommand: filters?.reexecuteCommand, limit: filters?.limit ?? 20 }))
  },
  getBulkCommandLineageSummary: async (bulkCommandId: string, filters?: { resultMode?: string; eventType?: string; command?: string; actionCode?: string; lineageDepth?: number; commandMode?: string; sourceBulkCommandId?: string; lineageScope?: string; selection?: string; reexecuteCommand?: string; limit?: number }): Promise<ActionBulkCommandLineageSummaryResponse> => {
    return fetchJson<ActionBulkCommandLineageSummaryResponse>(withQuery(`/api/v1/actions/worker/bulk-results/${bulkCommandId}/lineage-summary`, { resultMode: filters?.resultMode, eventType: filters?.eventType, command: filters?.command, actionCode: filters?.actionCode, lineageDepth: filters?.lineageDepth, commandMode: filters?.commandMode, sourceBulkCommandId: filters?.sourceBulkCommandId, lineageScope: filters?.lineageScope, selection: filters?.selection, reexecuteCommand: filters?.reexecuteCommand, limit: filters?.limit ?? 20 }))
  },
  reexecuteBulkCommand: async (bulkCommandId: string, options?: { selection?: string; command?: string; workerId?: string; reason?: string; note?: string; externalRef?: string }): Promise<ActionBulkCommandResponse> => {
    return postJson<ActionBulkCommandResponse>(`/api/v1/actions/worker/bulk-results/${bulkCommandId}/re-execute`, {
      selection: options?.selection,
      command: options?.command,
      operator: 'frontend',
      workerId: options?.workerId,
      reason: options?.reason,
      note: options?.note,
      externalRef: options?.externalRef,
    })
  },
  executeLineageBulkCommand: async (bulkCommandId: string, options?: { selection?: string; command?: string; scope?: string; workerId?: string; reason?: string; note?: string; externalRef?: string }): Promise<ActionBulkCommandResponse> => {
    return postJson<ActionBulkCommandResponse>(`/api/v1/actions/worker/bulk-results/${bulkCommandId}/lineage-command`, {
      selection: options?.selection,
      command: options?.command,
      scope: options?.scope,
      operator: 'frontend',
      workerId: options?.workerId,
      reason: options?.reason,
      note: options?.note,
      externalRef: options?.externalRef,
    })
  },
  getStoreOverview: async (batchRef?: string): Promise<ActionStoreOverviewResponse> => {
    return fetchJson<ActionStoreOverviewResponse>(withQuery('/api/v1/actions/store/overview', { batchRef, limit: 10 }))
  },
  getJobDetail: async (jobId: string): Promise<ActionJobDetailResponse> => {
    return fetchJson<ActionJobDetailResponse>(`/api/v1/jobs/${jobId}`)
  },
  getJobEvents: async (jobId: string): Promise<ActionJobEventsResponse> => {
    return fetchJson<ActionJobEventsResponse>(`/api/v1/jobs/${jobId}/events`)
  },
  getJobAudit: async (jobId: string): Promise<ActionJobAuditResponse> => {
    return fetchJson<ActionJobAuditResponse>(`/api/v1/actions/jobs/${jobId}/audit`)
  },
}
