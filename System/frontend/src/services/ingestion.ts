import { importApi } from './api'
import type {
  BatchSnapshot,
  ConfirmImportRequest,
  ConfirmImportResponse,
  DatasetRegistryItem,
  ImportResult,
  WorkspaceBatchDetail,
  WorkspaceBatchListItem,
} from '../types'

export const ingestionApi = {
  getDatasetRegistry: async (): Promise<{ contractVersion?: string; datasets: DatasetRegistryItem[] }> => {
    const data = await importApi.getDatasetRegistry()
    return {
      contractVersion: data?.contractVersion,
      datasets: data?.datasets || [],
    }
  },

  listBatches: async (
    limit = 20,
  ): Promise<{ contractVersion?: string; source?: string; total?: number; items: WorkspaceBatchListItem[] }> => {
    const response = await fetch(`/api/import/batches?limit=${encodeURIComponent(String(limit))}`)
    if (!response.ok) {
      throw new Error(`批次列表读取失败: ${response.status}`)
    }
    const data = await response.json()
    return {
      contractVersion: data?.contractVersion,
      source: data?.source,
      total: data?.total,
      items: data?.items || [],
    }
  },

  getBatch: async (sessionId: number): Promise<WorkspaceBatchDetail> => {
    const response = await fetch(`/api/import/batches/${encodeURIComponent(String(sessionId))}`)
    if (!response.ok) {
      throw new Error(`批次详情读取失败: ${response.status}`)
    }
    return response.json()
  },

  uploadFile: async (
    file: File,
    shopId: number,
    options?: { datasetKind?: string; importProfile?: string },
    onProgress?: (progress: number) => void,
  ): Promise<ImportResult & { batchSnapshot?: BatchSnapshot }> => {
    return importApi.uploadFile(file, shopId, onProgress, options)
  },

  confirmImport: async (
    data: ConfirmImportRequest & { datasetKind?: string; importProfile?: string },
  ): Promise<ConfirmImportResponse & { batchSnapshot?: BatchSnapshot }> => {
    return importApi.confirmImport(data)
  },
}
