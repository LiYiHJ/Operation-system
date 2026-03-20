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
    todaySummary?: Record<string, any>
    mustHandleToday?: any[]
    recentChanges?: Record<string, any>
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
