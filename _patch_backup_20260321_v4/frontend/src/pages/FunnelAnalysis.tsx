import { useMemo, useState } from 'react'
import { Card, Row, Col, Table, Tag, Button, Select, Space, Statistic, List, message, Empty } from 'antd'
import { UserOutlined, ShoppingCartOutlined, DollarOutlined, SendOutlined } from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { thematicApi } from '../services/api'
import { formatPercent, formatInteger, displayOrDash } from '../utils/format'
import { OpsConclusion, OpsPageHeader } from '../components/ops/ProductSection'

export default function FunnelAnalysis() {
  const [filter, setFilter] = useState('all')
  const navigate = useNavigate()
  const [flowStatus, setFlowStatus] = useState<Record<string, string>>({})
  const { data, isLoading } = useQuery({ queryKey: ['funnel-analysis'], queryFn: () => thematicApi.getFunnel({ shopId: 1, days: 7 }) })
  const rows = useMemo(() => filter === 'all' ? (data?.rows || []) : (data?.rows || []).filter((x: any) => x.bottleneck === filter), [data, filter])

  const pushMutation = useMutation({
    mutationFn: (row: any) => thematicApi.pushActionToStrategy({
      sourcePage: 'funnel', sku: row.sku, issueSummary: `漏斗瓶颈：${row.bottleneck}`, recommendedAction: row.recommendation, strategyType: 'conversion', priority: row.priority, operator: 'funnel_ui',
    }),
    onSuccess: (_: any, row: any) => { setFlowStatus((prev) => ({ ...prev, [row.sku]: '已推入策略' })); message.success('漏斗优化动作已推送到策略清单') },
  })

  const funnelChart = {
    tooltip: { trigger: 'item' },
    series: [{ type: 'funnel', data: [
      { name: '展示', value: (data?.rows || []).reduce((s: number, x: any) => s + x.impressions, 0) },
      { name: '访问', value: (data?.rows || []).reduce((s: number, x: any) => s + x.cardVisits, 0) },
      { name: '加购', value: (data?.rows || []).reduce((s: number, x: any) => s + x.addToCart, 0) },
      { name: '下单', value: (data?.rows || []).reduce((s: number, x: any) => s + x.orders, 0) },
    ] }],
  }

  const columns: any[] = [
    { title: 'SKU', dataIndex: 'sku', render: (v: string) => displayOrDash(v) },
    { title: '展示', dataIndex: 'impressions', render: (v: number) => formatInteger(v) },
    { title: '访问', dataIndex: 'cardVisits', render: (v: number) => formatInteger(v) },
    { title: '加购', dataIndex: 'addToCart', render: (v: number) => formatInteger(v) },
    { title: '订单', dataIndex: 'orders', render: (v: number) => formatInteger(v) },
    { title: 'CTR', dataIndex: 'ctr', render: (v: number) => formatPercent(v, 2, true) },
    { title: '加购率', dataIndex: 'addRate', render: (v: number) => formatPercent(v, 1, true) },
    { title: '下单率', dataIndex: 'orderRate', render: (v: number) => formatPercent(v, 1, true) },
    { title: '瓶颈', dataIndex: 'bottleneck', render: (v: string) => <Tag color={v === '无' ? 'green' : 'orange'}>{displayOrDash(v)}</Tag> },
    { title: '建议', dataIndex: 'recommendation', ellipsis: true, render: (v: string) => displayOrDash(v) },
    { title: '去向', key: 'flowStatus', render: (_: any, row: any) => <Tag color={flowStatus[row.sku] ? 'processing' : 'default'}>{flowStatus[row.sku] || '未推送'}</Tag> },
    { title: '操作', render: (_: any, row: any) => <Button icon={<SendOutlined />} onClick={() => pushMutation.mutate(row)}>推策略</Button> },
  ]

  return <div style={{ padding: 24 }}>
    <OpsPageHeader title="📊 转化漏斗专题" subtitle="先识别主要流失环节，再推动转化修复动作。" />
    <OpsConclusion title="本页结论" desc={`当前主要瓶颈集中在加购/下单阶段，建议优先修复高流失环节。`} level="warning" />
    <div style={{ height: 16 }} />
    <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
      <Col xs={24} lg={6}><Card><Statistic title="平均CTR" value={data?.summary?.avgCtr || 0} formatter={(v) => formatPercent(v, 2, true)} prefix={<UserOutlined />} /></Card></Col>
      <Col xs={24} lg={6}><Card><Statistic title="平均加购率" value={data?.summary?.avgAddRate || 0} formatter={(v) => formatPercent(v, 1, true)} prefix={<ShoppingCartOutlined />} /></Card></Col>
      <Col xs={24} lg={6}><Card><Statistic title="平均下单率" value={data?.summary?.avgOrderRate || 0} formatter={(v) => formatPercent(v, 1, true)} prefix={<DollarOutlined />} /></Card></Col>
      <Col xs={24} lg={6}><Card><Statistic title="总订单" value={data?.summary?.totalOrders || 0} formatter={(v) => formatInteger(v)} /></Card></Col>
    </Row>
    <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
      <Col xs={24} lg={14}><Card title="漏斗总览"><ReactECharts option={funnelChart} style={{ height: 340 }} /></Card></Col>
      <Col xs={24} lg={10}><Card title="问题识别 / 推荐动作">{data?.issues?.length ? <List size="small" dataSource={data?.issues || []} renderItem={(x: any) => <List.Item>{displayOrDash(x.sku)} / {displayOrDash(x.bottleneck)} / {displayOrDash(x.recommendation)}</List.Item>} /> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无问题" />}</Card></Col>
    </Row>
    <Card title="漏斗明细" extra={<Space><Select value={filter} onChange={setFilter} options={[{ value: 'all', label: '全部' }, { value: 'CTR', label: 'CTR瓶颈' }, { value: '加购率', label: '加购率瓶颈' }, { value: '下单率', label: '下单率瓶颈' }, { value: '无', label: '无瓶颈' }]} /><Button type="primary" onClick={() => navigate('/decision')}>去决策</Button></Space>}>
      <Table rowKey="sku" dataSource={rows} columns={columns} loading={isLoading} locale={{ emptyText: '暂无数据' }} pagination={{ pageSize: 8 }} size="small" scroll={{ x: 1200, y: 360 }} />
    </Card>
  </div>
}
