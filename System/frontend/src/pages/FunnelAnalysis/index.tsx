import { Row, Col, Card, Tag, Alert } from 'antd'
import LazyEChart from '../../components/charts/LazyEChart'

export default function FunnelAnalysis() {
  const funnelData = {
    impressions: 229650,
    tocart: 1000,
    orders: 239,
    rates: {
      tocartRate: 0.0044, // 0.44%
      cartToOrderRate: 0.239, // 23.9%
      overallRate: 0.0010, // 0.10%
    },
    benchmarks: {
      tocartRate: { min: 0.08, max: 0.15 }, // 8-15%
      cartToOrderRate: { min: 0.30, max: 0.50 }, // 30-50%
      overallRate: { min: 0.03, max: 0.08 }, // 3-8%
    },
    bottleneck: '浏览→加购',
  }

  // 转化漏斗图
  const funnelChartOption = {
    title: { text: '转化漏斗分析' },
    tooltip: { trigger: 'item', formatter: '{b}: {c}' },
    series: [
      {
        name: '转化漏斗',
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
          formatter: '{b}: {c}',
        },
        labelLine: {
          length: 10,
          lineStyle: { width: 1, type: 'solid' },
        },
        itemStyle: { borderColor: '#fff', borderWidth: 1 },
        emphasis: { label: { fontSize: 20 } },
        data: [
          { value: 100, name: '浏览量', itemStyle: { color: '#1890ff' } },
          { value: (funnelData.tocart / funnelData.impressions) * 100, name: '加购数', itemStyle: { color: '#52c41a' } },
          { value: (funnelData.orders / funnelData.impressions) * 100, name: '订单数', itemStyle: { color: '#faad14' } },
        ],
      },
    ],
  }

  // 转化率趋势
  const rateTrendOption = {
    title: { text: '转化率趋势（7天）' },
    tooltip: { trigger: 'axis' },
    legend: { data: ['加购率', '购物车转化率', '整体转化率'] },
    xAxis: { type: 'category', data: ['03-02', '03-03', '03-04', '03-05', '03-06', '03-07', '03-08'] },
    yAxis: { type: 'value', axisLabel: { formatter: '{value}%' } },
    series: [
      {
        name: '加购率',
        type: 'line',
        data: [0.45, 0.42, 0.48, 0.43, 0.44, 0.46, 0.44],
      },
      {
        name: '购物车转化率',
        type: 'line',
        data: [25.2, 24.8, 26.1, 23.9, 24.5, 25.0, 23.9],
      },
      {
        name: '整体转化率',
        type: 'line',
        data: [0.11, 0.10, 0.12, 0.10, 0.11, 0.11, 0.10],
      },
    ],
  }

  return (
    <div>
      {/* 瓶颈告警 */}
      <Alert
        message="瓶颈识别"
        description={`主要瓶颈在"${funnelData.bottleneck}"环节，加购率仅 ${(funnelData.rates.tocartRate * 100).toFixed(2)}%，远低于基准 8-15%`}
        type="warning"
        showIcon
        style={{ marginBottom: 16 }}
      />

      {/* 转化漏斗图 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={12}>
          <Card>
            <LazyEChart option={funnelChartOption} style={{ height: 400 }} />
          </Card>
        </Col>
        <Col span={12}>
          <Card>
            <LazyEChart option={rateTrendOption} style={{ height: 400 }} />
          </Card>
        </Col>
      </Row>

      {/* 漏斗详情 */}
      <Card title="📊 转化漏斗详情">
        <Row gutter={16}>
          <Col span={8}>
            <div style={{ textAlign: 'center' }}>
              <h3>浏览量</h3>
              <p style={{ fontSize: 24, fontWeight: 'bold' }}>{funnelData.impressions.toLocaleString()}</p>
            </div>
          </Col>
          <Col span={8}>
            <div style={{ textAlign: 'center' }}>
              <h3>加购数</h3>
              <p style={{ fontSize: 24, fontWeight: 'bold' }}>{funnelData.tocart.toLocaleString()}</p>
              <Tag color={funnelData.rates.tocartRate < funnelData.benchmarks.tocartRate.min ? 'red' : 'green'}>
                加购率: {(funnelData.rates.tocartRate * 100).toFixed(2)}%
              </Tag>
              <br />
              <small>基准: {(funnelData.benchmarks.tocartRate.min * 100).toFixed(0)}% - {(funnelData.benchmarks.tocartRate.max * 100).toFixed(0)}%</small>
            </div>
          </Col>
          <Col span={8}>
            <div style={{ textAlign: 'center' }}>
              <h3>订单数</h3>
              <p style={{ fontSize: 24, fontWeight: 'bold' }}>{funnelData.orders.toLocaleString()}</p>
              <Tag color={funnelData.rates.cartToOrderRate < funnelData.benchmarks.cartToOrderRate.min ? 'red' : 'green'}>
                购物车转化率: {(funnelData.rates.cartToOrderRate * 100).toFixed(1)}%
              </Tag>
              <br />
              <small>基准: {(funnelData.benchmarks.cartToOrderRate.min * 100).toFixed(0)}% - {(funnelData.benchmarks.cartToOrderRate.max * 100).toFixed(0)}%</small>
            </div>
          </Col>
        </Row>

        <div style={{ marginTop: 24, padding: 16, backgroundColor: '#f0f2f5', borderRadius: 8 }}>
          <h4>🔍 瓶颈诊断: {funnelData.bottleneck}</h4>
          <p><strong>处方:</strong></p>
          <ul>
            <li>✅ 优化主图（增加场景图、细节图）</li>
            <li>✅ 优化标题关键词</li>
            <li>✅ 检查价格指数（若 RED → 先降价）</li>
            <li>✅ 增加评价数（提升信任度）</li>
          </ul>
        </div>
      </Card>
    </div>
  )
}
