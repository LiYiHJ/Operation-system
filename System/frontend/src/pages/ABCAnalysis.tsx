import { useMemo, useState } from 'react'
import { Table, Tag, Card, Row, Col, Statistic, Button, Select, Space, List, message, Empty, Tooltip, Tabs } from 'antd'
import { TrophyOutlined, SendOutlined } from '@ant-design/icons'
import LazyEChart from '../components/charts/LazyEChart'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { thematicApi } from '../services/api'
import { formatCurrency, formatPercent, formatInteger, displayOrDash } from '../utils/format'

import { OpsConclusion, OpsPageHeader } from '../components/ops/ProductSection'

const abcColorMap: Record<string, string> = { A: '#f5222d', B: '#faad14', C: '#52c41a' }

export default function ABCAnalysis() {
  const [filterClass, setFilterClass] = useState<string>('all')
  const navigate = useNavigate()
  const [flowStatus, setFlowStatus] = useState<Record<string, string>>({})

  const { data, isLoading } = useQuery({ queryKey: ['abc-analysis'], queryFn: () => thematicApi.getABC({ shopId: 1, days: 7 }) })
  const rows = useMemo(() => filterClass === 'all' ? (data?.rows || []) : (data?.rows || []).filter((x: any) => x.abcClass === filterClass), [data, filterClass])

  const pushMutation = useMutation({
    mutationFn: (row: any) => thematicApi.pushActionToStrategy({ sourcePage: 'abc', sku: row.sku, issueSummary: `ABC-${row.abcClass} ${row.issue}`, recommendedAction: row.recommendation, strategyType: 'pricing', priority: row.priority || 'P1', operator: 'abc_ui' }),
    onSuccess: (_: any, row: any) => { setFlowStatus((prev) => ({ ...prev, [row.sku]: '已推入策略' })); message.success('ABC建议已推送策略清单') },
  })

  const pie = { series: [{ type: 'pie', radius: ['40%', '70%'], color: [abcColorMap.A, abcColorMap.B, abcColorMap.C], data: [{ name: 'A', value: data?.summary?.A || 0 }, { name: 'B', value: data?.summary?.B || 0 }, { name: 'C', value: data?.summary?.C || 0 }] }] }
  const revenueBar = { xAxis: { type: 'category', data: ['A', 'B', 'C'] }, yAxis: { type: 'value' }, series: [{ type: 'bar', data: ['A', 'B', 'C'].map(k => ({ value: (data?.rows || []).filter((x: any) => x.abcClass === k).reduce((s: number, x: any) => s + x.revenue, 0), itemStyle: { color: abcColorMap[k] || abcColorMap.C } })) }] }

  const columns: any[] = [
    { title: 'SKU', dataIndex: 'sku', width: 140, render: (v: string, r: any) => <Tag color={r.abcClass === 'A' ? 'red' : r.abcClass === 'B' ? 'gold' : 'green'}>{displayOrDash(v)}</Tag> },
    { title: 'ABC', dataIndex: 'abcClass', width: 80 },
    { title: '营收', dataIndex: 'revenue', width: 120, render: (v: number) => formatCurrency(v) },
    { title: '订单', dataIndex: 'orders', width: 90, render: (v: number) => formatInteger(v) },
    { title: '毛利率', dataIndex: 'margin', width: 100, render: (v: number) => formatPercent(v, 1, true) },
    { title: '问题识别', dataIndex: 'issue', width: 220, ellipsis: true, render: (v: string) => <Tooltip title={displayOrDash(v)}>{displayOrDash(v)}</Tooltip> },
    { title: '推荐动作', dataIndex: 'recommendation', width: 280, ellipsis: true, render: (v: string) => <Tooltip title={displayOrDash(v)}>{displayOrDash(v)}</Tooltip> },
    { title: '去向', key: 'flowStatus', render: (_: any, row: any) => <Tag color={flowStatus[row.sku] ? 'processing' : 'default'}>{flowStatus[row.sku] || '未推送'}</Tag> },
    { title: '操作', render: (_: any, row: any) => <Button icon={<SendOutlined />} onClick={() => pushMutation.mutate(row)}>推策略</Button> },
  ]

  return <div style={{ padding: 24 }}>
    <OpsPageHeader title="📊 ABC可执行分析" subtitle="先看核心分类结论，再处理问题与动作推送。" />
    <OpsConclusion title="本页结论" desc={`A类 ${formatInteger(data?.summary?.A || 0)}，B类 ${formatInteger(data?.summary?.B || 0)}，建议优先处理高营收低毛利异常。`} level="info" />
    <div style={{ height: 16 }} />
    <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
      <Col xs={24} lg={6}><Card><Statistic title="A类" value={data?.summary?.A || 0} formatter={(v) => formatInteger(v)} prefix={<TrophyOutlined style={{ color: abcColorMap.A }} />} /></Card></Col>
      <Col xs={24} lg={6}><Card><Statistic title="B类" value={data?.summary?.B || 0} formatter={(v) => formatInteger(v)} prefix={<TrophyOutlined style={{ color: abcColorMap.B }} />} /></Card></Col>
      <Col xs={24} lg={6}><Card><Statistic title="C类" value={data?.summary?.C || 0} formatter={(v) => formatInteger(v)} prefix={<TrophyOutlined style={{ color: abcColorMap.C }} />} /></Card></Col>
      <Col xs={24} lg={6}><Card><Statistic title="平均毛利率" value={data?.summary?.avgMargin || 0} formatter={(v) => formatPercent(v, 1, true)} /></Card></Col>
    </Row>
    <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
      <Col xs={24} lg={12}><Card title="ABC分布"><LazyEChart option={pie} style={{ height: 320 }} /></Card></Col>
      <Col xs={24} lg={12}><Card title="营收分布"><LazyEChart option={revenueBar} style={{ height: 320 }} /></Card></Col>
    </Row>
    <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
      <Col xs={24} lg={10}><Card title="问题识别">{data?.issues?.length ? <List size="small" dataSource={data?.issues || []} renderItem={(x: any) => <List.Item>{displayOrDash(x.sku)} / {displayOrDash(x.issue)}</List.Item>} /> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无问题" />}</Card></Col>
      <Col xs={24} lg={14}><Card title="推荐动作">{data?.recommendedActions?.length ? <List size="small" dataSource={data?.recommendedActions || []} renderItem={(x: any) => <List.Item>{displayOrDash(x.sku)} / {displayOrDash(x.recommendation)}</List.Item>} /> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无建议" />}</Card></Col>
    </Row>
    <Card title="SKU细分分析" extra={<Space><Select value={filterClass} onChange={setFilterClass} options={[{ value: 'all', label: '全部' }, { value: 'A', label: 'A类' }, { value: 'B', label: 'B类' }, { value: 'C', label: 'C类' }]} /><Button type="primary" onClick={() => navigate('/decision')}>去决策</Button></Space>}>
      <Table rowKey="sku" dataSource={rows} columns={columns} loading={isLoading} locale={{ emptyText: '暂无数据' }} pagination={{ pageSize: 8 }} size="small" scroll={{ x: 1200, y: 360 }} />
    </Card>
  </div>
}
