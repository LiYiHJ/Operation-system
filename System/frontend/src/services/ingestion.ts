import { importApi } from './api'
import type { BatchSnapshot, ConfirmImportRequest, ConfirmImportResponse, DatasetRegistryItem, ImportResult } from '../types'

export const ingestionApi = {
  getDatasetRegistry: async (): Promise<{ contractVersion?: string; datasets: DatasetRegistryItem[] }> => {
    const data = await importApi.getDatasetRegistry()
    return {
      contractVersion: data?.contractVersion,
      datasets: data?.datasets || [],
    }
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
