export type DatasetKind =
  | 'orders'
  | 'ads'
  | 'reviews'
  | 'refunds_returns'
  | 'inventory_snapshots'
  | 'price_snapshots'
  | 'store_health'
  | 'cost_config'
  | 'execution_results'

export interface DatasetRegistryItem {
  datasetKind: DatasetKind | string
  sourceType: 'file' | 'api' | 'manual' | string
  platform: string
  grain: string
  requiredCoreFields: string[]
  optionalCommonFields: string[]
  loaderTarget: string
  gatePolicy: string
  schemaVersion: string
}
