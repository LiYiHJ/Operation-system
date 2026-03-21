import { useMemo, useState } from 'react'
import { Card, Row, Col, Table, Tag, Button, Select, Space, Statistic, List, message, Empty } from 'antd'
import { DollarOutlined, EyeOutlined, SendOutlined } from '@ant-design/icons'
import LazyEChart from '../components/charts/LazyEChart'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { thematicApi } from '../services/api'
import { formatCurrency, formatPercent, formatRate, formatInteger, displayOrDash } from '../utils/format'
import { performanceLabels } from '../utils/labels'
import { OpsConclusion, OpsPageHeader } from '../components/ops/ProductSection'

export default function AdsManagement() {
  const [performanceFilter, setPerformanceFilter] = useState('all')
  const navigate = useNavigate()
  const [flowStatus, setFlowStatus] = useState<Record<string, string>>({})
  const { data, isLoading } = useQuery({ queryKey: ['ads-analysis'], queryFn: () => thematicApi.getAds({ shopId: 1, days: 7 }) })

  const rows = useMemo(() => performanceFilter === 'all' ? (data?.rows || []) : (data?.rows || []).filter((x: any) => x.performance === performanceFilter), [data, performanceFilter])
  const pushMutation = useMutation({
    mutationFn: (row: any) => thematicApi.pushActionToStrategy({
      sourcePage: 'ads', sku: row.sku, issueSummary: `广告表现 ${performanceLabels[row.performance] || row.performance} / ROAS ${formatRate(row.roas, 2)}`, recommendedAction: row.recommendation, strategyType: 'ads', priority: row.performance === 'critical' ? 'P0' : 'P1', operator: 'ads_ui',
    }),
    onSuccess: (_: any, row: any) => { setFlowStatus((prev) => ({ ...prev, [row.sku]: '已推入策略' })); message.success('广告优化动作已推送到策略清单') },
  })

  const roasChart = {
    xAxis: { type: 'category', data: (rows || []).map((x: any) => x.sku) },
    yAxis: { type: 'value' },
    series: [{ type: 'bar', data: (rows || []).map((x: any) => Number(x.roas || 0).toFixed(2)) }],
  }

  const columns: any[] = [
    { title: 'SKU', dataIndex: 'sku', render: (v: string) => displayOrDash(v) },
    { title: '活动', dataIndex: 'campaignName', render: (v: string) => displayOrDash(v) },
    { title: '状态', dataIndex: 'campaignStatus', render: (v: string) => <Tag color={v === 'active' ? 'green' : 'default'}>{v === 'active' ? '投放中' : '已暂停'}</Tag> },
    { title: '花费', dataIndex: 'adSpend', render: (v: number) => formatCurrency(v) },
    { title: '收入', dataIndex: 'adRevenue', render: (v: number) => formatCurrency(v) },
    { title: 'ROAS', dataIndex: 'roas', render: (v: number) => formatRate(v, 2) },
    { title: 'CTR', dataIndex: 'ctr', render: (v: number) => formatPercent(v, 2, true) },
    { title: 'ACOS', dataIndex: 'acos', render: (v: number) => formatPercent(v, 1, true) },
    { title: '表现', dataIndex: 'performance', render: (v: string) => <Tag color={v === 'excellent' ? 'green' : v === 'good' ? 'blue' : v === 'poor' ? 'orange' : 'red'}>{performanceLabels[v] || v}</Tag> },
    { title: '建议', dataIndex: 'recommendation', ellipsis: true, render: (v: string) => displayOrDash(v) },
    { title: '去向', key: 'flowStatus', render: (_: any, row: any) => <Tag color={flowStatus[row.sku] ? 'processing' : 'default'}>{flowStatus[row.sku] || '未推送'}</Tag> },
    { title: '操作', render: (_: any, row: any) => <Button icon={<SendOutlined />} onClick={() => pushMutation.mutate(row)}>推策略</Button> },
  ]

  return <div style={{ padding: 24 }}>
    <OpsPageHeader title="🎯 广告运营专题" subtitle="先看低效投放，再执行预算与出价优化动作。" />
    <OpsConclusion title="本页结论" desc={`当前需优化活动 ${formatInteger(data?.issues?.length || 0)} 条，建议先处理严重低效投放。`} level="warning" />
    <div style={{ height: 16 }} />
    <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
      <Col xs={24} lg={6}><Card><Statistic title="总花费" value={data?.summary?.totalSpend || 0} formatter={(v) => formatCurrency(v)} prefix={<DollarOutlined />} /></Card></Col>
      <Col xs={24} lg={6}><Card><Statistic title="总收入" value={data?.summary?.totalRevenue || 0} formatter={(v) => formatCurrency(v)} prefix={<DollarOutlined />} /></Card></Col>
      <Col xs={24} lg={6}><Card><Statistic title="平均ROAS" value={data?.summary?.avgRoas || 0} formatter={(v) => formatRate(v, 2)} /></Card></Col>
      <Col xs={24} lg={6}><Card><Statistic title="活跃活动" value={data?.summary?.activeCampaigns || 0} formatter={(v) => formatInteger(v)} prefix={<EyeOutlined />} /></Card></Col>
    </Row>
    <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
      <Col xs={24} lg={14}><Card title="ROAS 分布"><LazyEChart option={roasChart} style={{ height: 320 }} /></Card></Col>
      <Col xs={24} lg={10}><Card title="问题识别 / 推荐动作">{data?.issues?.length ? <List size="small" dataSource={data?.issues || []} renderItem={(x: any) => <List.Item>{displayOrDash(x.sku)} / {performanceLabels[x.performance] || x.performance} / {displayOrDash(x.recommendation)}</List.Item>} /> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无问题" />}</Card></Col>
    </Row>
    <Card title="广告活动详情" extra={<Space><Select value={performanceFilter} onChange={setPerformanceFilter} options={[{ value: 'all', label: '全部' }, { value: 'excellent', label: '优秀' }, { value: 'good', label: '良好' }, { value: 'poor', label: '较差' }, { value: 'critical', label: '严重' }]} /><Button type="primary" onClick={() => navigate('/decision')}>去决策</Button></Space>}>
      <Table rowKey="sku" dataSource={rows} columns={columns} loading={isLoading} locale={{ emptyText: '暂无数据' }} pagination={{ pageSize: 8 }} size="small" scroll={{ x: 1200, y: 360 }} />
    </Card>
  </div>
}
