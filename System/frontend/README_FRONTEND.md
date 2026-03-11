# 🚀 V5.1 前端系统启动指南

## 📋 系统概览

**V5.1 跨境电商智能运营系统** 前端部分已完成开发，包含 8 个核心运营页面。

---

## ✅ 已完成的页面

| 页面 | 文件 | 功能 | 代码量 |
|------|------|------|--------|
| 运营总览 | Dashboard.tsx | 核心指标展示、趋势图表、告警通知 | 7,512 字节 |
| 数据导入 | DataImport.tsx | 智能数据导入、平台识别、字段映射 | 9,779 字节 |
| ABC分析 | ABCAnalysis.tsx | ABC分类管理、策略分配、图表分析 | 12,792 字节 |
| 价格竞争力 | PriceCompetitiveness.tsx | 价格对比、竞争力区域分析、优化建议 | 11,730 字节 |
| 转化漏斗 | FunnelAnalysis.tsx | 漏斗分析、瓶颈识别、转化优化 | 12,916 字节 |
| 库存预警 | InventoryAlert.tsx | 库存监控、预警系统、补货管理 | 13,637 字节 |
| 广告管理 | AdsManagement.tsx | 广告活动管理、ROAS分析、预算优化 | 16,643 字节 |
| 策略清单 | StrategyList.tsx | 策略任务管理、优先级分配、进度跟踪 | 20,916 字节 |

**总代码量**: 105,825 字节

---

## 🎯 核心功能特性

### 1. **数据导入中心**
- ✅ 支持 Excel/CSV/JSON 多格式导入
- ✅ 智能平台识别（Ozon/Wildberries/AliExpress）
- ✅ 自动表头定位（前20行搜索）
- ✅ 多语言字段映射（俄语/中文/英语）
- ✅ 详细导入诊断报告

### 2. **ABC分类分析**
- ✅ 自动ABC分类算法
- ✅ 收入/订单/利润多维度分析
- ✅ 可视化分布图表
- ✅ SKU级别策略建议

### 3. **价格竞争力分析**
- ✅ 实时价格对比
- ✅ 绿区/黄区/红区竞争力分级
- ✅ 价格差距 vs 转化率相关性分析
- ✅ 智能定价建议

### 4. **转化漏斗分析**
- ✅ 展示 → 访问 → 加购 → 下单全链路
- ✅ 瓶颈自动识别
- ✅ CTR/加购率/下单率多维分析
- ✅ 优化建议生成

### 5. **库存预警**
- ✅ 库存周转天数监控
- ✅ 安全库存自动计算
- ✅ 紧急/警告/正常三级预警
- ✅ 补货建议生成

### 6. **广告管理**
- ✅ 广告活动状态监控
- ✅ ROAS/ACOS/CPC 多指标分析
- ✅ 表现分级（优秀/良好/较差/严重）
- ✅ 预算优化建议

### 7. **策略清单**
- ✅ P0-P3 优先级分类
- ✅ 定价/库存/转化/广告/风控多类型策略
- ✅ 任务状态跟踪
- ✅ 影响力 × 紧急度评分

### 8. **运营总览**
- ✅ 核心KPI卡片（营收/订单/客单价/毛利率）
- ✅ 7日趋势图表
- ✅ Top SKU 排行
- ✅ 紧急告警通知

---

## 🛠️ 技术栈

### 前端框架
- **React 18.2** - 现代化组件框架
- **TypeScript 5.3** - 类型安全
- **Vite 5.0** - 极速构建工具

### UI 组件库
- **Ant Design 5.13** - 企业级 UI 组件
- **Ant Design Pro Components** - 高级业务组件

### 状态管理
- **Zustand 4.4** - 轻量级状态管理
- **TanStack Query 5.17** - 服务端状态管理

### 图表库
- **ECharts 5.4** - 专业级可视化
- **ECharts for React** - React 封装

### 路由
- **React Router 6.21** - 路由管理

### HTTP 客户端
- **Axios 1.6** - HTTP 请求

### 工具库
- **Lodash 4.17** - 实用工具函数
- **Day.js 1.11** - 日期处理

---

## 🚀 快速启动

### 1. 安装依赖

```bash
cd C:\Operation-system\System\frontend
npm install
```

### 2. 启动开发服务器

```bash
npm run dev
```

### 3. 访问系统

浏览器访问: http://localhost:5173

---

## 📁 项目结构

```
C:\Operation-system\System\frontend\
│
├── src/
│   ├── pages/                    # 页面组件
│   │   ├── Dashboard.tsx        ✅ 运营总览
│   │   ├── DataImport.tsx       ✅ 数据导入
│   │   ├── ABCAnalysis.tsx      ✅ ABC分析
│   │   ├── PriceCompetitiveness.tsx  ✅ 价格竞争力
│   │   ├── FunnelAnalysis.tsx   ✅ 转化漏斗
│   │   ├── InventoryAlert.tsx   ✅ 库存预警
│   │   ├── AdsManagement.tsx    ✅ 广告管理
│   │   └── StrategyList.tsx     ✅ 策略清单
│   │
│   ├── layout/                   # 布局组件
│   │   └── Layout.tsx           ✅ 主布局（侧边栏 + 顶部栏）
│   │
│   ├── App.tsx                  ✅ 路由配置
│   ├── main.tsx                 ✅ 入口文件
│   ├── App.css                  ✅ 全局样式
│   └── index.css                ✅ 基础样式
│
├── public/                       # 静态资源
├── index.html                    # HTML 模板
├── package.json                  ✅ 依赖配置
├── tsconfig.json                 ✅ TypeScript 配置
├── vite.config.ts                ✅ Vite 配置
└── README_FRONTEND.md            # 本文档
```

