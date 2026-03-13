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

export interface ImportResult {
  sessionId: number
  fileName: string
  fileSize: number
  sheetNames: string[]
  selectedSheet: string
  totalRows: number
  totalColumns: number
  rawColumns?: number
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
    droppedPlaceholderColumns: string[]
    removedSummaryRows: number
    removedDescriptionRows: number
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
}

export interface FieldMapping {
  originalField: string
  standardField: string | null
  confidence: number
  sampleValues: any[]
  isManual: boolean
  reasons?: string[]
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
