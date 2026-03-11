/**
 * API 服务层
 * 封装所有后端 API 调用
 * 
 * 设计原则：
 * 1. 优先调用真实后端 API
 * 2. API 失败时返回 mock 数据（确保 UI 正常显示）
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
  FieldMapping,
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

const API_BASE_URL = 'http://localhost:5000/api'

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
   * 优先调用真实 API，失败时返回 mock 数据
   */
  getOverview: async (): Promise<DashboardMetrics> => {
    try {
      const response = await apiClient.get<any, any>('/dashboard/overview')
      return response.data as DashboardMetrics
    } catch (error) {
      console.warn('Dashboard API failed, using mock data:', error)
      // Mock 数据（确保 UI 正常显示）
      return {
        totalRevenue: 125680,
        totalOrders: 1247,
        avgOrderValue: 100.87,
        profitMargin: 0.23,
        totalProducts: 328,
        totalImpressions: 45600,
        totalClicks: 3280,
        avgCtr: 0.072,
        avgRating: 4.6,
        period: {
          start: '2026-03-03',
          end: '2026-03-10'
        },
        topSkus: [
          { sku: 'HAA132-01', revenue: 15680, orders: 156, margin: 0.28, abcClass: 'A' },
          { sku: 'HAA128-03', revenue: 12450, orders: 124, margin: 0.25, abcClass: 'A' },
          { sku: 'HAA145-02', revenue: 9870, orders: 98, margin: 0.22, abcClass: 'B' },
          { sku: 'HAA136-05', revenue: 7650, orders: 76, margin: 0.20, abcClass: 'B' },
          { sku: 'HAA142-04', revenue: 5430, orders: 54, margin: 0.18, abcClass: 'C' }
        ],
        alerts: [
          { type: 'P0', message: '库存不足 10 件', sku: 'HAA132-01' },
          { type: 'P1', message: '评分下降至 3.8', sku: 'HAA128-03' },
          { type: 'P2', message: '转化率低于 2%', sku: 'HAA145-02' }
        ],
        trends: {
          dates: ['03-04', '03-05', '03-06', '03-07', '03-08', '03-09', '03-10'],
          revenue: [15200, 16800, 14500, 18200, 17600, 19300, 18100],
          orders: [152, 168, 145, 182, 176, 193, 181]
        }
      }
    }
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
  ): Promise<ApiResponse<ImportResult>> => {
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
  confirmImport: (data: {
    filePath: string
    shopId: number
    headerRow: number
    fieldMappings: FieldMapping[]
    date?: string
  }): Promise<ApiResponse<{
    batchId: string
    importedRows: number
    errorRows: number
    status: string
  }>> => {
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

// ========== Strategy API ==========

export const strategyApi = {
  /**
   * 获取策略任务列表
   * 优先调用真实 API，失败时返回 mock 数据
   */
  getStrategyList: async (params?: {
    shop_id?: number
    priority?: string
    status?: string
    limit?: number
  }): Promise<StrategyListResponse> => {
    try {
      const response = await apiClient.get<any, any>('/strategy/list', { params })
      return response.data as StrategyListResponse
    } catch (error) {
      console.warn('Strategy API failed, using mock data:', error)
      // Mock 数据
      return {
        tasks: [
          {
            id: '1',
            sku: 'HAA132-01',
            strategyType: 'pricing',
            priority: 'P0',
            issueSummary: '价格低于成本线，亏损严重',
            recommendedAction: '立即提价 15% 至成本线以上',
            observationMetrics: ['profit_margin', 'price_gap'],
            status: 'pending',
            assignee: '运营主管',
            dueDate: '2026-03-10',
            createdAt: '2026-03-08 09:00',
            impact: 9,
            urgency: 9
          },
          {
            id: '2',
            sku: 'HAA128-03',
            strategyType: 'inventory',
            priority: 'P0',
            issueSummary: '库存不足 5 件，即将断货',
            recommendedAction: '紧急补货 500 件',
            observationMetrics: ['stock_days', 'sales_velocity'],
            status: 'in_progress',
            assignee: '库存专员',
            dueDate: '2026-03-11',
            createdAt: '2026-03-08 10:00',
            impact: 8,
            urgency: 10
          },
          {
            id: '3',
            sku: 'HAA145-02',
            strategyType: 'ads',
            priority: 'P1',
            issueSummary: '广告 ROI 仅 1.2，低于目标',
            recommendedAction: '优化关键词和投放时段',
            observationMetrics: ['ad_roi', 'ctr', 'conversion_rate'],
            status: 'pending',
            createdAt: '2026-03-08 11:00',
            impact: 7,
            urgency: 6
          },
          {
            id: '4',
            sku: 'HAA136-05',
            strategyType: 'conversion',
            priority: 'P2',
            issueSummary: '加购转化率仅 3.2%，低于类目平均',
            recommendedAction: '优化详情页和价格策略',
            observationMetrics: ['add_to_cart_rate', 'conversion_rate'],
            status: 'pending',
            createdAt: '2026-03-08 12:00',
            impact: 6,
            urgency: 5
          },
          {
            id: '5',
            sku: 'HAA142-04',
            strategyType: 'risk_control',
            priority: 'P1',
            issueSummary: '退货率超过 15%，评分低于 4.0',
            recommendedAction: '排查差评原因并修复',
            observationMetrics: ['return_rate', 'rating'],
            status: 'pending',
            dueDate: '2026-03-12',
            createdAt: '2026-03-08 11:00',
            impact: 7,
            urgency: 7
          },
          {
            id: '6',
            sku: 'HAA150-01',
            strategyType: 'conversion',
            priority: 'P2',
            issueSummary: '加购率偏低，转化漏斗受阻',
            recommendedAction: '优化价格竞争力，提升加购转化',
            observationMetrics: ['add_to_cart_rate', 'conversion_rate'],
            status: 'pending',
            createdAt: '2026-03-08 12:00',
            impact: 6,
            urgency: 5
          },
          {
            id: '7',
            sku: 'HAA160-02',
            strategyType: 'inventory',
            priority: 'P2',
            issueSummary: '库存周转天数不足 14 天',
            recommendedAction: '准备补货计划',
            observationMetrics: ['days_of_supply'],
            status: 'in_progress',
            assignee: '运营专员',
            dueDate: '2026-03-13',
            createdAt: '2026-03-08 13:00',
            impact: 5,
            urgency: 6
          },
          {
            id: '8',
            sku: 'HAA170-03',
            strategyType: 'pricing',
            priority: 'P3',
            issueSummary: '价格略低于市场均价',
            recommendedAction: '可适当提价 5%',
            observationMetrics: ['price_gap', 'profit_margin'],
            status: 'completed',
            completedAt: '2026-03-07 16:00',
            createdAt: '2026-03-06 10:00',
            impact: 4,
            urgency: 3
          }
        ],
        summary: {
          total: 8,
          pending: 5,
          in_progress: 2,
          completed: 1,
          P0: 2,
          P1: 2,
          P2: 3,
          P3: 1
        }
      }
    }
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

// ========== Health Check ==========

export const healthCheck = (): Promise<any> => {
  return apiClient.get('/health')
}

export default apiClient
