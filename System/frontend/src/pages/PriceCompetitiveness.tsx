import { Table, Tag, Card, Row, Col, Statistic, Button, Select, Space, Badge, Tooltip, message } from 'antd'
import { DollarOutlined, WarningOutlined, CheckCircleOutlined, ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'

interface PriceCompetitivenessData {
  sku: string
  ourPrice: number
  marketPrice: number
  priceGap: number
  competitiveness: 'green' | 'yellow' | 'red'
  ctr: number
  conversionRate: number
  roas: number
  salesVelocity: number
  recommendation: string
  lastUpdated: string
}

export default function PriceCompetitiveness() {
  const [filterZone, setFilterZone] = useState<string>('all')
  const [sortBy, setSortBy] = useState<string>('priceGap')

  // 获取数据
  const { data: priceData, isLoading } = useQuery<PriceCompetitivenessData[]>({
    queryKey: ['price-competitiveness', filterZone, sortBy],
    queryFn: async () => {
      // TODO: 调用后端 API
      return [
        {
          sku: 'SKU-001',
          ourPrice: 1299,
          marketPrice: 1199,
          priceGap: 100,
          competitiveness: 'green',
          ctr: 0.028,
          conversionRate: 0.15,
          roas: 4.5,
          salesVelocity: 8.5,
          recommendation: '价格有竞争力，保持当前策略',
          lastUpdated: '2026-03-08 15:30'
        },
        {
          sku: 'SKU-002',
          ourPrice: 899,
          marketPrice: 949,
          priceGap: -50,
          competitiveness: 'yellow',
          ctr: 0.018,
          conversionRate: 0.12,
          roas: 2.8,
          salesVelocity: 5.2,
          recommendation: '价格略低，可适当提价5%',
          lastUpdated: '2026-03-08 14:45'
        },
        {
          sku: 'SKU-003',
          ourPrice: 1599,
          marketPrice: 1299,
          priceGap: 300,
          competitiveness: 'red',
          ctr: 0.012,
          conversionRate: 0.08,
          roas: 1.2,
          salesVelocity: 2.1,
          recommendation: '价格过高，建议降价15%或优化价值感知',
          lastUpdated: '2026-03-08 16:00'
        },
        {
          sku: 'SKU-004',
          ourPrice: 799,
          marketPrice: 849,
          priceGap: -50,
          competitiveness: 'green',
          ctr: 0.025,
          conversionRate: 0.14,
          roas: 3.9,
          salesVelocity: 7.2,
          recommendation: '价格优势明显，可维持或小幅提价',
          lastUpdated: '2026-03-08 15:15'
        },
        {
          sku: 'SKU-005',
          ourPrice: 1999,
          marketPrice: 1599,
          priceGap: 400,
          competitiveness: 'red',
          ctr: 0.008,
          conversionRate: 0.05,
          roas: 0.6,
          salesVelocity: 1.2,
          recommendation: '严重价格劣势，需立即降价20%或优化产品',
          lastUpdated: '2026-03-08 15:50'
        }
      ]
    }
  })

  // 统计数据
  const stats = {
    greenZone: priceData?.filter(p => p.competitiveness === 'green').length || 0,
    yellowZone: priceData?.filter(p => p.competitiveness === 'yellow').length || 0,
    redZone: priceData?.filter(p => p.competitiveness === 'red').length || 0,
    avgPriceGap: priceData ? priceData.reduce((sum, p) => sum + p.priceGap, 0) / priceData.length : 0,
    avgConversionRate: priceData ? priceData.reduce((sum, p) => sum + p.conversionRate, 0) / priceData.length : 0
  }

  // 价格竞争力分布图表
  const competitivenessChartOption = {
    title: { text: '价格竞争力分布', left: 'center' },
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
          { value: stats.greenZone, name: '绿区', itemStyle: { color: '#52c41a' } },
          { value: stats.yellowZone, name: '黄区', itemStyle: { color: '#faad14' } },
          { value: stats.redZone, name: '红区', itemStyle: { color: '#f5222d' } }
        ]
      }
    ]
  }

  // 价格差距散点图
  const priceGapChartOption = {
    title: { text: '价格差距 vs 转化率', left: 'center' },
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        return `${params.data[2]}<br/>价格差距: ¥${params.data[0]}<br/>转化率: ${(params.data[1] * 100).toFixed(1)}%`
      }
    },
    xAxis: {
      type: 'value',
      name: '价格差距 (¥)',
      splitLine: { show: true }
    },
    yAxis: {
      type: 'value',
      name: '转化率',
      min: 0,
      max: 0.3,
      axisLabel: { formatter: (value: number) => `${(value * 100).toFixed(0)}%` }
    },
    series: [
      {
        type: 'scatter',
        symbolSize: 20,
        data: priceData?.map(p => [
          p.priceGap,
          p.conversionRate,
          p.sku,
          p.competitiveness
        ]) || [],
        itemStyle: {
          color: (params: any) => {
            const competitiveness = params.data[3]
            return competitiveness === 'green' ? '#52c41a' :
                   competitiveness === 'yellow' ? '#faad14' : '#f5222d'
          }
        }
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
      title: '竞争力区域',
      dataIndex: 'competitiveness',
      key: 'competitiveness',
      width: 130,
      render: (val: string) => {
        const config: Record<string, { color: string; text: string; icon: any }> = {
          green: { color: 'success', text: '绿区', icon: <CheckCircleOutlined /> },
          yellow: { color: 'warning', text: '黄区', icon: <WarningOutlined /> },
          red: { color: 'error', text: '红区', icon: <WarningOutlined /> }
        }
        const { color, text, icon } = config[val]
        return (
          <Badge status={color as any} text={
            <Space>
              {icon}
              <span>{text}</span>
            </Space>
          } />
        )
      },
      filters: [
        { text: '绿区', value: 'green' },
        { text: '黄区', value: 'yellow' },
        { text: '红区', value: 'red' }
      ],
      onFilter: (value: any, record: PriceCompetitivenessData) => record.competitiveness === value
    },
    {
      title: '我们的价格',
      dataIndex: 'ourPrice',
      key: 'ourPrice',
      width: 120,
      render: (val: number) => `¥${val.toLocaleString()}`
    },
    {
      title: '市场均价',
      dataIndex: 'marketPrice',
      key: 'marketPrice',
      width: 120,
      render: (val: number) => `¥${val.toLocaleString()}`
    },
    {
      title: '价格差距',
      dataIndex: 'priceGap',
      key: 'priceGap',
      width: 130,
      sorter: (a: PriceCompetitivenessData, b: PriceCompetitivenessData) => a.priceGap - b.priceGap,
      render: (val: number) => (
        <span style={{ color: val > 0 ? '#f5222d' : '#52c41a' }}>
          {val > 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
          {' '}¥{Math.abs(val).toLocaleString()}
        </span>
      )
    },
    {
      title: 'CTR',
      dataIndex: 'ctr',
      key: 'ctr',
      width: 90,
      render: (val: number) => `${(val * 100).toFixed(2)}%`
    },
    {
      title: '转化率',
      dataIndex: 'conversionRate',
      key: 'conversionRate',
      width: 100,
      render: (val: number) => (
        <span style={{ color: val > 0.1 ? '#52c41a' : '#f5222d' }}>
          {(val * 100).toFixed(1)}%
        </span>
      )
    },
    {
      title: 'ROAS',
      dataIndex: 'roas',
      key: 'roas',
      width: 90,
      render: (val: number) => (
        <span style={{ color: val > 2 ? '#52c41a' : '#f5222d' }}>
          {val.toFixed(1)}
        </span>
      )
    },
    {
      title: '销售速度',
      dataIndex: 'salesVelocity',
      key: 'salesVelocity',
      width: 100,
      render: (val: number) => `${val.toFixed(1)} 件/天`
    },
    {
      title: '优化建议',
      dataIndex: 'recommendation',
      key: 'recommendation',
      width: 250,
      ellipsis: true,
      render: (text: string) => (
        <Tooltip title={text}>
          {text}
        </Tooltip>
      )
    },
    {
      title: '更新时间',
      dataIndex: 'lastUpdated',
      key: 'lastUpdated',
      width: 150
    }
  ]

  // 过滤数据
  const filteredData = filterZone === 'all'
    ? priceData
    : priceData?.filter(p => p.competitiveness === filterZone)

  return (
    <div style={{ padding: '24px' }}>
      <h1 style={{ fontSize: '24px', fontWeight: 'bold', marginBottom: '24px' }}>
        💰 价格竞争力分析
      </h1>

      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="绿区商品"
              value={stats.greenZone}
              prefix={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
              suffix="个"
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="黄区商品"
              value={stats.yellowZone}
              prefix={<WarningOutlined style={{ color: '#faad14' }} />}
              suffix="个"
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="红区商品"
              value={stats.redZone}
              prefix={<WarningOutlined style={{ color: '#f5222d' }} />}
              suffix="个"
              valueStyle={{ color: '#f5222d' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="平均价格差距"
              value={stats.avgPriceGap}
              prefix={<DollarOutlined />}
              suffix="¥"
            />
          </Card>
        </Col>
      </Row>

      {/* 图表 */}
      <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
        <Col xs={24} lg={12}>
          <Card>
            <ReactECharts option={competitivenessChartOption} style={{ height: '350px' }} />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card>
            <ReactECharts option={priceGapChartOption} style={{ height: '350px' }} />
          </Card>
        </Col>
      </Row>

      {/* 过滤器和表格 */}
      <Card
        title="价格竞争力详情"
        extra={
          <Space>
            <Select
              value={filterZone}
              onChange={setFilterZone}
              style={{ width: 120 }}
            >
              <Select.Option value="all">全部</Select.Option>
              <Select.Option value="green">绿区</Select.Option>
              <Select.Option value="yellow">黄区</Select.Option>
              <Select.Option value="red">红区</Select.Option>
            </Select>
            <Select
              value={sortBy}
              onChange={setSortBy}
              style={{ width: 150 }}
            >
              <Select.Option value="priceGap">按价格差距</Select.Option>
              <Select.Option value="conversionRate">按转化率</Select.Option>
              <Select.Option value="salesVelocity">按销售速度</Select.Option>
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
          scroll={{ x: 1600 }}
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
