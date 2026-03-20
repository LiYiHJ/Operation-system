import React from 'react'
import { Progress, Tag } from 'antd'
import type { UploadFile } from 'antd/es/upload/interface'
import type {
  ConfirmImportResponse,
  EntityKeySuggestion,
  FieldMapping,
  ImportResult,
} from '../../types'

export const SHOP_ID = 1
export const UNMAPPED_VALUE = '__UNMAPPED__'

export type StandardFieldConfig = {
  name: string
  category: string
  required?: boolean
  description?: string
}

export type SavedTemplate = {
  name: string
  platform: string
  mappings: FieldMapping[]
  createdAt: string
}

export const STANDARD_FIELDS: Record<string, StandardFieldConfig> = {
  sku: { name: 'SKU', category: '基础', required: true, description: '商品唯一标识' },
  product_name: { name: '商品名称', category: '基础' },
  category: { name: '类目', category: '基础' },
  orders: { name: '订单数', category: '销售' },
  revenue: { name: '销售额', category: '销售' },
  order_amount: { name: '订单金额', category: '销售' },
  units: { name: '销量', category: '销售' },
  impressions_total: { name: '总曝光', category: '流量' },
  impressions_search_catalog: { name: '搜索/目录曝光', category: '流量' },
  clicks: { name: '点击量', category: '流量' },
  product_card_visits: { name: '商品卡访问', category: '流量' },
  add_to_cart_total: { name: '总加购', category: '转化' },
  conversion_rate: { name: '转化率', category: '转化' },
  avg_sale_price: { name: '平均销售价', category: '价格' },
  price_index_status: { name: '价格指数状态', category: '价格' },
  stock_total: { name: '总库存', category: '库存' },
  rating_value: { name: '评分值', category: '评价' },
  review_count: { name: '评论数', category: '评价' },
  ad_spend: { name: '广告花费', category: '广告' },
  ad_revenue: { name: '广告收入', category: '广告' },
  cost_price: { name: '成本价', category: '成本' },
}

export const PROTECTED_TARGETS = new Set([
  'sku',
  'orders',
  'order_amount',
  'impressions_total',
  'impressions_search_catalog',
  'product_card_visits',
  'add_to_cart_total',
  'stock_total',
  'rating_value',
  'review_count',
  'price_index_status',
])

export const findProtectedTargetConflicts = (mappings: FieldMapping[]) => {
  const grouped = new Map<string, FieldMapping[]>()
  for (const item of mappings || []) {
    const target = item?.standardField || null
    if (!target || !PROTECTED_TARGETS.has(target)) continue
    if (!grouped.has(target)) grouped.set(target, [])
    grouped.get(target)!.push(item)
  }
  return [...grouped.entries()].filter(([, items]) => items.length > 1)
}

export const isMappedField = (m?: Pick<FieldMapping, 'standardField'> | null) =>
  !!m?.standardField && m.standardField !== 'unmapped'

export const isIgnoredField = (m?: FieldMapping | null) =>
  m?.dynamicCompanion === true ||
  m?.excludeFromSemanticGate === true ||
  !!m?.reasons?.includes('dynamic_column_ignored') ||
  !!m?.reasons?.includes('dynamic_companion') ||
  m?.mappingSource === 'dynamic_companion'

export const renderGateTag = (status?: 'passed' | 'risk' | 'failed') => {
  if (status === 'passed') return <Tag color="success">passed</Tag>
  if (status === 'risk') return <Tag color="warning">risk</Tag>
  if (status === 'failed') return <Tag color="error">failed</Tag>
  return <Tag>n/a</Tag>
}

export const normalizeRawFile = (uploadFile?: UploadFile): File | null => {
  if (!uploadFile) return null
  const raw = uploadFile.originFileObj
  return raw instanceof File ? raw : null
}

