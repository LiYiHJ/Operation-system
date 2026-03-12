/**
 * API 服务层
 * 封装所有后端 API 调用
 * 
 * 设计原则：
 * 1. 优先调用真实后端 API
 * 3. 所有类型定义从 @/types 导入
 */

import axios from 'axios'
import type {
  ApiResponse,
  DashboardMetrics,
  TopSku,
  Alert,
  TrendData,
  ShopHealth,
  ImportResult,
  ConfirmImportRequest,
  ConfirmImportResponse,
  SkuAnalysis,
  AbcAnalysis,
  FunnelAnalysis,
  PriceAnalysis,
  InventoryAnalysis,
  StrategyTask,
  StrategyListResponse,
  DecisionInput,
  DecisionOutput,
  ProfitResult,
  AdCampaign
} from '../types'

// ========== API 基础配置 ==========

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

// 创建 axios 实例
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // TODO: 添加认证 token
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    // 直接返回 response.data（后端返回格式：{ success, data, error }）
    return response.data
  },
  (error) => {
    // 统一错误处理
    const message = error.response?.data?.error || error.message || '请求失败'
    console.error('API Error:', message)
    return Promise.reject(new Error(message))
  }
)

// ========== Dashboard API ==========

export const dashboardApi = {
  /**
   * 获取仪表盘总览数据
   */
  getOverview: async (): Promise<DashboardMetrics> => {
    return apiClient.get('/dashboard/overview')
  },

  /**
   * 获取仪表盘关键指标
   */
  getMetrics: (params?: {
    shop_id?: number
    start_date?: string
    end_date?: string
  }): Promise<ApiResponse<DashboardMetrics>> => {
    return apiClient.get('/dashboard/metrics', { params })
  },

  /**
   * 获取 Top SKU 列表
   */
  getTopSkus: (params?: {
    limit?: number
    sort_by?: string
  }): Promise<ApiResponse<TopSku[]>> => {
    return apiClient.get('/dashboard/top-skus', { params })
  },

  /**
   * 获取告警列表
   */
  getAlerts: (params?: {
    priority?: string
    limit?: number
  }): Promise<ApiResponse<{ data: Alert[]; summary: Record<string, number> }>> => {
    return apiClient.get('/dashboard/alerts', { params })
  },

  /**
   * 获取趋势数据
   */
  getTrends: (params?: {
    metric?: string
    days?: number
  }): Promise<ApiResponse<TrendData>> => {
    return apiClient.get('/dashboard/trends', { params })
  },

  /**
   * 获取店铺健康度
   */
  getShopHealth: (params?: {
    shop_id?: number
  }): Promise<ApiResponse<ShopHealth[]>> => {
    return apiClient.get('/dashboard/shop-health', { params })
  },
}

// ========== Import API ==========

export const importApi = {
  /**
   * 上传并解析文件
   */
  uploadFile: (
    file: File,
    shopId: number,
    onProgress?: (progress: number) => void
  ): Promise<ImportResult> => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('shop_id', shopId.toString())

    return apiClient.post('/import/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = (progressEvent.loaded / progressEvent.total) * 100
          onProgress(progress)
        }
      },
    })
  },

  /**
   * 确认导入
   */
  confirmImport: (data: ConfirmImportRequest): Promise<ConfirmImportResponse> => {
    return apiClient.post('/import/confirm', data)
  },

  /**
   * 获取字段映射模板
   */
  getTemplate: (): Promise<ApiResponse<{
    standardFields: any
    savedTemplates: any[]
  }>> => {
    return apiClient.get('/import/template')
  },
}

// ========== Analysis API ==========

export const analysisApi = {
  /**
   * 单 SKU 分析
   */
  analyzeSku: (sku: string, params?: {
    shop_id?: number
    date?: string
  }): Promise<ApiResponse<SkuAnalysis>> => {
    return apiClient.get(`/analysis/sku/${sku}`, { params })
  },

  /**
   * ABC 分析
   */
  abcAnalysis: (params?: {
    shop_id?: number
    start_date?: string
    end_date?: string
    category?: string
  }): Promise<ApiResponse<AbcAnalysis>> => {
    return apiClient.get('/analysis/abc', { params })
  },

  /**
   * 漏斗分析
   */
  funnelAnalysis: (params?: {
    shop_id?: number
    start_date?: string
    end_date?: string
  }): Promise<ApiResponse<FunnelAnalysis>> => {
    return apiClient.get('/analysis/funnel', { params })
  },

  /**
   * 价格分析
   */
  priceAnalysis: (params?: {
    shop_id?: number
  }): Promise<ApiResponse<PriceAnalysis>> => {
    return apiClient.get('/analysis/price', { params })
  },

  /**
   * 库存分析
   */
  inventoryAnalysis: (params?: {
    shop_id?: number
  }): Promise<ApiResponse<InventoryAnalysis>> => {
    return apiClient.get('/analysis/inventory', { params })
  },

  /**
   * 利润计算
   */
  calculateProfit: (data: {
    salePrice: number
    listPrice: number
    variableRateTotal: number
    fixedCostTotal: number
  }): Promise<ApiResponse<ProfitResult>> => {
    return apiClient.post('/analysis/profit', data)
  },
}



// ========== Profit API ==========

