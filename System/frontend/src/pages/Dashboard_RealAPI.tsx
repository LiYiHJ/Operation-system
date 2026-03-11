import { Row, Col, Card, Statistic, Table, Tag, Progress, Divider, Alert, Spin } from 'antd'
import { ArrowUpOutlined, ArrowDownOutlined, ShoppingCart, DollarOutlined, WarningOutlined, CheckCircleOutlined } from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import dayjs from 'dayjs'
import { dashboardApi } from '../services/api'

export default function Dashboard() {
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs]>([
    dayjs().subtract(7, 'days'),
    dayjs()
  ])

  // ✅ 使用真实 API
  const { data: metricsData, isLoading: metricsLoading, error: metricsError } = useQuery({
    queryKey: ['dashboard-metrics', dateRange],
    queryFn: () => dashboardApi.getMetrics({
      start_date: dateRange[0].format('YYYY-MM-DD'),
      end_date: dateRange[1].format('YYYY-MM-DD')
    }).then(res => res.data)
  })

  const { data: topSkusData, isLoading: topSkusLoading } = useQuery({
    queryKey: ['dashboard-top-skus'],
    queryFn: () => dashboardApi.getTopSkus({ limit: 5 }).then(res => res.data)
  })

  const { data: alertsData, isLoading: alertsLoading } = useQuery({
    queryKey: ['dashboard-alerts'],
    queryFn: () => dashboardApi.getAlerts({ limit: 5 }).then(res => res.data)
  })

  const { data: trendsData, isLoading: trendsLoading } = useQuery({
    queryKey: ['dashboard-trends', dateRange],
    queryFn: () => dashboardApi.getTrends({
      metric: 'all',
      days: 7
    }).then(res => res.data)
  })

  const { data: shopHealthData, isLoading: shopHealthLoading } = useQuery({
    queryKey: ['dashboard-shop-health'],
    queryFn: () => dashboardApi.getShopHealth().then(res => res.data)
  })

  // 加载状态
  if (metricsLoading) {
    return (
      <div style={{ textAlign: 'center', padding: '100px 0' }}>
        <Spin size="large" tip="加载数据中..." />
      </div>
    )
  }

  // 错误状态
  if (metricsError) {
    return (
      <Alert
        message="数据加载失败"
        description={metricsError instanceof Error ? metricsError.message : '请检查后端服务是否启动'}
        type="error"
        showIcon
      />
    )
  }

  // 趋势图表配置
  const trendChartOption = {
    title: { text: '7日营收趋势', left: 'center' },
    tooltip: { trigger: 'axis' },
    legend: { data: ['营收', '订单数'], bottom: 0 },
    xAxis: { type: 'category', data: trendsData?.dates || [] },
    yAxis: [
      { type: 'value', name: '营收 (¥)', position: 'left' },
      { type: 'value', name: '订单数', position: 'right' }
    ],
    series: [
      {
        name: '营收',
        type: 'line',
        data: trendsData?.revenue || [],
        smooth: true,
        itemStyle: { color: '#1890ff' }
      },
      {
        name: '订单数',
        type: 'bar',
        yAxisIndex: 1,
        data: trendsData?.orders || [],
        itemStyle: { color: '#52c41a' }
      }
    ]
  }

  // Top SKU 表格列定义
  const topSkuColumns = [
    {
      title: 'SKU',
      dataIndex: 'sku',
      key: 'sku',
      render: (text: string, record: any) => (
        <Tag color={record.abcClass === 'A' ? 'red' : record.abcClass === 'B' ? 'orange' : 'blue'}>
          {text}
        </Tag>
      )
    },
    {
      title: '商品名称',
      dataIndex: 'productName',
      key: 'productName',
      ellipsis: true
    },
    {
      title: '营收 (¥)',
      dataIndex: 'revenue',
      key: 'revenue',
      render: (val: number) => `¥${val.toLocaleString()}`
    },
    {
      title: '订单数',
      dataIndex: 'orders',
      key: 'orders'
    },
    {
      title: '毛利率',
      dataIndex: 'margin',
      key: 'margin',
      render: (val: number) => (
        <span style={{ color: val > 0.2 ? '#52c41a' : val > 0.1 ? '#faad14' : '#f5222d' }}>
          {(val * 100).toFixed(1)}%
        </span>
      )
    },
    {
      title: 'ABC分类',
      dataIndex: 'abcClass',
      key: 'abcClass',
      render: (val: string) => (
        <Tag color={val === 'A' ? 'red' : val === 'B' ? 'orange' : 'blue'}>{val}</Tag>
      )
    },
    {
      title: '趋势',
      dataIndex: 'trend',
      key: 'trend',
      render: (val: string) => {
        const icon = val === 'up' ? <ArrowUpOutlined style={{ color: '#52c41a' }} /> :
                     val === 'down' ? <ArrowDownOutlined style={{ color: '#f5222d' }} /> :
                     <span style={{ color: '#8c8c8c' }}>—</span>
        return icon
      }
    }
  ]

  // 告警列表
  const alertColumns = [
    {
      title: '优先级',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => {
        const colorMap: Record<string, string> = {
          P0: '#f5222d',
          P1: '#fa8c16',
          P2: '#faad14',
          P3: '#8c8c8c'
        }
        return <Tag color={colorMap[type]}>{type}</Tag>
      }
    },
    {
      title: 'SKU',
      dataIndex: 'sku',
      key: 'sku'
    },
    {
      title: '告警信息',
      dataIndex: 'message',
      key: 'message'
    },
    {
      title: '时间',
      dataIndex: 'timestamp',
      key: 'timestamp',
      render: (val: string) => dayjs(val).format('MM-DD HH:mm')
    }
  ]

  // 店铺健康度表格
  const shopHealthColumns = [
    {
      title: '店铺',
      dataIndex: 'shopName',
      key: 'shopName'
    },
    {
      title: '评分',
      dataIndex: 'rating',
      key: 'rating',
      render: (val: number) => (
        <span style={{ color: val >= 4.8 ? '#52c41a' : val >= 4.5 ? '#faad14' : '#f5222d' }}>
          {val.toFixed(1)} ⭐
        </span>
      )
    },
    {
      title: '延迟率',
      dataIndex: 'delayRate',
      key: 'delayRate',
      render: (val: number) => `${(val * 100).toFixed(1)}%`
    },
    {
      title: '价格竞争力',
      key: 'priceCompetitiveness',
      render: (_: any, record: any) => {
        const green = record.priceCompetitiveness?.green || 0
        const red = record.priceCompetitiveness?.red || 0
        return (
          <div>
            <Tag color="green">绿区 {green}%</Tag>
            <Tag color="red">红区 {red}%</Tag>
          </div>
        )
      }
    },
    {
      title: '订单数',
      dataIndex: 'totalOrders',
      key: 'totalOrders'
    },
    {
      title: '产品数',
      dataIndex: 'totalProducts',
      key: 'totalProducts'
    }
  ]

  return (
    <div>
      {/* 关键指标卡片 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总营收"
              value={metricsData?.totalRevenue || 0}
              precision={2}
              prefix={<DollarOutlined />}
              suffix="¥"
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="总订单数"
              value={metricsData?.totalOrders || 0}
              prefix={<ShoppingCart />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="平均客单价"
              value={metricsData?.avgOrderValue || 0}
              precision={2}
              prefix="¥"
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="毛利率"
              value={(metricsData?.profitMargin || 0) * 100}
              precision={1}
              suffix="%"
              valueStyle={{ color: metricsData?.profitMargin && metricsData.profitMargin > 0.15 ? '#3f8600' : '#cf1322' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="产品总数"
              value={metricsData?.totalProducts || 0}
              valueStyle={{ color: '#595959' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="总展示量"
              value={metricsData?.totalImpressions || 0}
              valueStyle={{ color: '#595959' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="平均CTR"
              value={(metricsData?.avgCtr || 0) * 100}
              precision={2}
              suffix="%"
              valueStyle={{ color: '#595959' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="平均评分"
              value={metricsData?.avgRating || 0}
              precision={1}
              suffix="/ 5.0"
              valueStyle={{ color: metricsData?.avgRating && metricsData.avgRating >= 4.5 ? '#3f8600' : '#fa8c16' }}
            />
          </Card>
        </Col>
      </Row>

      <Divider>详细分析</Divider>

      {/* 趋势图表 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={24}>
          <Card>
            <ReactECharts option={trendChartOption} style={{ height: 300 }} />
          </Card>
        </Col>
      </Row>

      <Row gutter={16}>
        {/* Top SKU 表格 */}
        <Col span={12}>
          <Card title="Top 5 产品" extra={<a href="/abc">查看全部</a>}>
            <Table
              columns={topSkuColumns}
              dataSource={topSkusData || []}
              rowKey="sku"
              pagination={false}
              loading={topSkusLoading}
              size="small"
            />
          </Card>
        </Col>

        {/* 告警列表 */}
        <Col span={12}>
          <Card
            title="告警中心"
            extra={
              <div>
                {alertsData?.summary && (
                  <>
                    <Tag color="red">P0: {alertsData.summary.P0}</Tag>
                    <Tag color="orange">P1: {alertsData.summary.P1}</Tag>
                    <Tag color="blue">P2: {alertsData.summary.P2}</Tag>
                  </>
                )}
              </div>
            }
          >
            <Table
              columns={alertColumns}
              dataSource={alertsData || []}
              rowKey="id"
              pagination={false}
              loading={alertsLoading}
              size="small"
            />
          </Card>
        </Col>
      </Row>

      {/* 店铺健康度 */}
      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col span={24}>
          <Card title="店铺健康度">
            <Table
              columns={shopHealthColumns}
              dataSource={shopHealthData || []}
              rowKey="shopId"
              pagination={false}
              loading={shopHealthLoading}
            />
          </Card>
        </Col>
      </Row>
    </div>
  )
}
