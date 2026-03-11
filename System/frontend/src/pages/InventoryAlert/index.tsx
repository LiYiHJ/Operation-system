import { Row, Col, Card, Table, Tag, Statistic, Alert } from 'antd'
import ReactECharts from 'echarts-for-react'

export default function InventoryAlert() {
  const inventorySummary = {
    critical: { count: 5, skus: ['HAA132-01', 'HAA240-10'] },
    warning: { count: 12, skus: ['HAA150-08'] },
    normal: { count: 800 },
    overstock: { count: 183 },
  }

  const criticalInventory = [
    { key: '1', sku: 'HAA132-01', name: '拖把 13cm', stock: 0, daily: 1.7, days: 0, level: '🔴 紧急', action: '立即补货' },
    { key: '2', sku: 'HAA240-10', name: '花瓶 陶瓷 20.7cm', stock: 5, daily: 2.3, days: 2, level: '🔴 紧急', action: '24h内补货' },
    { key: '3', sku: 'HAA150-08', name: '洗漱套装', stock: 20, daily: 3.0, days: 7, level: '🟡 警告', action: '3天内补货' },
  ]

  const overstockInventory = [
    { key: '1', sku: 'HAA066-99', name: '旧款产品A', stock: 150, daily: 0.5, days: 300, level: '⚠️ 滞销', action: '清仓 50%' },
    { key: '2', sku: 'HAA043-88', name: '旧款产品B', stock: 200, daily: 0.3, days: 667, level: '⚠️ 滞销', action: '下架评估' },
    { key: '3', sku: 'HAA061-77', name: '旧款产品C', stock: 180, daily: 0.2, days: 900, level: '⚠️ 滞销', action: '清仓 30%' },
  ]

  // 库存分布饼图
  const inventoryDistOption = {
    title: { text: '库存预警分布', left: 'center' },
    tooltip: { trigger: 'item', formatter: '{b}: {c} 个SKU' },
    legend: { orient: 'vertical', left: 'left' },
    series: [
      {
        name: '库存状态',
        type: 'pie',
        radius: '50%',
        data: [
          { value: inventorySummary.critical.count, name: '🔴 紧急', itemStyle: { color: '#ff4d4f' } },
          { value: inventorySummary.warning.count, name: '🟡 警告', itemStyle: { color: '#faad14' } },
          { value: inventorySummary.normal.count, name: '✅ 正常', itemStyle: { color: '#52c41a' } },
          { value: inventorySummary.overstock.count, name: '⚠️ 滞销', itemStyle: { color: '#8c8c8c' } },
        ],
        emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.5)' } },
      },
    ],
  }

  // 库存周转率
  const turnoverOption = {
    title: { text: '库存周转率（按品类）' },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: ['家居', '厨具', '洗护', '户外', '其他'] },
    yAxis: { type: 'value', name: '周转率' },
    series: [
      {
        name: '周转率',
        type: 'bar',
        data: [4.5, 3.8, 2.1, 1.5, 0.8],
        itemStyle: {
          color: (params: any) => {
            const colors = ['#52c41a', '#52c41a', '#faad14', '#faad14', '#ff4d4f']
            return colors[params.dataIndex]
          },
        },
      },
    ],
  }

  const criticalColumns = [
    { title: 'SKU', dataIndex: 'sku', key: 'sku' },
    { title: '产品名称', dataIndex: 'name', key: 'name' },
    { title: '库存', dataIndex: 'stock', key: 'stock', render: (stock: number) => <Tag color={stock === 0 ? 'red' : 'orange'}>{stock}</Tag> },
    { title: '日均销量', dataIndex: 'daily', key: 'daily' },
    { title: '可售天数', dataIndex: 'days', key: 'days', render: (days: number) => <Tag color={days < 7 ? 'red' : 'orange'}>{days} 天</Tag> },
    { title: '预警等级', dataIndex: 'level', key: 'level' },
    { title: '建议行动', dataIndex: 'action', key: 'action', render: (action: string) => <Tag color="red">{action}</Tag> },
  ]

  const overstockColumns = [
    { title: 'SKU', dataIndex: 'sku', key: 'sku' },
    { title: '产品名称', dataIndex: 'name', key: 'name' },
    { title: '库存', dataIndex: 'stock', key: 'stock' },
    { title: '日均销量', dataIndex: 'daily', key: 'daily' },
    { title: '可售天数', dataIndex: 'days', key: 'days', render: (days: number) => <Tag color="red">{days} 天</Tag> },
    { title: '状态', dataIndex: 'level', key: 'level' },
    { title: '建议行动', dataIndex: 'action', key: 'action', render: (action: string) => <Tag color="orange">{action}</Tag> },
  ]

  return (
    <div>
      {/* 紧急告警 */}
      <Alert
        message="库存预警"
        description={`有 ${inventorySummary.critical.count} 个 SKU 库存紧急，需立即补货！`}
        type="error"
        showIcon
        style={{ marginBottom: 16 }}
      />

      {/* 库存统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="🔴 紧急"
              value={inventorySummary.critical.count}
              suffix="个 SKU"
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="🟡 警告"
              value={inventorySummary.warning.count}
              suffix="个 SKU"
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="✅ 正常"
              value={inventorySummary.normal.count}
              suffix="个 SKU"
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="⚠️ 滞销"
              value={inventorySummary.overstock.count}
              suffix="个 SKU"
              valueStyle={{ color: '#8c8c8c' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 库存分布图 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={12}>
          <Card>
            <ReactECharts option={inventoryDistOption} style={{ height: 300 }} />
          </Card>
        </Col>
        <Col span={12}>
          <Card>
            <ReactECharts option={turnoverOption} style={{ height: 300 }} />
          </Card>
        </Col>
      </Row>

      {/* 紧急补货清单 */}
      <Card title="🔴 紧急补货清单" style={{ marginBottom: 16 }}>
        <Table
          dataSource={criticalInventory}
          columns={criticalColumns}
          pagination={false}
          size="small"
        />
      </Card>

      {/* 滞销库存清单 */}
      <Card title="⚠️ 滞销库存清单">
        <Table
          dataSource={overstockInventory}
          columns={overstockColumns}
          pagination={false}
          size="small"
        />
      </Card>
    </div>
  )
}
