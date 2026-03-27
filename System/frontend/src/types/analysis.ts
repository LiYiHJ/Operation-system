// ========== Analysis 相关类型 ==========
import type { StrategyTask } from './strategy'

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
  stages: { name: string; count: number; rate: number }[]
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
