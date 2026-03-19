/**
 * 类型定义中心
 * 统一管理所有 TypeScript 接口和类型
 */

// ========== 通用类型 ==========

export interface ApiResponse<T = any> {
  success: boolean
  data: T
  error?: string
}

// ========== Dashboard 相关类型 ==========

export interface DashboardMetrics {
  totalRevenue: number
  totalOrders: number
  avgOrderValue: number
  profitMargin: number
  totalProducts: number
  totalImpressions: number
  totalClicks: number
  avgCtr: number
  avgRating: number
  period: {
    start: string
    end: string
  }
  kpiDeltas?: {
    revenue?: number | null
    orders?: number | null
    avgOrderValue?: number | null
  }
  openingWorkbench?: {
    todaySummary?: Record<string, number>
    mustHandleToday?: any[]
    recentChanges?: Record<string, any[]>
  }
  topSkus: TopSku[]
  alerts: Alert[]
  trends: TrendData
}

export interface TopSku {
  sku: string
  productName?: string
  revenue: number
  orders: number
  margin: number
  abcClass: string
  trend?: 'up' | 'down' | 'stable'
}

export interface Alert {
  id?: number
  type: 'P0' | 'P1' | 'P2' | 'P3'
  message: string
  sku: string
  timestamp?: string
}

export interface TrendData {
  dates: string[]
  revenue: number[]
  orders: number[]
  impressions?: number[]
}

export interface ShopHealth {
  shopId: number
  shopName: string
  rating: number
  delayRate: number
  priceCompetitiveness: {
    green: number
    red: number
  }
  totalOrders: number
  totalProducts: number
}
// ========== Import 相关类型 ==========

export type ImportSessionStatus = 'success' | 'partial' | 'failed' | 'draft' | 'processing' | 'uploaded'

export interface ImportDiagnosis {
  suggestions: string[]
  keyField: string | null
  unmappedFields: string[]
  status: 'success' | 'partial' | 'failed'
}

export interface EntityKeySuggestion {
  field: string
  confidence: number
  sourceHeader?: string | null
  sourceColumn?: string | null
  sampleToken?: string | null
  detectedBy?: string | null
  rawCandidate?: string | null
}

export interface ImportResult {
  sessionId: number
  fileName: string
  fileSize: number
  sheetNames: string[]
  selectedSheet: string
  totalRows: number
  totalColumns: number
  rawColumns?: number
  normalizedColumns?: number
  readerEngineUsed?: string | null
  readerFallbackStage?: string | null
  fieldRegistryVersion?: string
  headerRow: number
  dataPreview: any[][]
  platform: string
  fieldMappings: FieldMapping[]
  mappedCount: number
  unmappedCount: number
  confidence: number
  stats?: {
    candidateColumns: number
    ignoredColumns: number
    ignoredFields: string[]
    mappedConfidence: number
    mappingCoverage: number
    mappedCount?: number
    unmappedCount?: number
    correctlyMappedCount?: number
    wronglyMappedCount?: number
    ruUnmappedCount?: number
    ruMappingPass?: boolean
    droppedPlaceholderColumns: string[]
    removedSummaryRows: number
    removedDescriptionRows: number
  }
  ruMappingQuality?: {
    correctlyMappedCount: number
    wronglyMappedCount: number
    unmappedCount: number
    goldenTotal: number
    pass: boolean
    details: Array<{
      originalField: string
      expectedCanonical: string
      expectedFactTarget: string
      actualCanonical: string | null
      status: 'correct' | 'wrong' | 'unmapped'
    }>
  }
  transportStatus?: 'passed' | 'failed'
  semanticStatus?: 'passed' | 'risk' | 'failed'
  finalStatus?: 'passed' | 'risk' | 'failed'
  semanticGateReasons?: string[]
  riskOverrideReasons?: string[]
  semanticAcceptanceReason?: string[]
  semanticMetrics?: {
    mappedCount?: number
    unmappedCount?: number
    candidateColumns?: number
    mappingCoverage?: number
    mappedConfidence?: number
    correctlyMappedCount?: number
    wronglyMappedCount?: number
  }
  coreFieldHitSummary?: {
    sku?: boolean
    orders_or_order_amount?: boolean
    impressions_total?: boolean
    product_card_visits_or_add_to_cart_total?: boolean
    optionalFieldPool?: string[]
    optionalHitCount?: number
    optionalHitFields?: string[]
    mappedTargets?: string[]
  }
  headerBlock?: {
    startRow: number
    endRow: number
    confidence: number
    signals?: string[]
  }
  flattenedHeaders?: string[]
  headerRecoveryApplied?: boolean
  headerStructureScore?: number
  headerStructureRiskSignals?: string[]
  droppedPlaceholderColumns?: string[]
  rescuedPlaceholderColumns?: string[]
  preRecoveryStatus?: 'passed' | 'risk' | 'failed'
  postRecoveryStatus?: 'passed' | 'risk' | 'failed'
  recoveryAttempted?: boolean
  recoveryImproved?: boolean
  sampleHint?: string | null
  entityKeySuggestion?: EntityKeySuggestion
  recoveryDiff?: {
    mappedCount_before: number
    mappedCount_after: number
    unmappedCount_before: number
    unmappedCount_after: number
    mappingCoverage_before: number
    mappingCoverage_after: number
    coreFieldHit_before: number
    coreFieldHit_after: number
  }
  status: ImportSessionStatus
  diagnosis: ImportDiagnosis
}

