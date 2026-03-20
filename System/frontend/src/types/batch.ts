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
}
