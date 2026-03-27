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
  summary: Record<string, any>
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
