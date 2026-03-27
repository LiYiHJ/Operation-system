import { Row, Col, Card, Table, Tag, Progress, Alert } from 'antd'
import LazyEChart from '../../components/charts/LazyEChart'

export default function PriceCompetitiveness() {
  const priceDistribution = {
    YunElite: { green: 0.46, yellow: 0.06, red: 0.48 },
    ALORA: { green: 0.49, yellow: 0.02, red: 0.49 },
  }

  const urgentReprice = [
    { key: '1', sku: 'HAA240-10', name: '花瓶 陶瓷 20.7cm', abc: 'A', priceIndex: 1.08, colorIndex: 'RED', currentPrice: '₽1,449', suggestion: '降价 8%', priority: 'P0' },
    { key: '2', sku: 'HAA132-15', name: '拖把 15cm', abc: 'A', priceIndex: 1.12, colorIndex: 'RED', currentPrice: '₽899', suggestion: '降价 10%', priority: 'P0' },
    { key: '3', sku: 'HAA150-03', name: '洗漱套装', abc: 'A', priceIndex: 1.05, colorIndex: 'RED', currentPrice: '₽1,299', suggestion: '降价 5%', priority: 'P1' },
  ]

  // 价格区域分布堆叠柱状图
  const priceZoneOption = {
    title: { text: '价格竞争力区域分布' },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { data: ['绿色区域', '黄色区域', '红色区域'] },
    xAxis: { type: 'category', data: ['YunElite', 'ALORA'] },
    yAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%' } },
    series: [
      {
        name: '绿色区域',
        type: 'bar',
        stack: 'total',
        data: [priceDistribution.YunElite.green * 100, priceDistribution.ALORA.green * 100],
        itemStyle: { color: '#52c41a' },
      },
      {
        name: '黄色区域',
        type: 'bar',
        stack: 'total',
        data: [priceDistribution.YunElite.yellow * 100, priceDistribution.ALORA.yellow * 100],
        itemStyle: { color: '#faad14' },
      },
      {
        name: '红色区域',
        type: 'bar',
        stack: 'total',
        data: [priceDistribution.YunElite.red * 100, priceDistribution.ALORA.red * 100],
        itemStyle: { color: '#ff4d4f' },
      },
    ],
  }

  // 价格指数趋势
  const priceIndexTrendOption = {
    title: { text: '价格指数趋势（7天）' },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: ['03-02', '03-03', '03-04', '03-05', '03-06', '03-07', '03-08'] },
    yAxis: { type: 'value', min: 0.8, max: 1.2 },
    series: [
      {
        name: '平均价格指数',
        type: 'line',
        data: [1.05, 1.04, 1.06, 1.05, 1.07, 1.06, 1.08],
        markLine: {
          data: [
            { yAxis: 1.0, name: '基准线', lineStyle: { color: '#52c41a' } },
          ],
        },
      },
    ],
  }

  const urgentRepriceColumns = [
    { title: 'SKU', dataIndex: 'sku', key: 'sku' },
    { title: '产品名称', dataIndex: 'name', key: 'name' },
    { title: 'ABC', dataIndex: 'abc', key: 'abc', render: (abc: string) => <Tag color="green">{abc}类</Tag> },
    { title: '价格指数', dataIndex: 'priceIndex', key: 'priceIndex', render: (index: number) => (
      <span style={{ color: index > 1.0 ? '#ff4d4f' : '#52c41a' }}>
        {index.toFixed(2)}
      </span>
    ) },
    { title: '价格区域', dataIndex: 'colorIndex', key: 'colorIndex', render: (zone: string) => (
      <Tag color={zone === 'GREEN' ? 'green' : zone === 'YELLOW' ? 'orange' : 'red'}>{zone}</Tag>
    ) },
    { title: '当前价格', dataIndex: 'currentPrice', key: 'currentPrice' },
    { title: '建议', dataIndex: 'suggestion', key: 'suggestion', render: (sug: string) => <Tag color="red">{sug}</Tag> },
    { title: '优先级', dataIndex: 'priority', key: 'priority', render: (pri: string) => <Tag color={pri === 'P0' ? 'red' : 'orange'}>{pri}</Tag> },
  ]

  return (
    <div>
      {/* 告警 */}
      <Alert
        message="价格竞争力警告"
        description="YunElite 和 ALORA 的红色区域占比均接近 50%，需紧急调价！"
        type="error"
        showIcon
        style={{ marginBottom: 16 }}
      />

      {/* 价格区域分布 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={12}>
          <Card>
            <LazyEChart option={priceZoneOption} style={{ height: 300 }} />
          </Card>
        </Col>
        <Col span={12}>
          <Card>
            <LazyEChart option={priceIndexTrendOption} style={{ height: 300 }} />
          </Card>
        </Col>
      </Row>

      {/* 价格竞争力详情 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={12}>
          <Card title="YunElite 价格竞争力">
            <p>🟢 绿色区域（价格有利）: <Progress percent={priceDistribution.YunElite.green * 100} size="small" strokeColor="#52c41a" /></p>
            <p>🟡 黄色区域（价格正常）: <Progress percent={priceDistribution.YunElite.yellow * 100} size="small" strokeColor="#faad14" /></p>
            <p>🔴 红色区域（价格偏高）: <Progress percent={priceDistribution.YunElite.red * 100} size="small" strokeColor="#ff4d4f" /></p>
          </Card>
        </Col>
        <Col span={12}>
          <Card title="ALORA 价格竞争力">
            <p>🟢 绿色区域（价格有利）: <Progress percent={priceDistribution.ALORA.green * 100} size="small" strokeColor="#52c41a" /></p>
            <p>🟡 黄色区域（价格正常）: <Progress percent={priceDistribution.ALORA.yellow * 100} size="small" strokeColor="#faad14" /></p>
            <p>🔴 红色区域（价格偏高）: <Progress percent={priceDistribution.ALORA.red * 100} size="small" strokeColor="#ff4d4f" /></p>
          </Card>
        </Col>
      </Row>

      {/* 紧急调价清单 */}
      <Card title="🔴 紧急调价清单（A类 + RED 价格区域）">
        <Table
          dataSource={urgentReprice}
          columns={urgentRepriceColumns}
          pagination={false}
          size="small"
        />
      </Card>
    </div>
  )
}
