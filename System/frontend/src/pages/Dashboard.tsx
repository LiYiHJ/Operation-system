import { Row, Col, Card, Statistic, Table, Tag, Progress, Divider } from 'antd'
import { ArrowUpOutlined, ArrowDownOutlined, ShoppingCartOutlined, DollarOutlined, WarningOutlined } from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import dayjs from 'dayjs'
import { dashboardApi } from '../services/api'
import type { DashboardMetrics } from '../types'

export default function Dashboard() {
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs]>([
    dayjs().subtract(7, 'days'),
    dayjs()
  ])

  // 调用后端真实API（带 mock fallback）
  const { data: metrics, isLoading, error } = useQuery<DashboardMetrics>({
    queryKey: ['dashboard', dateRange],
    queryFn: () => dashboardApi.getOverview(),
    staleTime: 5 * 60 * 1000, // 5分钟内数据视为新鲜
  })

  // 错误处理
  if (error) {
    console.error('Dashboard API Error:', error)
  }

  // 趋势图表配置
  const trendChartOption = {
    title: { text: '7日营收趋势', left: 'center' },
    tooltip: { trigger: 'axis' },
    legend: { data: ['营收', '订单数'], bottom: 0 },
    xAxis: { type: 'category', data: metrics?.trends?.dates || [] },
    yAxis: [
      { type: 'value', name: '营收 (¥)', position: 'left' },
      { type: 'value', name: '订单数', position: 'right' }
    ],
    series: [
      {
        name: '营收',
        type: 'line',
        data: metrics?.trends?.revenue || [],
        smooth: true,
        itemStyle: { color: '#1890ff' }
      },
      {
        name: '订单数',
        type: 'bar',
        yAxisIndex: 1,
        data: metrics?.trends?.orders || [],
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
          P3: '#52c41a'
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
      title: '问题描述',
      dataIndex: 'message',
      key: 'message'
    },
    {
      title: '操作',
      key: 'action',
      render: () => <a href="#">查看详情 →</a>
    }
  ]

  if (isLoading) return <div>加载中...</div>

  return (
    <div style={{ padding: '24px' }}>
      <h1 style={{ fontSize: '24px', fontWeight: 'bold', marginBottom: '24px' }}>
        📊 运营总览
      </h1>

      {/* 核心指标卡片 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="总营收"
              value={metrics?.totalRevenue || 0}
              precision={2}
              prefix={<DollarOutlined />}
              suffix="¥"
              valueStyle={{ color: '#3f8600' }}
            />
            <div style={{ marginTop: 8 }}>
              <ArrowUpOutlined style={{ color: '#52c41a' }} /> 较昨日 +12.5%
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="订单总数"
              value={metrics?.totalOrders || 0}
              prefix={<ShoppingCartOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
            <div style={{ marginTop: 8 }}>
              <ArrowUpOutlined style={{ color: '#52c41a' }} /> 较昨日 +8.2%
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="客单价"
              value={metrics?.avgOrderValue || 0}
              precision={2}
              prefix="¥"
              valueStyle={{ color: '#722ed1' }}
            />
            <div style={{ marginTop: 8 }}>
              <ArrowDownOutlined style={{ color: '#f5222d' }} /> 较昨日 -2.3%
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="平均毛利率"
              value={metrics ? metrics.profitMargin * 100 : 0}
              precision={1}
              suffix="%"
              valueStyle={{ color: '#13c2c2' }}
            />
            <Progress percent={metrics ? metrics.profitMargin * 100 : 0} showInfo={false} />
          </Card>
        </Col>
      </Row>

      <Divider />

      {/* 趋势图表 + 告警列表 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={16}>
          <Card>
            <ReactECharts option={trendChartOption} style={{ height: '400px' }} />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card
            title={<span><WarningOutlined /> 紧急告警</span>}
            extra={<a href="#">查看全部</a>}
          >
            <Table
              dataSource={metrics?.alerts || []}
              columns={alertColumns}
              pagination={false}
              size="small"
              rowKey="sku"
            />
          </Card>
        </Col>
      </Row>

      <Divider />

      {/* Top SKU 列表 */}
      <Card title="🏆 Top 5 SKU (按营收)">
        <Table
          dataSource={metrics?.topSkus || []}
          columns={topSkuColumns}
          pagination={false}
          rowKey="sku"
        />
      </Card>
    </div>
  )
}
