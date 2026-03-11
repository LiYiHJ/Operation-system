import { Card, Row, Col, Table, Tag, Button, Select, Space, Statistic, Badge, Progress, Tooltip, Alert, message, Modal, Form, InputNumber } from 'antd'
import { WarningOutlined, CheckCircleOutlined, StockOutlined, EditOutlined } from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'

interface InventoryData {
  sku: string
  stockTotal: number
  daysOfSupply: number
  salesVelocity: number
  safetyStock: number
  reorderPoint: number
  alertLevel: 'critical' | 'warning' | 'normal'
  estimatedStockout: string
  recommendation: string
  lastUpdated: string
}

export default function InventoryAlert() {
  const [filterAlert, setFilterAlert] = useState<string>('all')
  const [restockModalVisible, setRestockModalVisible] = useState(false)
  const [selectedSku, setSelectedSku] = useState<InventoryData | null>(null)
  const [form] = Form.useForm()

  // 获取数据
  const { data: inventoryData, isLoading } = useQuery<InventoryData[]>({
    queryKey: ['inventory-alert', filterAlert],
    queryFn: async () => {
      // TODO: 调用后端 API
      return [
        {
          sku: 'SKU-001',
          stockTotal: 150,
          daysOfSupply: 5,
          salesVelocity: 30,
          safetyStock: 90,
          reorderPoint: 120,
          alertLevel: 'critical',
          estimatedStockout: '2026-03-13',
          recommendation: '立即补货，建议订货量：180件',
          lastUpdated: '2026-03-08 16:00'
        },
        {
          sku: 'SKU-002',
          stockTotal: 200,
          daysOfSupply: 12,
          salesVelocity: 16.7,
          safetyStock: 100,
          reorderPoint: 150,
          alertLevel: 'warning',
          estimatedStockout: '2026-03-20',
          recommendation: '准备补货计划，建议订货量：150件',
          lastUpdated: '2026-03-08 16:00'
        },
        {
          sku: 'SKU-003',
          stockTotal: 500,
          daysOfSupply: 25,
          salesVelocity: 20,
          safetyStock: 120,
          reorderPoint: 180,
          alertLevel: 'normal',
          estimatedStockout: '2026-04-02',
          recommendation: '库存充足，无需补货',
          lastUpdated: '2026-03-08 16:00'
        },
        {
          sku: 'SKU-004',
          stockTotal: 80,
          daysOfSupply: 4,
          salesVelocity: 20,
          safetyStock: 80,
          reorderPoint: 120,
          alertLevel: 'critical',
          estimatedStockout: '2026-03-12',
          recommendation: '紧急补货，建议订货量：200件',
          lastUpdated: '2026-03-08 16:00'
        },
        {
          sku: 'SKU-005',
          stockTotal: 300,
          daysOfSupply: 15,
          salesVelocity: 20,
          safetyStock: 100,
          reorderPoint: 150,
          alertLevel: 'normal',
          estimatedStockout: '2026-03-23',
          recommendation: '库存健康，保持监控',
          lastUpdated: '2026-03-08 16:00'
        }
      ]
    }
  })

  // 统计数据
  const stats = {
    critical: inventoryData?.filter(i => i.alertLevel === 'critical').length || 0,
    warning: inventoryData?.filter(i => i.alertLevel === 'warning').length || 0,
    normal: inventoryData?.filter(i => i.alertLevel === 'normal').length || 0,
    totalStock: inventoryData?.reduce((sum, i) => sum + i.stockTotal, 0) || 0,
    avgDaysOfSupply: inventoryData ? inventoryData.reduce((sum, i) => sum + i.daysOfSupply, 0) / inventoryData.length : 0
  }

  // 库存预警分布
  const alertDistributionOption = {
    title: { text: '库存预警分布', left: 'center' },
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
          { value: stats.critical, name: '紧急', itemStyle: { color: '#f5222d' } },
          { value: stats.warning, name: '警告', itemStyle: { color: '#faad14' } },
          { value: stats.normal, name: '正常', itemStyle: { color: '#52c41a' } }
        ]
      }
    ]
  }

  // 库存天数分布
  const stockDaysOption = {
    title: { text: '库存周转天数分布', left: 'center' },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: {
      type: 'category',
      data: inventoryData?.map(i => i.sku) || []
    },
    yAxis: { type: 'value', name: '库存天数' },
    series: [
      {
        type: 'bar',
        data: inventoryData?.map(i => {
          let color = '#52c41a'
          if (i.daysOfSupply < 7) color = '#f5222d'
          else if (i.daysOfSupply < 14) color = '#faad14'
          return {
            value: i.daysOfSupply,
            itemStyle: { color }
          }
        }) || [],
        label: { show: true, position: 'top' }
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
      title: '预警状态',
      dataIndex: 'alertLevel',
      key: 'alertLevel',
      width: 120,
      render: (val: string) => {
        const config: Record<string, { color: string; text: string; icon: any }> = {
          critical: { color: 'error', text: '紧急', icon: <WarningOutlined /> },
          warning: { color: 'warning', text: '警告', icon: <WarningOutlined /> },
          normal: { color: 'success', text: '正常', icon: <CheckCircleOutlined /> }
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
        { text: '紧急', value: 'critical' },
        { text: '警告', value: 'warning' },
        { text: '正常', value: 'normal' }
      ],
      onFilter: (value: any, record: InventoryData) => record.alertLevel === value
    },
    {
      title: '当前库存',
      dataIndex: 'stockTotal',
      key: 'stockTotal',
      width: 120,
      render: (val: number, record: InventoryData) => (
        <div>
          <div>{val.toLocaleString()} 件</div>
          <Progress
            percent={(val / record.reorderPoint) * 100}
            size="small"
            status={val < record.safetyStock ? 'exception' : 'active'}
            showInfo={false}
          />
        </div>
      )
    },
    {
      title: '库存天数',
      dataIndex: 'daysOfSupply',
      key: 'daysOfSupply',
      width: 120,
      sorter: (a: InventoryData, b: InventoryData) => a.daysOfSupply - b.daysOfSupply,
      render: (val: number) => (
        <span style={{ color: val < 7 ? '#f5222d' : val < 14 ? '#faad14' : '#52c41a' }}>
          {val} 天
        </span>
      )
    },
    {
      title: '销售速度',
      dataIndex: 'salesVelocity',
      key: 'salesVelocity',
      width: 120,
      render: (val: number) => `${val.toFixed(1)} 件/天`
    },
    {
      title: '安全库存',
      dataIndex: 'safetyStock',
      key: 'safetyStock',
      width: 120,
      render: (val: number) => val.toLocaleString()
    },
    {
      title: '补货点',
      dataIndex: 'reorderPoint',
      key: 'reorderPoint',
      width: 120,
      render: (val: number) => val.toLocaleString()
    },
    {
      title: '预计断货日期',
      dataIndex: 'estimatedStockout',
      key: 'estimatedStockout',
      width: 150,
      render: (val: string, record: InventoryData) => (
        <span style={{ color: record.alertLevel === 'critical' ? '#f5222d' : 'inherit' }}>
          {val}
        </span>
      )
    },
    {
      title: '补货建议',
      dataIndex: 'recommendation',
      key: 'recommendation',
      width: 200,
      ellipsis: true,
      render: (text: string) => <Tooltip title={text}>{text}</Tooltip>
    },
    {
      title: '更新时间',
      dataIndex: 'lastUpdated',
      key: 'lastUpdated',
      width: 150
    },
    {
      title: '操作',
      key: 'action',
      fixed: 'right' as const,
      width: 100,
      render: (_: any, record: InventoryData) => (
        <Button
          type="link"
          size="small"
          icon={<EditOutlined />}
          onClick={() => handleRestock(record)}
        >
          补货
        </Button>
      )
    }
  ]

  // 处理补货
  const handleRestock = (sku: InventoryData) => {
    setSelectedSku(sku)
    form.setFieldsValue({
      orderQuantity: Math.ceil((sku.reorderPoint - sku.stockTotal + sku.safetyStock) * 1.2)
    })
    setRestockModalVisible(true)
  }

  // 提交补货
  const handleSubmitRestock = async () => {
    try {
      const values = await form.validateFields()
      message.success(`已提交 ${selectedSku?.sku} 的补货申请：${values.orderQuantity} 件`)
      setRestockModalVisible(false)
      setSelectedSku(null)
    } catch (error) {
      message.error('提交失败')
    }
  }

  // 过滤数据
  const filteredData = filterAlert === 'all'
    ? inventoryData
    : inventoryData?.filter(i => i.alertLevel === filterAlert)

  return (
    <div style={{ padding: '24px' }}>
      <h1 style={{ fontSize: '24px', fontWeight: 'bold', marginBottom: '24px' }}>
        📦 库存预警
      </h1>

      {/* 紧急告警 */}
      {stats.critical > 0 && (
        <Alert
          message="紧急库存预警"
          description={`有 ${stats.critical} 个商品库存低于安全水平，需要立即补货！`}
          type="error"
          showIcon
          icon={<WarningOutlined />}
          style={{ marginBottom: '24px' }}
        />
      )}

      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="紧急预警"
              value={stats.critical}
              prefix={<WarningOutlined style={{ color: '#f5222d' }} />}
              suffix="个"
              valueStyle={{ color: '#f5222d' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="警告预警"
              value={stats.warning}
              prefix={<WarningOutlined style={{ color: '#faad14' }} />}
              suffix="个"
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="总库存量"
              value={stats.totalStock}
              prefix={<StockOutlined />}
              suffix="件"
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="平均库存天数"
              value={stats.avgDaysOfSupply}
              precision={1}
              suffix="天"
            />
          </Card>
        </Col>
      </Row>

      {/* 图表 */}
      <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
        <Col xs={24} lg={12}>
          <Card>
            <ReactECharts option={alertDistributionOption} style={{ height: '350px' }} />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card>
            <ReactECharts option={stockDaysOption} style={{ height: '350px' }} />
          </Card>
        </Col>
      </Row>

      {/* 过滤器和表格 */}
      <Card
        title="库存详情"
        extra={
          <Space>
            <Select
              value={filterAlert}
              onChange={setFilterAlert}
              style={{ width: 120 }}
            >
              <Select.Option value="all">全部</Select.Option>
              <Select.Option value="critical">紧急</Select.Option>
              <Select.Option value="warning">警告</Select.Option>
              <Select.Option value="normal">正常</Select.Option>
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

      {/* 补货模态框 */}
      <Modal
        title={`补货申请 - ${selectedSku?.sku}`}
        open={restockModalVisible}
        onCancel={() => setRestockModalVisible(false)}
        onOk={handleSubmitRestock}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="当前库存">
                <InputNumber value={selectedSku?.stockTotal} disabled style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="安全库存">
                <InputNumber value={selectedSku?.safetyStock} disabled style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="补货点">
                <InputNumber value={selectedSku?.reorderPoint} disabled style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="销售速度 (件/天)">
                <InputNumber value={selectedSku?.salesVelocity} disabled style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={24}>
              <Form.Item
                label="建议订货量"
                name="orderQuantity"
                rules={[{ required: true, message: '请输入订货量' }]}
              >
                <InputNumber style={{ width: '100%' }} min={0} />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
    </div>
  )
}