export interface ConfirmImportRequest {
  sessionId: number
  shopId: number
  manualOverrides: FieldMapping[]
  operator?: string
}

export interface ConfirmImportResponse {
  sessionId: number
  batchId: number
  importedRows: number
  errorRows: number
  status: 'success' | 'failed' | 'processing'
  warnings: string[]
  errors: string[]
  rowErrorSummary?: {
    auto_fixed: number
    ignorable: number
    quarantined: number
    fatal: number
  }
  quarantineCount?: number
  stagingRows?: number
  factLoadErrors?: number
  missingRatingCount?: number
  ratingIssueSamples?: Array<{
    row?: number
    ratingValue?: any
    ratingSourceColumn?: string | null
    ratingSourceRawValue?: any
    error?: string
  }>
  transportStatus?: 'passed' | 'failed'
  semanticStatus?: 'passed' | 'risk' | 'failed'
  finalStatus?: 'passed' | 'risk' | 'failed'
  importabilityStatus?: 'passed' | 'risk' | 'failed'
  importabilityReasons?: string[]
  semanticGateReasons?: string[]
  riskOverrideReasons?: string[]
  semanticAcceptanceReason?: string[]
  recoverySummary?: {
    headerRecoveryApplied?: boolean
    preRecoveryStatus?: 'passed' | 'risk' | 'failed'
    postRecoveryStatus?: 'passed' | 'risk' | 'failed'
    recoveryAttempted?: boolean
    recoveryImproved?: boolean
    semanticGateReasons?: string[]
    riskOverrideReasons?: string[]
    recoveryDiff?: Record<string, any>
  }
}

export interface FieldMapping {
  originalField: string
  normalizedField?: string
  standardField: string | null
  mappingSource?: string
  confidence: number
  sampleValues: any[]
  isManual: boolean
  reasons?: string[]
  reason?: string
  sampleToken?: string
  dynamicCompanion?: boolean
  excludeFromSemanticGate?: boolean
}

export interface FieldRegistryField {
  canonical: string
  aliases: Record<string, string[]>
  type: string
  unit?: string | null
  enumValues?: string[]
  validator?: string
  factTarget?: string
  displayLabel?: string
}

export interface FieldRegistryResponse {
  version: string
  fields: FieldRegistryField[]
}

// ========== Analysis 相关类型 ==========

export interface SkuAnalysis {
  sku: string
  funnel: {
    ctr: number
    add_to_cart_rate: number
    order_rate: number
  }
  netProfit: number
  netMargin: number
  breakEvenPrice: number
  discountSimulations: DiscountSimulation[]
  strategyTasks: StrategyTask[]
}

export interface DiscountSimulation {
  discount: number
  finalPrice: number
  profit: number
  margin: number
  roi: number
}

export interface AbcAnalysis {
  summary: {
    A: { count: number; revenue: number; percentage: number }
    B: { count: number; revenue: number; percentage: number }
    C: { count: number; revenue: number; percentage: number }
  }
  topProducts: any[]
  abcDistribution: any
}

export interface FunnelAnalysis {
  stages: {
    name: string
    count: number
    rate: number
  }[]
  skuBreakdown: any[]
}

