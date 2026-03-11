import { Card, Row, Col, Table, Tag, Statistic, Progress, Tabs, Badge, Empty, Button, Space, Modal, Descriptions } from 'antd'
import { ArrowUpOutlined, ArrowDownOutlined, FilterOutlined, DownloadOutlined } from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import { useState } from 'react'

// ==================== 类型定义 ====================
interface SKUMetric {
  sku: string
  name: string
  abc: 'A' | 'B' | 'C'
  priceZone: 'GREEN' | 'YELLOW' | 'RED'
  orders: number
  revenue: number
  views: number
  conversionRate: number
  stock: number
  trend: number
}

interface ABCDistribution {
  A: { count: number; revenueShare: number; ordersShare: number }
  B: { count: number; revenueShare: number; ordersShare: number }
  C: { count: number; revenueShare: number; ordersShare: number }
}

// ==================== 模拟数据 ====================
const mockDistribution: ABCDistribution = {
  A: { count: 200, revenueShare: 0.70, ordersShare: 0.65 },
  B: { count: 300, revenueShare: 0.20, ordersShare: 0.25 },
  C: { count: 500, revenueShare: 0.10, ordersShare: 0.10 }
}

const mockTopSKUs: SKUMetric[] = [
  { sku: 'HAA240-10', name: '花瓶 陶瓷 20.7cm', abc: 'A', priceZone: 'RED', orders: 67, revenue: 7000, views: 6231, conversionRate: 1.08, stock: 5, trend: -15 },
  { sku: 'HAA132-01', name: '拖把 13cm', abc: 'A', priceZone: 'GREEN', orders: 58, revenue: 5200, views: 4500, conversionRate: 1.29, stock: 120, trend: 12 },
  { sku: 'HAA150-08', name: '洗漱套装', abc: 'A', priceZone: 'GREEN', orders: 45, revenue: 4500, views: 3800, conversionRate: 1.18, stock: 85, trend: 8 },
  { sku: 'HAA196-11', name: '玻璃花瓶', abc: 'A', priceZone: 'YELLOW', orders: 38, revenue: 3800, views: 3200, conversionRate: 1.19, stock: 150, trend: 0 },
  { sku: 'HAA048-02', name: '厨具套装', abc: 'B', priceZone: 'GREEN', orders: 32, revenue: 3200, views: 2800, conversionRate: 1.14, stock: 200, trend: 5 }
]

const mockSlowSKUs = [
  { sku: 'HAA066-99', name: '旧款产品A', abc: 'C', stock: 150, days: 90, suggestion: '清仓 50%', trend: -80 },
  { sku: 'HAA043-88', name: '旧款产品B', abc: 'C', stock: 200, days: 85, suggestion: '下架评估', trend: -70 },
  { sku: 'HAA061-77', name: '旧款产品C', abc: 'C', stock: 180, days: 80, suggestion: '清仓 30%', trend: -60 }
]

// ==================== ABC 分布概览组件 ====================
function ABCDistributionCard({ distribution, type }: { distribution: ABCDistribution; type: 'A' | 'B' | 'C' }) {
  const data = distribution[type]
  
  const config = {
    A: { color: '#52c41a', title: 'A类 - 核心爆款', icon: '🔥', desc: '贡献 70% 销售额' },
    B: { color: '#1890ff', title: 'B类 - 潜力商品', icon: '🚀', desc: '贡献 20% 销售额' },
    C: { color: '#faad14', title: 'C类 - 长尾商品', icon: '📦', desc: '贡献 10% 销售额' }
  }

  const c = config[type]

  return (
    <Card 
      hoverable
      style={{ 
        borderTop: `4px solid ${c.color}`,
        height: '100%'
      }}
    >
      <div style={{ textAlign: 'center', marginBottom: '16px' }}>
        <span style={{ fontSize: '32px' }}>{c.icon}</span>
        <h3 style={{ margin: '12px 0 4px 0', fontSize: '18px', fontWeight: 600 }}>
          {c.title}
        </h3>
        <p style={{ margin: 0, color: '#8c8c8c', fontSize: '12px' }}>{c.desc}</p>
      </div>

      <Statistic
        title="SKU 数量"
        value={data.count}
        suffix="个"
        valueStyle={{ color: c.color, fontSize: '32px', fontWeight: 700 }}
      />

      <div style={{ marginTop: '16px' }}>
        <div style={{ marginBottom: '8px' }}>
          <span style={{ fontSize: '12px', color: '#8c8c8c' }}>销售额占比</span>
          <Progress 
            percent={data.revenueShare * 100} 
            strokeColor={c.color}
            size="small"
            format={(percent) => `${percent}%`}
          />
        </div>
        <div>
          <span style={{ fontSize: '12px', color: '#8c8c8c' }}>订单占比</span>
          <Progress 
            percent={data.ordersShare * 100} 
            strokeColor={c.color}
            size="small"
            format={(percent) => `${percent}%`}
          />
        </div>
      </div>
    </Card>
  )
}

