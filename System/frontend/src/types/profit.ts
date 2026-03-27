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