export const profitApi = {
  getProfiles: (): Promise<any> => {
    return apiClient.get('/profit/profiles')
  },

  solve: (data: {
    mode: string
    targetValue: number
    salePrice: number
    listPrice: number
    variableRateTotal: number
    fixedCostTotal: number
    algorithmProfile?: string
    layeredParams?: any
    scenarios?: any[]
  }): Promise<any> => {
    return apiClient.post('/profit/solve', data)
  },

  saveSnapshot: (data: {
    shopId: number
    snapshotName: string
    algorithmProfile: string
    payload: any
    result: any
    operator?: string
  }): Promise<any> => {
    return apiClient.post('/profit/snapshots', data)
  },

  getSnapshots: (params?: { shopId?: number; limit?: number }): Promise<any> => {
    return apiClient.get('/profit/snapshots', { params })
  },

  saveTemplate: (data: {
    shopId: number
    templateName: string
    algorithmProfile: string
    layeredParams: any
    scenarios: any[]
    operator?: string
  }): Promise<any> => {
    return apiClient.post('/profit/templates', data)
  },

  getTemplates: (params?: { shopId?: number; limit?: number }): Promise<any> => {
    return apiClient.get('/profit/templates', { params })
  },

}

// ========== Strategy API ==========

export const strategyApi = {
  /**
   * 获取策略任务列表
   */
  getStrategyList: async (params?: {
    shop_id?: number
    priority?: string
    status?: string
    limit?: number
  }): Promise<StrategyListResponse> => {
    const response = await apiClient.get<any, any>('/strategy/list', { params })
    return response as StrategyListResponse
  },

  /**
   * 为 SKU 生成策略
   */
  generateStrategy: (sku: string, data: {
    shopId: number
    snapshot: any
  }): Promise<ApiResponse<{ tasks: StrategyTask[] }>> => {
    return apiClient.post(`/strategy/generate/${sku}`, data)
  },

  /**
   * 批量生成策略
   */
  batchGenerate: (data: {
    shopId: number
    date?: string
    filters?: any
  }): Promise<ApiResponse<{
    batchId: string
    totalTasks: number
    summary: Record<string, number>
  }>> => {
    return apiClient.post('/strategy/batch', data)
  },

  /**
   * 综合决策
   */
  makeDecision: (data: DecisionInput): Promise<ApiResponse<DecisionOutput>> => {
    return apiClient.post('/strategy/decision', data)
  },

  decisionPreview: (scope: 'all' | 'high_priority' | 'low_hanging_fruit' = 'all'): Promise<ApiResponse<any>> => {
    return apiClient.get('/strategy/decision/preview', { params: { scope } })
  },

  decisionConfirm: (taskIds: number[], operator = 'planner'): Promise<ApiResponse<any>> => {
    return apiClient.post('/strategy/decision/confirm', { taskIds, operator })
  },

  /**
   * 更新任务状态
   */
  updateTaskStatus: (taskId: number, data: {
    status: string
    assignedTo?: string
    notes?: string
  }): Promise<ApiResponse<{
    taskId: number
    status: string
    updatedAt: string
  }>> => {
    return apiClient.put(`/strategy/task/${taskId}/status`, data)
  },
}

// ========== Ads API ==========

export const adsApi = {
  /**
   * 获取广告活动列表
   */
  getCampaigns: (params?: {
    shop_id?: number
    status?: string
  }): Promise<ApiResponse<AdCampaign[]>> => {
    return apiClient.get('/ads/campaigns', { params })
  },

  /**
   * 更新广告活动
   */
  updateCampaign: (campaignId: string, data: {
    budget?: number
    status?: string
  }): Promise<ApiResponse<AdCampaign>> => {
    return apiClient.put(`/ads/campaign/${campaignId}`, data)
  },
}



export const thematicApi = {
  getABC: (params?: { shopId?: number; days?: number }): Promise<any> => apiClient.get('/analysis/abc', { params }),
  getPriceCockpit: (params?: { shopId?: number; days?: number; view?: string }): Promise<any> => apiClient.get('/analysis/price-cockpit', { params }),
  getFunnel: (params?: { shopId?: number; days?: number }): Promise<any> => apiClient.get('/analysis/funnel', { params }),
  getInventory: (params?: { shopId?: number; days?: number }): Promise<any> => apiClient.get('/analysis/inventory', { params }),
  getAds: (params?: { shopId?: number; days?: number }): Promise<any> => apiClient.get('/analysis/ads', { params }),
  pushActionToStrategy: (data: {
    shopId?: number
    sourcePage: string
    sku: string
    issueSummary: string
    recommendedAction: string
    strategyType: string
    priority: string
    operator?: string
  }): Promise<any> => apiClient.post('/analysis/action-to-strategy', data),
}

export const authApi = {
  login: (username: string, password: string): Promise<any> => apiClient.post('/auth/login', { username, password }),
  me: (): Promise<any> => apiClient.get('/auth/me'),
  logout: (): Promise<any> => apiClient.post('/auth/logout', {}),
}

export const reminderApi = {
  list: (params?: { shopId?: number }): Promise<any> => apiClient.get('/reminders/list', { params }),
  ack: (): Promise<any> => apiClient.post('/reminders/ack', {}),
}

// ========== Health Check ==========

export const healthCheck = (): Promise<any> => {
  return apiClient.get('/health')
}

export default apiClient