// ==================== ABC 分布饼图 ====================
function ABCPieChart({ distribution }: { distribution: ABCDistribution }) {
  const option = {
    title: {
      text: 'SKU ABC 分类分布',
      left: 'center',
      top: 10,
      textStyle: { fontSize: 16, fontWeight: 600 }
    },
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c}个 SKU ({d}%)'
    },
    legend: {
      orient: 'vertical',
      left: 'left',
      top: 50
    },
    series: [{
      name: 'SKU分布',
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['60%', '55%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 10,
        borderColor: '#fff',
        borderWidth: 2
      },
      label: {
        show: true,
        formatter: '{b}\n{c}个'
      },
      emphasis: {
        label: {
          show: true,
          fontSize: 16,
          fontWeight: 'bold'
        }
      },
      data: [
        { value: distribution.A.count, name: 'A类', itemStyle: { color: '#52c41a' } },
        { value: distribution.B.count, name: 'B类', itemStyle: { color: '#1890ff' } },
        { value: distribution.C.count, name: 'C类', itemStyle: { color: '#faad14' } }
      ]
    }]
  }

  return (
    <Card>
      <ReactECharts option={option} style={{ height: '350px' }} />
    </Card>
  )
}

// ==================== 销售额占比柱状图 ====================
function RevenueShareChart({ distribution }: { distribution: ABCDistribution }) {
  const option = {
    title: {
      text: '销售额 & 订单占比',
      left: 'center',
      top: 10,
      textStyle: { fontSize: 16, fontWeight: 600 }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' }
    },
    legend: {
      data: ['销售额占比', '订单占比'],
      top: 40
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: 80,
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: ['A类', 'B类', 'C类']
    },
    yAxis: {
      type: 'value',
      max: 100,
      axisLabel: { formatter: '{value}%' }
    },
    series: [
      {
        name: '销售额占比',
        type: 'bar',
        data: [
          { value: distribution.A.revenueShare * 100, itemStyle: { color: '#52c41a' } },
          { value: distribution.B.revenueShare * 100, itemStyle: { color: '#1890ff' } },
          { value: distribution.C.revenueShare * 100, itemStyle: { color: '#faad14' } }
        ],
        label: {
          show: true,
          position: 'top',
          formatter: '{c}%'
        }
      },
      {
        name: '订单占比',
        type: 'bar',
        data: [
          { value: distribution.A.ordersShare * 100, itemStyle: { color: '#73d13d' } },
          { value: distribution.B.ordersShare * 100, itemStyle: { color: '#40a9ff' } },
          { value: distribution.C.ordersShare * 100, itemStyle: { color: '#ffc53d' } }
        ],
        label: {
          show: true,
          position: 'top',
          formatter: '{c}%'
        }
      }
    ]
  }

  return (
    <Card>
      <ReactECharts option={option} style={{ height: '350px' }} />
    </Card>
  )
}

