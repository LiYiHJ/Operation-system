import { Card, Row, Col, Table, Tag, Button, Select, Space, Statistic, Badge, Progress, Tooltip, message, Modal, Form, InputNumber, Switch, Divider } from 'antd'
import { DollarOutlined, EyeOutlined, ShoppingCartOutlined, WarningOutlined, CheckCircleOutlined, EditOutlined, PauseCircleOutlined, PlayCircleOutlined } from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'

interface AdsData {
  sku: string
  campaignName: string
  campaignStatus: 'active' | 'paused' | 'ended'
  impressions: number
  clicks: number
  ctr: number
  adSpend: number
  adRevenue: number
  roas: number
  cpc: number
  acos: number
  orders: number
  avgOrderValue: number
  performance: 'excellent' | 'good' | 'poor' | 'critical'
  recommendation: string
  lastUpdated: string
}

export default function AdsManagement() {
  const [filterStatus, setFilterStatus] = useState<string>('all')
  const [filterPerformance, setFilterPerformance] = useState<string>('all')
  const [editModalVisible, setEditModalVisible] = useState(false)
  const [selectedAds, setSelectedAds] = useState<AdsData | null>(null)
  const [form] = Form.useForm()

  // 获取数据
  const { data: adsData, isLoading } = useQuery<AdsData[]>({
    queryKey: ['ads-management', filterStatus, filterPerformance],
    queryFn: async () => {
      // TODO: 调用后端 API
      return [
        {
          sku: 'SKU-001',
          campaignName: '热销商品推广',
          campaignStatus: 'active',
          impressions: 50000,
          clicks: 1500,
          ctr: 0.03,
          adSpend: 4500,
          adRevenue: 18000,
          roas: 4.0,
          cpc: 3.0,
          acos: 0.25,
          orders: 45,
          avgOrderValue: 400,
          performance: 'excellent',
          recommendation: 'ROAS 优秀，建议增加预算 20%',
          lastUpdated: '2026-03-08 16:00'
        },
        {
          sku: 'SKU-002',
          campaignName: '新品推广',
          campaignStatus: 'active',
          impressions: 30000,
          clicks: 600,
          ctr: 0.02,
          adSpend: 2400,
          adRevenue: 4800,
          roas: 2.0,
          cpc: 4.0,
          acos: 0.50,
          orders: 12,
          avgOrderValue: 400,
          performance: 'good',
          recommendation: 'ROAS 达标，优化关键词提升 CTR',
          lastUpdated: '2026-03-08 16:00'
        },
        {
          sku: 'SKU-003',
          campaignName: '清仓促销',
          campaignStatus: 'active',
          impressions: 20000,
          clicks: 200,
          ctr: 0.01,
          adSpend: 1200,
          adRevenue: 960,
          roas: 0.8,
          cpc: 6.0,
          acos: 1.25,
          orders: 3,
          avgOrderValue: 320,
          performance: 'critical',
          recommendation: 'ROAS 严重低于标准，建议暂停或优化',
          lastUpdated: '2026-03-08 16:00'
        },
        {
          sku: 'SKU-004',
          campaignName: '日常推广',
          campaignStatus: 'paused',
          impressions: 15000,
          clicks: 375,
          ctr: 0.025,
          adSpend: 1125,
          adRevenue: 3375,
          roas: 3.0,
          cpc: 3.0,
          acos: 0.33,
          orders: 9,
          avgOrderValue: 375,
          performance: 'good',
          recommendation: '暂停中，ROAS 良好',
          lastUpdated: '2026-03-08 14:00'
        },
        {
          sku: 'SKU-005',
          campaignName: '测试推广',
          campaignStatus: 'active',
          impressions: 10000,
          clicks: 150,
          ctr: 0.015,
          adSpend: 600,
          adRevenue: 900,
          roas: 1.5,
          cpc: 4.0,
          acos: 0.67,
          orders: 3,
          avgOrderValue: 300,
          performance: 'poor',
          recommendation: 'ROAS 偏低，需要优化关键词或调整出价',
          lastUpdated: '2026-03-08 16:00'
        }
      ]
    }
  })

  // 统计数据
  const stats = {
    totalSpend: adsData?.filter(a => a.campaignStatus === 'active').reduce((sum, a) => sum + a.adSpend, 0) || 0,
    totalRevenue: adsData?.filter(a => a.campaignStatus === 'active').reduce((sum, a) => sum + a.adRevenue, 0) || 0,
    avgRoas: adsData && adsData.filter(a => a.campaignStatus === 'active').length > 0
      ? adsData.filter(a => a.campaignStatus === 'active').reduce((sum, a) => sum + a.roas, 0) / adsData.filter(a => a.campaignStatus === 'active').length
      : 0,
    activeCampaigns: adsData?.filter(a => a.campaignStatus === 'active').length || 0,
    excellentCount: adsData?.filter(a => a.performance === 'excellent').length || 0,
    criticalCount: adsData?.filter(a => a.performance === 'critical').length || 0
  }

  // ROAS 分布图
  const roasDistributionOption = {
    title: { text: 'ROAS 分布', left: 'center' },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: { type: 'category', data: ['< 1.0', '1.0-2.0', '2.0-3.0', '> 3.0'] },
    yAxis: { type: 'value', name: '活动数' },
    series: [
      {
        type: 'bar',
        data: [
          {
            value: adsData?.filter(a => a.roas < 1.0).length || 0,
            itemStyle: { color: '#f5222d' }
          },
          {
            value: adsData?.filter(a => a.roas >= 1.0 && a.roas < 2.0).length || 0,
            itemStyle: { color: '#faad14' }
          },
          {
            value: adsData?.filter(a => a.roas >= 2.0 && a.roas < 3.0).length || 0,
            itemStyle: { color: '#52c41a' }
          },
          {
            value: adsData?.filter(a => a.roas >= 3.0).length || 0,
            itemStyle: { color: '#1890ff' }
          }
        ],
        label: { show: true, position: 'top' }
      }
    ]
  }

  // 广告花费 vs 收入散点图
  const spendVsRevenueOption = {
    title: { text: '广告花费 vs 收入', left: 'center' },
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        return `${params.data[2]}<br/>花费: ¥${params.data[0]}<br/>收入: ¥${params.data[1]}<br/>ROAS: ${params.data[3].toFixed(1)}`
      }
    },
    xAxis: {
      type: 'value',
      name: '广告花费 (¥)',
      splitLine: { show: true }
    },
    yAxis: {
      type: 'value',
      name: '广告收入 (¥)'
    },
    series: [
      {
        type: 'scatter',
        symbolSize: 20,
        data: adsData?.map(a => [a.adSpend, a.adRevenue, a.sku, a.roas]) || [],
        itemStyle: {
          color: (params: any) => {
            const roas = params.data[3]
            return roas > 3 ? '#52c41a' : roas > 2 ? '#1890ff' : roas > 1 ? '#faad14' : '#f5222d'
          }
        }
      },
      {
        type: 'line',
        data: [[0, 0], [5000, 10000], [10000, 20000]],
        lineStyle: { type: 'dashed', color: '#8c8c8c' },
        symbol: 'none',
        name: 'ROAS = 2.0'
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
      title: '活动名称',
      dataIndex: 'campaignName',
      key: 'campaignName',
      width: 180,
      ellipsis: true
    },
    {
      title: '状态',
      dataIndex: 'campaignStatus',
      key: 'campaignStatus',
      width: 100,
      render: (val: string) => {
        const config: Record<string, { color: string; text: string }> = {
          active: { color: 'success', text: '运行中' },
          paused: { color: 'warning', text: '已暂停' },
          ended: { color: 'default', text: '已结束' }
        }
        const { color, text } = config[val]
        return <Badge status={color as any} text={text} />
      }
    },
    {
      title: '表现',
      dataIndex: 'performance',
      key: 'performance',
      width: 100,
      render: (val: string) => {
        const config: Record<string, { color: string; text: string }> = {
          excellent: { color: 'green', text: '优秀' },
          good: { color: 'blue', text: '良好' },
          poor: { color: 'orange', text: '较差' },
          critical: { color: 'red', text: '严重' }
        }
        const { color, text } = config[val]
        return <Tag color={color}>{text}</Tag>
      }
    },
    {
      title: '展示量',
      dataIndex: 'impressions',
      key: 'impressions',
      width: 100,
      render: (val: number) => val.toLocaleString()
    },
    {
      title: '点击量',
      dataIndex: 'clicks',
      key: 'clicks',
      width: 100,
      render: (val: number) => val.toLocaleString()
    },
    {
      title: 'CTR',
      dataIndex: 'ctr',
      key: 'ctr',
      width: 100,
      render: (val: number) => `${(val * 100).toFixed(2)}%`
    },
    {
      title: '广告花费',
      dataIndex: 'adSpend',
      key: 'adSpend',
      width: 120,
      render: (val: number) => `¥${val.toLocaleString()}`
    },
    {
      title: '广告收入',
      dataIndex: 'adRevenue',
      key: 'adRevenue',
      width: 120,
      render: (val: number) => `¥${val.toLocaleString()}`
    },
    {
      title: 'ROAS',
      dataIndex: 'roas',
      key: 'roas',
      width: 100,
      sorter: (a: AdsData, b: AdsData) => a.roas - b.roas,
      render: (val: number) => (
        <span style={{ color: val > 3 ? '#52c41a' : val > 2 ? '#1890ff' : val > 1 ? '#faad14' : '#f5222d' }}>
          {val.toFixed(1)}
        </span>
      )
    },
    {
      title: 'CPC',
      dataIndex: 'cpc',
      key: 'cpc',
      width: 100,
      render: (val: number) => `¥${val.toFixed(1)}`
    },
    {
      title: 'ACOS',
      dataIndex: 'acos',
      key: 'acos',
      width: 100,
      render: (val: number) => `${(val * 100).toFixed(0)}%`
    },
    {
      title: '订单数',
      dataIndex: 'orders',
      key: 'orders',
      width: 100
    },
    {
      title: '优化建议',
      dataIndex: 'recommendation',
      key: 'recommendation',
      width: 200,
      ellipsis: true,
      render: (text: string) => <Tooltip title={text}>{text}</Tooltip>
    },
    {
      title: '操作',
      key: 'action',
      fixed: 'right' as const,
      width: 150,
      render: (_: any, record: AdsData) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          {record.campaignStatus === 'active' ? (
            <Button
              type="link"
              size="small"
              icon={<PauseCircleOutlined />}
              onClick={() => message.info('暂停活动')}
            >
              暂停
            </Button>
          ) : (
            <Button
              type="link"
              size="small"
              icon={<PlayCircleOutlined />}
              onClick={() => message.info('启动活动')}
            >
              启动
            </Button>
          )}
        </Space>
      )
    }
  ]

  // 处理编辑
  const handleEdit = (ads: AdsData) => {
    setSelectedAds(ads)
    form.setFieldsValue(ads)
    setEditModalVisible(true)
  }

  // 保存编辑
  const handleSaveEdit = async () => {
    try {
      const values = await form.validateFields()
      message.success(`活动 ${selectedAds?.campaignName} 更新成功`)
      setEditModalVisible(false)
      setSelectedAds(null)
    } catch (error) {
      message.error('保存失败')
    }
  }

  // 过滤数据
  const filteredData = adsData?.filter(a => {
    const statusMatch = filterStatus === 'all' || a.campaignStatus === filterStatus
    const performanceMatch = filterPerformance === 'all' || a.performance === filterPerformance
    return statusMatch && performanceMatch
  })

  return (
    <div style={{ padding: '24px' }}>
      <h1 style={{ fontSize: '24px', fontWeight: 'bold', marginBottom: '24px' }}>
        🎯 广告管理
      </h1>

      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="总广告花费"
              value={stats.totalSpend}
              prefix={<DollarOutlined />}
              suffix="¥"
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="总广告收入"
              value={stats.totalRevenue}
              prefix={<DollarOutlined />}
              suffix="¥"
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="平均 ROAS"
              value={stats.avgRoas}
              precision={1}
              suffix="倍"
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="活跃活动数"
              value={stats.activeCampaigns}
              prefix={<EyeOutlined />}
              suffix="个"
            />
          </Card>
        </Col>
      </Row>

      {/* 图表 */}
      <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
        <Col xs={24} lg={12}>
          <Card>
            <ReactECharts option={roasDistributionOption} style={{ height: '350px' }} />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card>
            <ReactECharts option={spendVsRevenueOption} style={{ height: '350px' }} />
          </Card>
        </Col>
      </Row>

      {/* 过滤器和表格 */}
      <Card
        title="广告活动列表"
        extra={
          <Space>
            <Select
              value={filterStatus}
              onChange={setFilterStatus}
              style={{ width: 120 }}
            >
              <Select.Option value="all">全部状态</Select.Option>
              <Select.Option value="active">运行中</Select.Option>
              <Select.Option value="paused">已暂停</Select.Option>
              <Select.Option value="ended">已结束</Select.Option>
            </Select>
            <Select
              value={filterPerformance}
              onChange={setFilterPerformance}
              style={{ width: 120 }}
            >
              <Select.Option value="all">全部表现</Select.Option>
              <Select.Option value="excellent">优秀</Select.Option>
              <Select.Option value="good">良好</Select.Option>
              <Select.Option value="poor">较差</Select.Option>
              <Select.Option value="critical">严重</Select.Option>
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
          scroll={{ x: 2000 }}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`
          }}
        />
      </Card>

      {/* 编辑模态框 */}
      <Modal
        title={`编辑广告活动 - ${selectedAds?.campaignName}`}
        open={editModalVisible}
        onCancel={() => setEditModalVisible(false)}
        onOk={handleSaveEdit}
        width={800}
      >
        <Form form={form} layout="vertical">
          <Divider orientation="left">基础信息</Divider>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="SKU">
                <InputNumber value={selectedAds?.sku} disabled style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="活动状态" name="campaignStatus">
                <Select>
                  <Select.Option value="active">运行中</Select.Option>
                  <Select.Option value="paused">已暂停</Select.Option>
                  <Select.Option value="ended">已结束</Select.Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Divider orientation="left">预算设置</Divider>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="日预算 (¥)" name="dailyBudget">
                <InputNumber style={{ width: '100%' }} min={0} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="单次点击出价 (¥)" name="cpc">
                <InputNumber style={{ width: '100%' }} min={0} step={0.1} />
              </Form.Item>
            </Col>
          </Row>

          <Divider orientation="left">目标设置</Divider>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="目标 ROAS" name="targetRoas">
                <InputNumber style={{ width: '100%' }} min={0} step={0.1} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="目标 ACOS (%)" name="targetAcos">
                <InputNumber style={{ width: '100%' }} min={0} max={100} />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
    </div>
  )
}