export const getSuggestionOverride = (
  suggestion: EntityKeySuggestion | null,
): FieldMapping | null => {
  if (!suggestion?.field || !suggestion?.sourceColumn) return null
  return {
    originalField: suggestion.sourceColumn,
    normalizedField: suggestion.sourceColumn.toLowerCase(),
    standardField: suggestion.field,
    mappingSource: 'manual_override',
    confidence: 1.0,
    sampleValues: suggestion.sampleToken ? [suggestion.sampleToken] : [],
    isManual: true,
    reasons: ['entity_key_suggestion_confirmed'],
    reason: 'entity_key_suggestion_confirmed',
    sampleToken: suggestion.sampleToken || undefined,
  }
}

const tryParseJson = (value: any) => {
  if (typeof value !== 'string') return value
  try {
    return JSON.parse(value)
  } catch {
    return value
  }
}

const unwrapPayload = (raw: any) => {
  const parsedRaw = tryParseJson(raw)
  const candidate = parsedRaw?.data ?? parsedRaw?.result ?? parsedRaw ?? {}
  return tryParseJson(candidate)
}

export const normalizeFieldMappings = (value: any): FieldMapping[] => {
  if (!Array.isArray(value)) return []
  return value.map((item: any) => ({
    originalField: item?.originalField ?? item?.original_field ?? '',
    normalizedField: item?.normalizedField ?? item?.normalized_field ?? undefined,
    standardField: item?.standardField ?? item?.standard_field ?? null,
    mappingSource: item?.mappingSource ?? item?.mapping_source ?? undefined,
    confidence: Number(item?.confidence ?? 0),
    sampleValues: Array.isArray(item?.sampleValues)
      ? item.sampleValues
      : Array.isArray(item?.sample_values)
      ? item.sample_values
      : [],
    isManual: Boolean(item?.isManual ?? item?.is_manual ?? false),
    reasons: Array.isArray(item?.reasons) ? item.reasons : [],
    reason: item?.reason ?? undefined,
    sampleToken: item?.sampleToken ?? item?.sample_token ?? undefined,
    dynamicCompanion: item?.dynamicCompanion ?? item?.dynamic_companion ?? false,
    excludeFromSemanticGate:
      item?.excludeFromSemanticGate ?? item?.exclude_from_semantic_gate ?? false,
  }))
}

export const normalizeImportResult = (raw: any): ImportResult => {
  const payload = unwrapPayload(raw)
  return {
    status: payload?.status ?? 'success',
    sessionId: Number(payload?.sessionId ?? payload?.session_id ?? 0),
    fileName: payload?.fileName ?? payload?.file_name ?? payload?.filename ?? '',
    platform: payload?.platform ?? '',
    headerRow: Number(payload?.headerRow ?? payload?.header_row ?? 0),
    totalRows: Number(payload?.totalRows ?? payload?.total_rows ?? 0),
    totalColumns: Number(payload?.totalColumns ?? payload?.total_columns ?? 0),
    rawColumns: Number(
      payload?.rawColumns ??
        payload?.raw_columns ??
        payload?.totalColumns ??
        payload?.total_columns ??
        0,
    ),
    fieldMappings: normalizeFieldMappings(payload?.fieldMappings ?? payload?.field_mappings),
    stats: payload?.stats ?? {},
    transportStatus: payload?.transportStatus ?? payload?.transport_status,
    semanticStatus: payload?.semanticStatus ?? payload?.semantic_status,
    finalStatus: payload?.finalStatus ?? payload?.final_status,
    semanticGateReasons:
      payload?.semanticGateReasons ?? payload?.semantic_gate_reasons ?? [],
    semanticAcceptanceReason:
      payload?.semanticAcceptanceReason ??
      payload?.semantic_acceptance_reason ??
      [],
    entityKeySuggestion:
      payload?.entityKeySuggestion ?? payload?.entity_key_suggestion ?? null,
    mappedCount: Number(payload?.mappedCount ?? payload?.mapped_count ?? 0),
    unmappedCount: Number(payload?.unmappedCount ?? payload?.unmapped_count ?? 0),
    mappingCoverage: Number(
      payload?.mappingCoverage ?? payload?.mapping_coverage ?? 0,
    ),
    ...payload,
  } as ImportResult
}