---

## 🔌 后端 API 集成

### 当前状态
- ✅ 前端页面已完成
- 🔄 API 调用使用模拟数据
- 📝 需要后端提供真实 API

### API 接口清单

#### 1. 数据导入
```
POST /api/import/upload         # 上传文件
POST /api/import/diagnose       # 诊断导入
GET  /api/import/history        # 导入历史
```

#### 2. 运营分析
```
GET  /api/dashboard/metrics     # 获取仪表盘指标
GET  /api/abc/analysis          # ABC 分析数据
GET  /api/price/competitiveness # 价格竞争力数据
GET  /api/funnel/analysis       # 转化漏斗数据
GET  /api/inventory/alerts      # 库存预警数据
GET  /api/ads/campaigns         # 广告活动数据
GET  /api/strategy/tasks        # 策略任务列表
```

#### 3. 作战室服务
```
POST /api/war-room/report       # 生成作战室报告
POST /api/profit/calculate      # 利润计算
POST /api/strategy/generate     # 生成策略
```

### 集成步骤

1. **配置 API 基础路径**

创建 `src/utils/api.ts`:

```typescript
import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 10000,
})

export default api
```

2. **替换模拟数据**

在每个页面文件中，将 `queryFn` 中的模拟数据替换为真实 API 调用：

```typescript
// 示例：Dashboard.tsx
const { data: metrics, isLoading } = useQuery<DashboardMetrics>({
  queryKey: ['dashboard', dateRange],
  queryFn: async () => {
    const response = await api.get('/dashboard/metrics', {
      params: {
        startDate: dateRange[0].format('YYYY-MM-DD'),
        endDate: dateRange[1].format('YYYY-MM-DD'),
      }
    })
    return response.data
  }
})
```

---

## 🎨 设计亮点

### 1. **响应式设计**
- ✅ 支持桌面端和移动端
- ✅ 栅格布局自适应

### 2. **数据可视化**
- ✅ ECharts 专业图表
- ✅ 漏斗图、饼图、柱状图、散点图
- ✅ 数据实时更新

### 3. **用户体验**
- ✅ Ant Design 企业级 UI
- ✅ 侧边栏可折叠
- ✅ 表格支持排序、筛选、分页
- ✅ 详情模态框

### 4. **状态管理**
- ✅ TanStack Query 管理服务端状态
- ✅ 自动缓存和重新获取
- ✅ 加载和错误状态处理

### 5. **类型安全**
- ✅ TypeScript 严格模式
- ✅ 完整的类型定义
- ✅ 编译时错误检查

---

## 🔧 开发命令

```bash
# 开发
npm run dev

# 构建
npm run build

# 预览
npm run preview

# 代码检查
npm run lint
```

---

## 📊 性能优化建议

### 1. 代码分割
```typescript
// 使用 React.lazy 进行路由级代码分割
const Dashboard = React.lazy(() => import('./pages/Dashboard'))
```

### 2. 图表优化
```typescript
// 使用 ECharts 的 lazy 渲染
<ReactECharts
  option={chartOption}
  notMerge={true}
  lazyUpdate={true}
/>
```

### 3. 数据缓存
```typescript
// TanStack Query 自动缓存
const { data } = useQuery({
  queryKey: ['data'],
  queryFn: fetchData,
  staleTime: 5 * 60 * 1000, // 5分钟内不重新获取
})
```

---

## 🐛 常见问题

### 1. 依赖安装失败
```bash
# 清除缓存重新安装
rm -rf node_modules package-lock.json
npm install
```

### 2. 端口被占用
```bash
# 修改 vite.config.ts
server: {
  port: 5174  // 改为其他端口
}
```

### 3. 图表不显示
```bash
# 确保 ECharts 正确导入
import ReactECharts from 'echarts-for-react'
```

---

## 📝 更新日志

### 2026-03-08
- ✅ 完成所有 8 个页面开发
- ✅ 创建 Layout 布局组件
- ✅ 配置路由系统
- ✅ 集成 Ant Design 和 ECharts
- ✅ 编写启动文档

---

## 🚀 下一步计划

### 后端集成
1. 连接后端 API（FastAPI）
2. 实现真实数据获取
3. 添加错误处理和重试机制

### 功能增强
1. 用户认证和权限管理
2. 数据导出功能
3. 更多图表类型
4. 实时数据推送（WebSocket）

### 性能优化
1. 代码分割和懒加载
2. 图表渲染优化
3. 数据缓存策略

---

## 📞 技术支持

- **前端负责人**: Ozon Agent
- **后端 API**: 参考 README_V51.md
- **项目位置**: C:\Operation-system\System\frontend

---

**系统状态**: ✅ 前端开发完成，等待后端集成
**最后更新**: 2026-03-08 20:30
