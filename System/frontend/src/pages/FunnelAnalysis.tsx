import { Card, Row, Col, Table, Tag, Button, Select, Space, Statistic, Badge, Tooltip, message } from 'antd'
import { UserOutlined, ShoppingCartOutlined, DollarOutlined, WarningOutlined, ArrowDownOutlined } from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'

interface FunnelData {
  sku: string
  impressions: number
  cardVisits: number
  addToCart: number
  orders: number
  ctr: number
  addRate: number
  orderRate: number
  conversionFunnel: string
  bottleneck: string
  recommendation: string
  priority: 'P0' | 'P1' | 'P2' | 'P3'
}

export default function FunnelAnalysis() {
  const [filterBottleneck, setFilterBottleneck] = useState<string>('all')
  const [sortBy, setSortBy] = useState<string>('conversionFunnel')

  // 获取数据
  const { data: funnelData, isLoading } = useQuery<FunnelData[]>({
    queryKey: ['funnel-analysis', filterBottleneck, sortBy],
    queryFn: async () => {
      // TODO: 调用后端 API
      return [
        {
          sku: 'SKU-001',
          impressions: 10000,
          cardVisits: 280,
          addToCart: 56,
          orders: 14,
          ctr: 0.028,
          addRate: 0.20,
          orderRate: 0.25,
          conversionFunnel: '100% → 2.8% → 0.56% → 0.14%',
          bottleneck: '加购率',
          recommendation: '优化价格竞争力，提升加购转化',
          priority: 'P1'
        },
        {
          sku: 'SKU-002',
          impressions: 8000,
          cardVisits: 144,
          addToCart: 43,
          orders: 8,
          ctr: 0.018,
          addRate: 0.30,
          orderRate: 0.19,
          conversionFunnel: '100% → 1.8% → 0.54% → 0.10%',
          bottleneck: 'CTR',
          recommendation: '优化主图和标题，提升点击率',
          priority: 'P1'
        },
        {
          sku: 'SKU-003',
          impressions: 12000,
          cardVisits: 240,
          addToCart: 72,
          orders: 18,
          ctr: 0.02,
          addRate: 0.30,
          orderRate: 0.25,
          conversionFunnel: '100% → 2.0% → 0.60% → 0.15%',
          bottleneck: 'CTR',
          recommendation: '优化首图和关键词',
          priority: 'P2'
        },
        {
          sku: 'SKU-004',
          impressions: 5000,
          cardVisits: 100,
          addToCart: 10,
          orders: 2,
          ctr: 0.02,
          addRate: 0.10,
          orderRate: 0.20,
          conversionFunnel: '100% → 2.0% → 0.20% → 0.04%',
          bottleneck: '加购率',
          recommendation: '检查价格竞争力，优化产品描述',
          priority: 'P0'
        },
        {
          sku: 'SKU-005',
          impressions: 15000,
          cardVisits: 450,
          addToCart: 135,
          orders: 27,
          ctr: 0.03,
          addRate: 0.30,
          orderRate: 0.20,
          conversionFunnel: '100% → 3.0% → 0.90% → 0.18%',
          bottleneck: '无',
          recommendation: '转化漏斗健康，保持优化',
          priority: 'P3'
        }
      ]
    }
  })

  // 统计数据
  const stats = {
    avgCtr: funnelData ? funnelData.reduce((sum, f) => sum + f.ctr, 0) / funnelData.length : 0,
    avgAddRate: funnelData ? funnelData.reduce((sum, f) => sum + f.addRate, 0) / funnelData.length : 0,
    avgOrderRate: funnelData ? funnelData.reduce((sum, f) => sum + f.orderRate, 0) / funnelData.length : 0,
    totalOrders: funnelData?.reduce((sum, f) => sum + f.orders, 0) || 0
  }

  // 整体漏斗图
  const overallFunnelOption = {
    title: { text: '整体转化漏斗', left: 'center' },
    tooltip: { trigger: 'item', formatter: '{b}: {c}' },
    series: [
      {
        type: 'funnel',
        left: '10%',
        top: 60,
        bottom: 60,
        width: '80%',
        min: 0,
        max: 100,
        minSize: '0%',
        maxSize: '100%',
        sort: 'descending',
        gap: 2,
        label: {
          show: true,
          position: 'inside',
          formatter: '{b}: {c}'
        },
        labelLine: {
          length: 10,
          lineStyle: { width: 1, type: 'solid' }
        },
        itemStyle: { borderColor: '#fff', borderWidth: 1 },
        emphasis: {
          label: { fontSize: 16 }
        },
        data: [
          { value: 100, name: '展示量', itemStyle: { color: '#1890ff' } },
          { value: (stats.avgCtr * 100).toFixed(1), name: '商品页访问', itemStyle: { color: '#52c41a' } },
          { value: (stats.avgCtr * stats.avgAddRate * 100).toFixed(2), name: '加购', itemStyle: { color: '#faad14' } },
          { value: (stats.avgCtr * stats.avgAddRate * stats.avgOrderRate * 100).toFixed(3), name: '订单', itemStyle: { color: '#f5222d' } }
        ]
      }
    ]
  }

  // 瓶颈分布饼图
  const bottleneckChartOption = {
    title: { text: '转化瓶颈分布', left: 'center' },
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0 },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: { show: true, formatter: '{b}: {c}' },
        data: [
          { value: funnelData?.filter(f => f.bottleneck === 'CTR').length || 0, name: 'CTR', itemStyle: { color: '#1890ff' } },
          { value: funnelData?.filter(f => f.bottleneck === '加购率').length || 0, name: '加购率', itemStyle: { color: '#faad14' } },
          { value: funnelData?.filter(f => f.bottleneck === '下单率').length || 0, name: '下单率', itemStyle: { color: '#f5222d' } },
          { value: funnelData?.filter(f => f.bottleneck === '无').length || 0, name: '无明显瓶颈', itemStyle: { color: '#52c41a' } }
        ]
      }
    ]
  }

  // CTR vs 转化率散点图
  const scatterChartOption = {
    title: { text: 'CTR vs 转化率', left: 'center' },
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        return `${params.data[2]}<br/>CTR: ${(params.data[0] * 100).toFixed(2)}%<br/>转化率: ${(params.data[1] * 100).toFixed(2)}%`
      }
    },
    xAxis: {
      type: 'value',
      name: 'CTR',
      min: 0,
      max: 0.05,
      axisLabel: { formatter: (value: number) => `${(value * 100).toFixed(1)}%` }
    },
    yAxis: {
      type: 'value',
      name: '转化率',
      min: 0,
      max: 0.4,
      axisLabel: { formatter: (value: number) => `${(value * 100).toFixed(0)}%` }
    },
    series: [
      {
        type: 'scatter',
        symbolSize: 20,
        data: funnelData?.map(f => [f.ctr, f.addRate * f.orderRate, f.sku]) || [],
        itemStyle: { color: '#1890ff' }
      },
      {
        type: 'line',
        data: [[0.015, 0.05], [0.025, 0.1], [0.035, 0.15]],
        lineStyle: { type: 'dashed', color: '#8c8c8c' },
        symbol: 'none',
        name: '基准线'
      }
    ]
  }

  // 表格列定义
  const columns = [
    {
      title: 'SKU',
      dataIndex: 'sku',
      key: 'sku',
      fixed: 'left' as const,
      width: 120
    },
    {
      title: '展示量',
      dataIndex: 'impressions',
      key: 'impressions',
      width: 100,
      render: (val: number) => val.toLocaleString()
    },
    {
      title: '访问数',
      dataIndex: 'cardVisits',
      key: 'cardVisits',
      width: 100,
      render: (val: number) => val.toLocaleString()
    },
    {
      title: '加购数',
      dataIndex: 'addToCart',
      key: 'addToCart',
      width: 100,
      render: (val: number) => val.toLocaleString()
    },
    {
      title: '订单数',
      dataIndex: 'orders',
      key: 'orders',
      width: 100,
      render: (val: number) => val.toLocaleString()
    },
    {
      title: 'CTR',
      dataIndex: 'ctr',
      key: 'ctr',
      width: 100,
      sorter: (a: FunnelData, b: FunnelData) => a.ctr - b.ctr,
      render: (val: number) => (
        <span style={{ color: val > 0.02 ? '#52c41a' : '#f5222d' }}>
          {(val * 100).toFixed(2)}%
        </span>
      )
    },
    {
      title: '加购率',
      dataIndex: 'addRate',
      key: 'addRate',
      width: 100,
      sorter: (a: FunnelData, b: FunnelData) => a.addRate - b.addRate,
      render: (val: number) => (
        <span style={{ color: val > 0.2 ? '#52c41a' : '#f5222d' }}>
          {(val * 100).toFixed(1)}%
        </span>
      )
    },
    {
      title: '下单率',
      dataIndex: 'orderRate',
      key: 'orderRate',
      width: 100,
      sorter: (a: FunnelData, b: FunnelData) => a.orderRate - b.orderRate,
      render: (val: number) => (
        <span style={{ color: val > 0.2 ? '#52c41a' : '#f5222d' }}>
          {(val * 100).toFixed(1)}%
        </span>
      )
    },
    {
      title: '转化漏斗',
      dataIndex: 'conversionFunnel',
      key: 'conversionFunnel',
      width: 220,
      ellipsis: true
    },
    {
      title: '瓶颈',
      dataIndex: 'bottleneck',
      key: 'bottleneck',
      width: 100,
      render: (val: string) => (
        <Tag color={val === '无' ? 'green' : 'orange'}>{val}</Tag>
      )
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      width: 80,
      render: (val: string) => {
        const colorMap: Record<string, string> = {
          P0: '#f5222d',
          P1: '#fa8c16',
          P2: '#faad14',
          P3: '#52c41a'
        }
        return <Badge color={colorMap[val]} text={val} />
      }
    },
    {
      title: '优化建议',
      dataIndex: 'recommendation',
      key: 'recommendation',
      width: 200,
      ellipsis: true,
      render: (text: string) => <Tooltip title={text}>{text}</Tooltip>
    }
  ]

  // 过滤数据
  const filteredData = filterBottleneck === 'all'
    ? funnelData
    : funnelData?.filter(f => f.bottleneck === filterBottleneck)

  return (
    <div style={{ padding: '24px' }}>
      <h1 style={{ fontSize: '24px', fontWeight: 'bold', marginBottom: '24px' }}>
        📊 转化漏斗分析
      </h1>

      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="平均 CTR"
              value={stats.avgCtr * 100}
              precision={2}
              suffix="%"
              prefix={<UserOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="平均加购率"
              value={stats.avgAddRate * 100}
              precision={1}
              suffix="%"
              prefix={<ShoppingCartOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="平均下单率"
              value={stats.avgOrderRate * 100}
              precision={1}
              suffix="%"
              prefix={<DollarOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="总订单数"
              value={stats.totalOrders}
              prefix={<ArrowDownOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* 图表 */}
      <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
        <Col xs={24} lg={8}>
          <Card>
            <ReactECharts option={overallFunnelOption} style={{ height: '400px' }} />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card>
            <ReactECharts option={bottleneckChartOption} style={{ height: '400px' }} />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card>
            <ReactECharts option={scatterChartOption} style={{ height: '400px' }} />
          </Card>
        </Col>
      </Row>

      {/* 过滤器和表格 */}
      <Card
        title="漏斗数据详情"
        extra={
          <Space>
            <Select
              value={filterBottleneck}
              onChange={setFilterBottleneck}
              style={{ width: 150 }}
            >
              <Select.Option value="all">全部</Select.Option>
              <Select.Option value="CTR">CTR瓶颈</Select.Option>
              <Select.Option value="加购率">加购率瓶颈</Select.Option>
              <Select.Option value="下单率">下单率瓶颈</Select.Option>
              <Select.Option value="无">无明显瓶颈</Select.Option>
            </Select>
            <Select
              value={sortBy}
              onChange={setSortBy}
              style={{ width: 150 }}
            >
              <Select.Option value="conversionFunnel">按转化率</Select.Option>
              <Select.Option value="ctr">按CTR</Select.Option>
              <Select.Option value="orders">按订单数</Select.Option>
            </Select>
            <Button type="primary" onClick={() => message.info('导出功能')}>
              导出报表
            </Button>
          </Space>
        }
      >
        <Table
          dataSource={filteredData}
          columns={columns}
          rowKey="sku"
          loading={isLoading}
          scroll={{ x: 1700 }}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`
          }}
        />
      </Card>
    </div>
  )
}
