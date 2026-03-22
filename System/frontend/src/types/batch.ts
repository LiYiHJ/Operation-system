import type { DatasetKind } from './dataset'

export type BatchStatus =
  | 'uploaded'
  | 'parsed'
  | 'mapped'
  | 'validated'
  | 'blocked'
  | 'imported'
  | 'partially_imported'
  | 'failed'

export interface BatchSnapshot {
  contractVersion: string
  datasetKind: DatasetKind | string
  batchStatus: BatchStatus | string
  transportStatus: 'passed' | 'failed' | string
  semanticStatus: 'passed' | 'risk' | 'failed' | string
  importabilityStatus: 'passed' | 'risk' | 'failed' | string
  quarantineCount: number
  importedRows: number
  mappingSummary?: {
    mappedCanonicalFields?: string[]
    mappedConfidence?: number
    mappedCount?: number
    mappingCoverage?: number
    topUnmappedHeaders?: string[]
    unmappedCount?: number
  }
  auditSummary?: Record<string, any>
}

export interface WorkspaceBatchTimelineItem {
  eventType?: string
  status?: string
  finalStatus?: string
  batchStatus?: string
  importabilityStatus?: string
  importedRows?: number
  quarantineCount?: number
  recordedAt?: string
  reasons?: string[]
}

export interface WorkspaceBatchListItem {
  workspaceBatchId?: string
  dbBatchId?: number
  sessionId: number
  datasetKind?: DatasetKind | string
  importProfile?: string
  fileName?: string
  sourceMode?: string
  shopId?: number
  operator?: string
  createdAt?: string
  updatedAt?: string
  batchStatus?: BatchStatus | string
  transportStatus?: string
  semanticStatus?: string
  importabilityStatus?: string
  importedRows?: number
  quarantineCount?: number
}

export interface WorkspaceBatchDetail extends WorkspaceBatchListItem {
  parseSnapshot?: BatchSnapshot | null
  confirmSnapshot?: BatchSnapshot | null
  finalSnapshot?: BatchSnapshot | null
  parseResultMeta?: {
    totalRows?: number
    totalColumns?: number
    status?: string
    finalStatus?: string
    mappedCount?: number
    unmappedCount?: number
    mappingCoverage?: number
    mappedConfidence?: number
    selectedSheet?: string
  }
  confirmResultMeta?: {
    status?: string
    importedRows?: number
    errorRows?: number
    quarantineCount?: number
    factLoadErrors?: number
  }
  timeline?: WorkspaceBatchTimelineItem[]
}
