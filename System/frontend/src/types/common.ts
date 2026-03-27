// ========== 通用类型 ==========
export interface ApiResponse<T = any> {
  success: boolean
  data: T
  error?: string
}

// ========== 通用工具类型 ==========
export type StatusType = 'pending' | 'in_progress' | 'completed' | 'cancelled'
export type PriorityType = 'P0' | 'P1' | 'P2' | 'P3'
export type StrategyType = 'pricing' | 'inventory' | 'conversion' | 'ads' | 'risk_control'
