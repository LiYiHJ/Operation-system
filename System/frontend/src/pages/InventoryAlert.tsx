import { useMemo, useState } from 'react'
import { Card, Row, Col, Table, Tag, Button, Select, Space, Statistic, Alert, List, message, Empty } from 'antd'
import { WarningOutlined, StockOutlined, SendOutlined } from '@ant-design/icons'
import LazyEChart from '../components/charts/LazyEChart'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { thematicApi } from '../services/api'
import { formatInteger, formatRate, formatDays, displayOrDash } from '../utils/format'
import { alertLevelLabels } from '../utils/labels'
import { OpsConclusion, OpsPageHeader } from '../components/ops/ProductSection'

export default function InventoryAlert() {
  const [filterAlert, setFilterAlert] = useState<string>('all')
  const navigate = useNavigate()
  const [flowStatus, setFlowStatus] = useState<Record<string, string>>({})

  const { data, isLoading } = useQuery({ queryKey: ['inventory-analysis'], queryFn: () => thematicApi.getInventory({ shopId: 1, days: 7 }) })
  const rows = useMemo(() => filterAlert === 'all' ? (data?.rows || []) : (data?.rows || []).filter((i: any) => i.alertLevel === filterAlert), [data, filterAlert])

  const pushMutation = useMutation({
    mutationFn: (row: any) => thematicApi.pushActionToStrategy({
      sourcePage: 'inventory', sku: row.sku, issueSummary: `库存预警 ${alertLevelLabels[row.alertLevel] || row.alertLevel} / ${formatDays(row.daysOfSupply)}`, recommendedAction: row.recommendation, strategyType: 'inventory', priority: row.alertLevel === 'critical' ? 'P0' : 'P1', operator: 'inventory_ui',
    }),
    onSuccess: (_: any, row: any) => { setFlowStatus((prev) => ({ ...prev, [row.sku]: '已推入策略' })); message.success('已推送到策略清单') },
  })

  const chart = { xAxis: { type: 'category', data: (data?.rows || []).map((x: any) => x.sku) }, yAxis: { type: 'value' }, series: [{ type: 'bar', data: (data?.rows || []).map((x: any) => Number(x.daysOfSupply || 0).toFixed(0)) }] }
  const columns: any[] = [
    { title: 'SKU', dataIndex: 'sku', render: (v: string) => displayOrDash(v) },
    { title: '库存', dataIndex: 'stockTotal', render: (v: number) => formatInteger(v) },
    { title: '库存天数', dataIndex: 'daysOfSupply', render: (v: number) => formatDays(v) },
    { title: '安全库存', dataIndex: 'safetyStock', render: (v: number) => formatInteger(v) },
    { title: '补货点', dataIndex: 'reorderPoint', render: (v: number) => formatInteger(v) },
    { title: '预警', dataIndex: 'alertLevel', render: (v: string) => <Tag color={v === 'critical' ? 'red' : v === 'warning' ? 'orange' : 'green'}>{alertLevelLabels[v] || v}</Tag> },
    { title: '建议', dataIndex: 'recommendation', ellipsis: true, render: (v: string) => displayOrDash(v) },
    { title: '去向', key: 'flowStatus', render: (_: any, row: any) => <Tag color={flowStatus[row.sku] ? 'processing' : 'default'}>{flowStatus[row.sku] || '未推送'}</Tag> },
    { title: '操作', render: (_: any, row: any) => <Button icon={<SendOutlined />} onClick={() => pushMutation.mutate(row)}>推策略</Button> },
  ]

  return <div style={{ padding: 24 }}>
    <OpsPageHeader title="📦 库存预警专题" subtitle="先看断货与积压风险，再下发补货/降库存动作。" />
    <OpsConclusion title="本页结论" desc={`当前库存风险 ${formatInteger(data?.summary?.riskSku || 0)} 个，优先处理高风险SKU。`} level="warning" />
    <div style={{ height: 16 }} />
    {(data?.summary?.critical || 0) > 0 && <Alert style={{ marginBottom: 16 }} type="error" showIcon icon={<WarningOutlined />} message={`紧急预警 ${formatInteger(data.summary.critical)} 个`} />}
    <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
      <Col xs={24} lg={6}><Card><Statistic title="紧急" value={data?.summary?.critical || 0} formatter={(v) => formatInteger(v)} valueStyle={{ color: '#f5222d' }} /></Card></Col>
      <Col xs={24} lg={6}><Card><Statistic title="警告" value={data?.summary?.warning || 0} formatter={(v) => formatInteger(v)} /></Card></Col>
      <Col xs={24} lg={6}><Card><Statistic title="总库存" value={data?.summary?.totalStock || 0} formatter={(v) => formatInteger(v)} prefix={<StockOutlined />} /></Card></Col>
      <Col xs={24} lg={6}><Card><Statistic title="平均库存天数" value={data?.summary?.avgDaysOfSupply || 0} formatter={(v) => formatRate(v, 0)} suffix="天" /></Card></Col>
    </Row>
    <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
      <Col xs={24} lg={14}><Card title="库存天数分布"><LazyEChart option={chart} style={{ height: 320 }} /></Card></Col>
      <Col xs={24} lg={10}><Card title="问题识别 / 推荐动作">{data?.issues?.length ? <List size="small" dataSource={data?.issues || []} renderItem={(x: any) => <List.Item>{displayOrDash(x.sku)} / {alertLevelLabels[x.alertLevel] || x.alertLevel} / {displayOrDash(x.recommendation)}</List.Item>} /> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无问题" />}</Card></Col>
    </Row>
    <Card title="库存详情" extra={<Space><Select value={filterAlert} onChange={setFilterAlert} options={[{ value: 'all', label: '全部' }, { value: 'critical', label: '紧急' }, { value: 'warning', label: '警告' }, { value: 'normal', label: '正常' }]} /><Button type="primary" onClick={() => navigate('/decision')}>去决策</Button></Space>}>
      <Table rowKey="sku" dataSource={rows} columns={columns} loading={isLoading} locale={{ emptyText: '暂无数据' }} pagination={{ pageSize: 8 }} size="small" scroll={{ x: 1200, y: 360 }} />
    </Card>
  </div>
}
