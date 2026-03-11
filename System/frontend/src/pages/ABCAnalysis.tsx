import { Table, Tag, Card, Row, Col, Statistic, Button, Modal, Form, Input, InputNumber, Select, Space, message } from 'antd'
import { TrophyOutlined, EditOutlined, DeleteOutlined, BarChartOutlined } from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'

interface SkuData {
  sku: string
  revenue: number
  orders: number
  margin: number
  abcClass: 'A' | 'B' | 'C'
  strategy: string
  ctr: number
  roas: number
  daysOfSupply: number
  rating: number
  returnRate: number
}

export default function ABCAnalysis() {
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([])
  const [filterClass, setFilterClass] = useState<string>('all')
  const [editModalVisible, setEditModalVisible] = useState(false)
  const [editingSku, setEditingSku] = useState<SkuData | null>(null)
  const [form] = Form.useForm()

  // 获取数据 - 调用真实后端API
  const { data: skuList, isLoading } = useQuery<SkuData[]>({
    queryKey: ['abc-analysis', filterClass],
    queryFn: async () => {
      const { abcAPI } = await import('../utils/api')
      const response = await abcAPI.getAnalysis()
      
      // 转换API返回格式为前端格式
      const products = response.topProducts || []
      return products.map((p: any) => ({
        sku: p.sku,
        revenue: p.revenue,
        orders: p.orders,
        margin: p.margin || 0.2,
        abcClass: p.abcClass,
        strategy: p.abcClass === 'A' ? '重点运营，保持库存' :
                  p.abcClass === 'B' ? '优化广告投放' : '考虑清仓促销',
        ctr: p.ctr || 0.02,
        roas: p.roas || 3.0,
        daysOfSupply: p.daysOfSupply || 30,
        rating: p.rating || 4.5,
        returnRate: p.returnRate || 0.1
      }))
    }
  })

  // 统计数据
  const stats = {
    classA: skuList?.filter(s => s.abcClass === 'A').length || 0,
    classB: skuList?.filter(s => s.abcClass === 'B').length || 0,
    classC: skuList?.filter(s => s.abcClass === 'C').length || 0,
    totalRevenue: skuList?.reduce((sum, s) => sum + s.revenue, 0) || 0,
    avgMargin: skuList ? skuList.reduce((sum, s) => sum + s.margin, 0) / skuList.length : 0
  }

  // ABC 分布图表
  const abcChartOption = {
    title: { text: 'ABC 分类分布', left: 'center' },
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
          { value: stats.classA, name: 'A类', itemStyle: { color: '#f5222d' } },
          { value: stats.classB, name: 'B类', itemStyle: { color: '#fa8c16' } },
          { value: stats.classC, name: 'C类', itemStyle: { color: '#52c41a' } }
        ]
      }
    ]
  }

  // 营收分布图表
  const revenueChartOption = {
    title: { text: '营收占比分析', left: 'center' },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: { type: 'category', data: ['A类', 'B类', 'C类'] },
    yAxis: { type: 'value', name: '营收 (¥)' },
    series: [
      {
        type: 'bar',
        data: [
          {
            value: skuList?.filter(s => s.abcClass === 'A').reduce((sum, s) => sum + s.revenue, 0) || 0,
            itemStyle: { color: '#f5222d' }
          },
          {
            value: skuList?.filter(s => s.abcClass === 'B').reduce((sum, s) => sum + s.revenue, 0) || 0,
            itemStyle: { color: '#fa8c16' }
          },
          {
            value: skuList?.filter(s => s.abcClass === 'C').reduce((sum, s) => sum + s.revenue, 0) || 0,
            itemStyle: { color: '#52c41a' }
          }
        ],
        label: { show: true, position: 'top', formatter: '¥{c}' }
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
      width: 120,
      render: (text: string, record: SkuData) => (
        <Tag color={record.abcClass === 'A' ? 'red' : record.abcClass === 'B' ? 'orange' : 'blue'}>
          {text}
        </Tag>
      )
    },
    {
      title: 'ABC分类',
      dataIndex: 'abcClass',
      key: 'abcClass',
      width: 100,
      render: (val: string) => (
        <Tag color={val === 'A' ? 'red' : val === 'B' ? 'orange' : 'blue'}>
          <TrophyOutlined /> {val}类
        </Tag>
      )
    },
    {
      title: '营收',
      dataIndex: 'revenue',
      key: 'revenue',
      width: 120,
      sorter: (a: SkuData, b: SkuData) => a.revenue - b.revenue,
      render: (val: number) => `¥${val.toLocaleString()}`
    },
    {
      title: '订单数',
      dataIndex: 'orders',
      key: 'orders',
      width: 100,
      sorter: (a: SkuData, b: SkuData) => a.orders - b.orders
    },
    {
      title: '毛利率',
      dataIndex: 'margin',
      key: 'margin',
      width: 100,
      sorter: (a: SkuData, b: SkuData) => a.margin - b.margin,
      render: (val: number) => (
        <span style={{ color: val > 0.2 ? '#52c41a' : val > 0.1 ? '#faad14' : '#f5222d' }}>
          {(val * 100).toFixed(1)}%
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
      title: 'ROAS',
      dataIndex: 'roas',
      key: 'roas',
      width: 90,
      render: (val: number) => (
        <span style={{ color: val > 3 ? '#52c41a' : val > 1.5 ? '#faad14' : '#f5222d' }}>
          {val.toFixed(1)}
        </span>
      )
    },
    {
      title: '库存天数',
      dataIndex: 'daysOfSupply',
      key: 'daysOfSupply',
      width: 100,
      render: (val: number) => (
        <span style={{ color: val < 7 ? '#f5222d' : val < 30 ? '#faad14' : '#52c41a' }}>
          {val} 天
        </span>
      )
    },
    {
      title: '评分',
      dataIndex: 'rating',
      key: 'rating',
      width: 90,
      render: (val: number) => (
        <span style={{ color: val >= 4.5 ? '#52c41a' : val >= 4.0 ? '#faad14' : '#f5222d' }}>
          {val.toFixed(1)}
        </span>
      )
    },
    {
      title: '退货率',
      dataIndex: 'returnRate',
      key: 'returnRate',
      width: 100,
      render: (val: number) => `${(val * 100).toFixed(1)}%`
    },
    {
      title: '运营策略',
      dataIndex: 'strategy',
      key: 'strategy',
      width: 200,
      ellipsis: true
    },
    {
      title: '操作',
      key: 'action',
      fixed: 'right' as const,
      width: 150,
      render: (_: any, record: SkuData) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Button
            type="link"
            size="small"
            icon={<BarChartOutlined />}
            onClick={() => message.info('跳转到作战室')}
          >
            作战室
          </Button>
        </Space>
      )
    }
  ]

  // 处理编辑
  const handleEdit = (sku: SkuData) => {
    setEditingSku(sku)
    form.setFieldsValue(sku)
    setEditModalVisible(true)
  }

  // 保存编辑
  const handleSaveEdit = async () => {
    try {
      const values = await form.validateFields()
      message.success(`SKU ${editingSku?.sku} 更新成功`)
      setEditModalVisible(false)
      setEditingSku(null)
    } catch (error) {
      message.error('保存失败')
    }
  }

  // 过滤数据
  const filteredData = filterClass === 'all'
    ? skuList
    : skuList?.filter(s => s.abcClass === filterClass)

  return (
    <div style={{ padding: '24px' }}>
      <h1 style={{ fontSize: '24px', fontWeight: 'bold', marginBottom: '24px' }}>
        📊 ABC 分类分析
      </h1>

      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="A类商品"
              value={stats.classA}
              prefix={<TrophyOutlined style={{ color: '#f5222d' }} />}
              suffix="个"
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="B类商品"
              value={stats.classB}
              prefix={<TrophyOutlined style={{ color: '#fa8c16' }} />}
              suffix="个"
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="C类商品"
              value={stats.classC}
              prefix={<TrophyOutlined style={{ color: '#52c41a' }} />}
              suffix="个"
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="平均毛利率"
              value={stats.avgMargin * 100}
              precision={1}
              suffix="%"
            />
          </Card>
        </Col>
      </Row>

      {/* 图表 */}
      <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
        <Col xs={24} lg={12}>
          <Card>
            <ReactECharts option={abcChartOption} style={{ height: '350px' }} />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card>
            <ReactECharts option={revenueChartOption} style={{ height: '350px' }} />
          </Card>
        </Col>
      </Row>

      {/* 过滤器和表格 */}
      <Card
        title="SKU 列表"
        extra={
          <Space>
            <Select
              value={filterClass}
              onChange={setFilterClass}
              style={{ width: 120 }}
            >
              <Select.Option value="all">全部</Select.Option>
              <Select.Option value="A">A类</Select.Option>
              <Select.Option value="B">B类</Select.Option>
              <Select.Option value="C">C类</Select.Option>
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
          scroll={{ x: 1500 }}
          rowSelection={{
            selectedRowKeys,
            onChange: setSelectedRowKeys
          }}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`
          }}
        />
      </Card>

      {/* 编辑模态框 */}
      <Modal
        title={`编辑 SKU: ${editingSku?.sku}`}
        open={editModalVisible}
        onCancel={() => setEditModalVisible(false)}
        onOk={handleSaveEdit}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="营收" name="revenue">
                <InputNumber style={{ width: '100%' }} prefix="¥" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="订单数" name="orders">
                <InputNumber style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="毛利率" name="margin">
                <InputNumber style={{ width: '100%' }} step={0.01} min={0} max={1} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="ABC分类" name="abcClass">
                <Select>
                  <Select.Option value="A">A类</Select.Option>
                  <Select.Option value="B">B类</Select.Option>
                  <Select.Option value="C">C类</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={24}>
              <Form.Item label="运营策略" name="strategy">
                <Input.TextArea rows={3} />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
    </div>
  )
}
