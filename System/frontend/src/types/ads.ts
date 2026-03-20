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
