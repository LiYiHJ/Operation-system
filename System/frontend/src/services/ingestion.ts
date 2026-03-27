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

type JsonObject = Record<string, any>

function unwrapData<T>(payload: any): T {
  return (payload?.data ?? payload) as T
}

async function fetchJsonWithFallback<T>(
  primaryUrl: string,
  fallbackUrl: string | null,
  errorLabel: string,
): Promise<T> {
  const primaryResponse = await fetch(primaryUrl)
  if (primaryResponse.ok) {
    return unwrapData<T>(await primaryResponse.json())
  }

  if (fallbackUrl) {
    const fallbackResponse = await fetch(fallbackUrl)
    if (fallbackResponse.ok) {
      return (await fallbackResponse.json()) as T
    }
  }

  throw new Error(`${errorLabel}: ${primaryResponse.status}`)
}

export const ingestionApi = {
  getDatasetRegistry: async (): Promise<{ contractVersion?: string; datasets: DatasetRegistryItem[] }> => {
    const data = await fetchJsonWithFallback<{ contractVersion?: string; datasets?: DatasetRegistryItem[] }>(
      '/api/v1/registry/datasets',
      '/api/import/dataset-registry',
      '数据集注册表读取失败',
    )
    return {
      contractVersion: data?.contractVersion,
      datasets: data?.datasets || [],
    }
  },

  listBatches: async (
    limit = 20,
  ): Promise<{ contractVersion?: string; source?: string; total?: number; items: WorkspaceBatchListItem[] }> => {
    const query = `limit=${encodeURIComponent(String(limit))}`
    const data = await fetchJsonWithFallback<{ contractVersion?: string; source?: string; total?: number; items?: WorkspaceBatchListItem[] }>(
      `/api/v1/batches?${query}`,
      `/api/import/batches?${query}`,
      '批次列表读取失败',
    )
    return {
      contractVersion: data?.contractVersion,
      source: data?.source,
      total: data?.total,
      items: data?.items || [],
    }
  },

  getBatch: async (sessionId: number): Promise<WorkspaceBatchDetail> => {
    return fetchJsonWithFallback<WorkspaceBatchDetail>(
      `/api/v1/batches/${encodeURIComponent(String(sessionId))}`,
      `/api/import/batches/${encodeURIComponent(String(sessionId))}`,
      '批次详情读取失败',
    )
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