export const normalizeConfirmResult = (raw: any): ConfirmImportResponse => {
  const payload = unwrapPayload(raw)
  return {
    status: payload?.status ?? 'success',
    importedRows: Number(payload?.importedRows ?? payload?.imported_rows ?? 0),
    quarantineCount: Number(payload?.quarantineCount ?? payload?.quarantine_count ?? 0),
    duplicateCount: Number(payload?.duplicateCount ?? payload?.duplicate_count ?? 0),
    missingRatingCount: Number(payload?.missingRatingCount ?? payload?.missing_rating_count ?? 0),
    importabilityStatus: payload?.importabilityStatus ?? payload?.importability_status,
    importabilityReasons: payload?.importabilityReasons ?? payload?.importability_reasons ?? [],
    semanticStatus: payload?.semanticStatus ?? payload?.semantic_status,
    finalStatus: payload?.finalStatus ?? payload?.final_status,
    ratingIssueSamples: Array.isArray(payload?.ratingIssueSamples)
      ? payload.ratingIssueSamples
      : Array.isArray(payload?.rating_issue_samples)
      ? payload.rating_issue_samples
      : [],
    errors: Array.isArray(payload?.errors) ? payload.errors : [],
    ...payload,
  } as ConfirmImportResponse
}

export const isValidNumber = (value: unknown): value is number =>
  typeof value === 'number' && Number.isFinite(value)

export const buildDisplayStats = (result: ImportResult | null) => {
  const mappings = Array.isArray(result?.fieldMappings) ? result!.fieldMappings : []
  const candidateMappings = mappings.filter((m) => !isIgnoredField(m))
  const mappedCountFromMappings = candidateMappings.filter(isMappedField).length
  const unmappedCountFromMappings = candidateMappings.length - mappedCountFromMappings
  const coverageFromMappings = mappedCountFromMappings / Math.max(candidateMappings.length, 1)
  const mappedConfidenceFromMappings =
    mappedCountFromMappings > 0
      ? candidateMappings
          .filter(isMappedField)
          .reduce((acc, cur) => acc + (cur.confidence || 0), 0) / mappedCountFromMappings
      : 0

  const backendMappedCount = Number(
    (result as any)?.mappedCount ?? (result as any)?.mapped_count ?? Number.NaN,
  )
  const backendUnmappedCount = Number(
    (result as any)?.unmappedCount ?? (result as any)?.unmapped_count ?? Number.NaN,
  )
  const backendMappingCoverage = Number(
    (result as any)?.mappingCoverage ?? (result as any)?.mapping_coverage ?? Number.NaN,
  )
  const backendMappedConfidence = Number(
    (result as any)?.semanticMetrics?.mappedConfidence ?? Number.NaN,
  )

  const hasManualEdits = mappings.some((m) => m.isManual)

  const mappedCount =
    !hasManualEdits && isValidNumber(backendMappedCount)
      ? backendMappedCount
      : mappedCountFromMappings

  const unmappedCount =
    !hasManualEdits && isValidNumber(backendUnmappedCount)
      ? backendUnmappedCount
      : unmappedCountFromMappings

  const mappingCoverage = Number(
    (
      !hasManualEdits && isValidNumber(backendMappingCoverage)
        ? backendMappingCoverage
        : coverageFromMappings
    ).toFixed(3),
  )

  const mappedConfidence = Number(
    (
      !hasManualEdits && isValidNumber(backendMappedConfidence)
        ? backendMappedConfidence
        : mappedConfidenceFromMappings
    ).toFixed(3),
  )

  return {
    mappedCount,
    unmappedCount,
    mappingCoverage,
    mappedConfidence,
    rawColumns: Number(result?.rawColumns ?? result?.totalColumns ?? 0),
  }
}

export const renderMappingConfidence = (val: number) => (
  <Progress
    percent={(val || 0) * 100}
    size="small"
    status={val > 0.7 ? 'success' : val > 0.4 ? 'normal' : 'exception'}
    format={(percent) => `${percent?.toFixed(0)}%`}
  />
)