export interface PriceAnalysis {
  products: {
    sku: string
    currentPrice: number
    marketPrice: number
    priceGap: number
    competitiveness: 'green' | 'yellow' | 'red'
  }[]
  summary: {
    green: number
    yellow: number
    red: number
  }
}

export interface InventoryAnalysis {
  products: {
    sku: string
    stock: number
    daysOfSupply: number
    reorderPoint: number
    status: 'normal' | 'warning' | 'critical'
  }[]
  summary: {
    total: number
    warning: number
    critical: number
  }
}

// ========== Strategy 相关类型 ==========

export interface StrategyTask {
  id?: string
  sku: string
  strategyType: 'pricing' | 'inventory' | 'conversion' | 'ads' | 'risk_control'
  priority: 'P0' | 'P1' | 'P2' | 'P3'
  issueSummary: string
  recommendedAction: string
  observationMetrics: string[]
  status: 'pending' | 'in_progress' | 'completed' | 'cancelled'
  assignee?: string
  dueDate?: string
  createdAt?: string
  completedAt?: string
  impact?: number
  urgency?: number
}

export interface StrategyListResponse {
  tasks: StrategyTask[]
  summary: Record<string, number>
}

export interface DecisionInput {
  shopId: number
  date?: string
  scope: 'all' | 'high_priority' | 'low_hanging_fruit'
}

export interface DecisionOutput {
  decisions: {
    sku: string
    action: string
    expectedImpact: number
    confidence: number
    priority: number
  }[]
}

// ========== Profit Calculator 相关类型 ==========

export interface ProfitInput {
  mode: 'current' | 'target_profit' | 'target_margin' | 'target_roi'
  sale_price?: number
  list_price: number
  variable_rate_total: number
  fixed_cost_total: number
  target_value?: number
}

export interface ProfitResult {
  sale_price: number
  list_price: number
  discount: number
  revenue: number
  variable_cost: number
  fixed_cost: number
  total_cost: number
  net_profit: number
  net_margin: number
  roi: number
  break_even_price: number
  is_loss: boolean
}

export interface CostBreakdown {
  category: string
  amount: number
  percentage: number
  description: string
}


export interface CostComponentDefinition {
  code: string
  label: string
  allocLevel: 'order' | 'order_line' | 'sku' | 'shop'
  sourceMode: Array<'api' | 'import' | 'rule' | 'manual'>
  requiredPhase: 'P0' | 'P1' | 'P2' | 'P3' | 'P4'
  mutable: boolean
}

export interface ProfitMetricDefinition {
  code: string
  label: string
  phase: 'P0' | 'P1' | 'P2' | 'P3' | 'P4'
  strategyConsumable?: boolean
  dependsOn?: string[]
}

export interface PricingFieldDefinition {
  code: 'floor_price' | 'target_price' | 'ceiling_price'
  label: string
  phase: 'P0' | 'P1' | 'P2' | 'P3' | 'P4'
}

export interface CostComponentRegistryResponse {
  version: string
  count: number
  components: CostComponentDefinition[]
}

export interface ProfitMetricRegistryResponse {
  version: string
  metricCount: number
  pricingFieldCount: number
  metrics: ProfitMetricDefinition[]
  pricingFields: PricingFieldDefinition[]
}

export interface ProfitRegistrySummary {
  costRegistryVersion?: string
  metricRegistryVersion?: string
  costComponentCount: number
  metricCount: number
  pricingFieldCount: number
  strategyConsumableMetrics: string[]
  phaseBuckets: {
    costComponents: Record<string, number>
    metrics: Record<string, number>
    pricingFields: Record<string, number>
  }
}

// ========== Ads 相关类型 ==========


export interface AdCampaign {
  id: string
  name: string
  type: 'search' | 'display' | 'product'
  status: 'active' | 'paused' | 'ended'
  budget: number
  spent: number
  impressions: number
  clicks: number
  ctr: number
  conversions: number
  revenue: number
  roi: number
  acos: number
}

// ========== 通用工具类型 ==========

export type StatusType = 'pending' | 'in_progress' | 'completed' | 'cancelled'
export type PriorityType = 'P0' | 'P1' | 'P2' | 'P3'
export type StrategyType = 'pricing' | 'inventory' | 'conversion' | 'ads' | 'risk_control'