// ==================== Top SKU 表格 ====================
function TopSKUTable({ data }: { data: SKUMetric[] }) {
  const [selectedRow, setSelectedRow] = useState<SKUMetric | null>(null)

  const columns = [
    {
      title: 'SKU',
      dataIndex: 'sku',
      key: 'sku',
      width: 120,
      fixed: 'left' as const,
      render: (text: string) => (
        <Tag color="blue" style={{ fontFamily: 'monospace' }}>{text}</Tag>
      )
    },
    {
      title: '产品名称',
      dataIndex: 'name',
      key: 'name',
      width: 200,
      ellipsis: true
    },
    {
      title: 'ABC',
      dataIndex: 'abc',
      key: 'abc',
      width: 80,
      render: (abc: string) => {
        const colors = { A: 'green', B: 'blue', C: 'orange' }
        return <Tag color={colors[abc]}>{abc}类</Tag>
      }
    },
    {
      title: '价格区域',
      dataIndex: 'priceZone',
      key: 'priceZone',
      width: 100,
      render: (zone: string) => {
        const colors = { GREEN: 'green', YELLOW: 'orange', RED: 'red' }
        return <Tag color={colors[zone]}>{zone}</Tag>
      }
    },
    {
      title: '7天订单',
      dataIndex: 'orders',
      key: 'orders',
      width: 100,
      sorter: (a: SKUMetric, b: SKUMetric) => a.orders - b.orders,
      render: (orders: number) => <span style={{ fontWeight: 600 }}>{orders}</span>
    },
    {
      title: '7天金额(₽)',
      dataIndex: 'revenue',
      key: 'revenue',
      width: 120,
      sorter: (a: SKUMetric, b: SKUMetric) => a.revenue - b.revenue,
      render: (revenue: number) => `₽${revenue.toLocaleString()}`
    },
    {
      title: '转化率',
      dataIndex: 'conversionRate',
      key: 'conversionRate',
      width: 100,
      render: (rate: number) => `${rate.toFixed(2)}%`
    },
    {
      title: '库存',
      dataIndex: 'stock',
      key: 'stock',
      width: 80,
      render: (stock: number) => (
        <Tag color={stock < 20 ? 'red' : stock < 50 ? 'orange' : 'green'}>
          {stock}
        </Tag>
      )
    },
    {
      title: '趋势',
      dataIndex: 'trend',
      key: 'trend',
      width: 100,
      render: (trend: number) => (
        <span style={{ color: trend >= 0 ? '#52c41a' : '#ff4d4f' }}>
          {trend >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
          {Math.abs(trend)}%
        </span>
      )
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      fixed: 'right' as const,
      render: (_: any, record: SKUMetric) => (
        <Button 
          type="link" 
          size="small"
          onClick={() => setSelectedRow(record)}
        >
          详情
        </Button>
      )
    }
  ]

  return (
    <>
      <Card 
        title={
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>🏆 Top 5 畅销 SKU</span>
            <Space>
              <Button icon={<FilterOutlined />} size="small">筛选</Button>
              <Button icon={<DownloadOutlined />} size="small">导出</Button>
            </Space>
          </div>
        }
      >
        <Table
          dataSource={data}
          columns={columns}
          pagination={false}
          scroll={{ x: 1200 }}
          rowKey="sku"
          size="small"
        />
      </Card>

      {/* 详情模态框 */}
      <Modal
        title={`SKU 详情: ${selectedRow?.sku}`}
        open={!!selectedRow}
        onCancel={() => setSelectedRow(null)}
        footer={null}
        width={800}
      >
        {selectedRow && (
          <Descriptions bordered column={2}>
            <Descriptions.Item label="SKU">{selectedRow.sku}</Descriptions.Item>
            <Descriptions.Item label="产品名称">{selectedRow.name}</Descriptions.Item>
            <Descriptions.Item label="ABC 分类">
              <Tag color="green">{selectedRow.abc}类</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="价格区域">
              <Tag color={selectedRow.priceZone === 'GREEN' ? 'green' : selectedRow.priceZone === 'YELLOW' ? 'orange' : 'red'}>
                {selectedRow.priceZone}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="7天订单">{selectedRow.orders} 单</Descriptions.Item>
            <Descriptions.Item label="7天金额">₽{selectedRow.revenue.toLocaleString()}</Descriptions.Item>
            <Descriptions.Item label="浏览量">{selectedRow.views.toLocaleString()}</Descriptions.Item>
            <Descriptions.Item label="转化率">{selectedRow.conversionRate.toFixed(2)}%</Descriptions.Item>
            <Descriptions.Item label="库存">{selectedRow.stock} 件</Descriptions.Item>
            <Descriptions.Item label="趋势">
              <span style={{ color: selectedRow.trend >= 0 ? '#52c41a' : '#ff4d4f' }}>
                {selectedRow.trend >= 0 ? '+' : ''}{selectedRow.trend}%
              </span>
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </>
  )
}

// ==================== 滞销 SKU 表格 ====================
function SlowSKUTable({ data }: { data: any[] }) {
  const columns = [
    {
      title: 'SKU',
      dataIndex: 'sku',
      key: 'sku',
      render: (text: string) => <Tag color="orange">{text}</Tag>
    },
    {
      title: '产品名称',
      dataIndex: 'name',
      key: 'name'
    },
    {
      title: 'ABC',
      dataIndex: 'abc',
      key: 'abc',
      render: () => <Tag color="orange">C类</Tag>
    },
    {
      title: '库存',
      dataIndex: 'stock',
      key: 'stock'
    },
    {
      title: '滞销天数',
      dataIndex: 'days',
      key: 'days',
      render: (days: number) => (
        <Tag color={days > 90 ? 'red' : 'orange'}>{days} 天</Tag>
      )
    },
    {
      title: '趋势',
      dataIndex: 'trend',
      key: 'trend',
      render: (trend: number) => (
        <span style={{ color: '#ff4d4f' }}>
          <ArrowDownOutlined /> {Math.abs(trend)}%
        </span>
      )
    },
    {
      title: '建议',
      dataIndex: 'suggestion',
      key: 'suggestion',
      render: (sug: string) => <Tag color="red">{sug}</Tag>
    }
  ]

  return (
    <Card title="⚠️ Top 3 滞销 SKU（有库存但零销量）">
      <Table
        dataSource={data}
        columns={columns}
        pagination={false}
        rowKey="sku"
        size="small"
      />
    </Card>
  )
}

// ==================== 主组件 ====================
export default function ABCAnalysis() {
  const [activeTab, setActiveTab] = useState('overview')

  const tabItems = [
    {
      key: 'overview',
      label: '📊 概览',
      children: (
        <>
          {/* ABC 分类统计卡片 */}
          <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
            <Col xs={24} sm={8}>
              <ABCDistributionCard distribution={mockDistribution} type="A" />
            </Col>
            <Col xs={24} sm={8}>
              <ABCDistributionCard distribution={mockDistribution} type="B" />
            </Col>
            <Col xs={24} sm={8}>
              <ABCDistributionCard distribution={mockDistribution} type="C" />
            </Col>
          </Row>

          {/* 图表 */}
          <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
            <Col xs={24} lg={12}>
              <ABCPieChart distribution={mockDistribution} />
            </Col>
            <Col xs={24} lg={12}>
              <RevenueShareChart distribution={mockDistribution} />
            </Col>
          </Row>
        </>
      )
    },
    {
      key: 'top',
      label: (
        <Badge count={5} offset={[10, 0]}>
          🏆 畅销 SKU
        </Badge>
      ),
      children: <TopSKUTable data={mockTopSKUs} />
    },
    {
      key: 'slow',
      label: (
        <Badge count={3} offset={[10, 0]}>
          ⚠️ 滞销 SKU
        </Badge>
      ),
      children: <SlowSKUTable data={mockSlowSKUs} />
    }
  ]

  return (
    <div style={{ padding: '24px', background: '#f0f2f5', minHeight: '100vh' }}>
      {/* 页面标题 */}
      <div style={{ 
        background: '#fff', 
        padding: '16px 24px', 
        marginBottom: '24px',
        borderRadius: '8px',
        boxShadow: '0 1px 2px rgba(0,0,0,0.03)'
      }}>
        <h1 style={{ margin: 0, fontSize: '24px', fontWeight: 600 }}>
          🏷️ ABC 分类分析
        </h1>
        <p style={{ margin: '8px 0 0 0', color: '#8c8c8c', fontSize: '14px' }}>
          基于 Pareto 原则的 SKU 分类管理体系
        </p>
      </div>

      {/* 标签页 */}
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={tabItems}
        size="large"
        style={{ background: '#fff', padding: '16px', borderRadius: '8px' }}
      />
    </div>
  )
}
