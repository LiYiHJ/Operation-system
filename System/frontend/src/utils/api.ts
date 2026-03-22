import axios from 'axios'

// API 基础配置
const api = axios.create({
  baseURL: '/api',  // Vite dev server will proxy API requests to the backend.
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 可以在这里添加 token 等
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    // 统一错误处理
    const message = error.response?.data?.error || error.message || '请求失败'
    return Promise.reject(new Error(message))
  }
)

// ==================== Dashboard API ====================
export const dashboardAPI = {
  getOverview: () => api.get('/dashboard/overview'),
}

// ==================== Import API ====================
export const importAPI = {
  uploadFile: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/import/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  
  confirmImport: (data: any) => api.post('/import/confirm', data),
}

// ==================== ABC Analysis API ====================
export const abcAPI = {
  getAnalysis: () => api.get('/abc/analysis'),
}

// ==================== Price Competitiveness API ====================
export const priceAPI = {
  getCompetitiveness: () => api.get('/price/competitiveness'),
}

// ==================== Funnel Analysis API ====================
export const funnelAPI = {
  getAnalysis: () => api.get('/funnel/analysis'),
}

// ==================== Inventory Alert API ====================
export const inventoryAPI = {
  getAlert: () => api.get('/inventory/alert'),
}

// ==================== Ads Management API ====================
export const adsAPI = {
  getManagement: () => api.get('/ads/management'),
}

// ==================== Strategy List API ====================
export const strategyAPI = {
  getList: () => api.get('/strategy/list'),
  analyze: (data: any[], shopName?: string) => api.post('/strategy/analyze', { data, shop_name: shopName }),
  getQuickSummary: (data: any[]) => api.post('/strategy/quick-summary', { data }),
}

// ==================== War Room API ====================
export const warRoomAPI = {
  getSkuReport: (skuId: string) => api.get(`/sku/${skuId}/war-room`),
}

export default api
