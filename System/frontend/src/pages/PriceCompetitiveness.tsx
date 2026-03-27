import { useMemo, useState } from 'react'
import { Card, Row, Col, Statistic, Tabs, Tag, Table, Space, Select, Button, List, message, Drawer, Typography, Empty, Tooltip } from 'antd'
import { DollarOutlined, WarningOutlined, CheckCircleOutlined, ThunderboltOutlined, SendOutlined } from '@ant-design/icons'
import LazyEChart from '../components/charts/LazyEChart'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { thematicApi } from '../services/api'
import { formatCurrency, formatPercent, formatInteger, formatRate, displayOrDash } from '../utils/format'
import { strategyGroupLabels } from '../utils/labels'
import { OpsConclusion, OpsPageHeader, OpsRiskTag } from '../components/ops/ProductSection'

const { Text } = Typography

const competitivenessColorMap: Record<string, string> = { red: '#f5222d', yellow: '#faad14', green: '#52c41a' }

export default function PriceCompetitiveness() {
  const [view, setView] = useState<'daily' | 'campaign' | 'promo'>('daily')
  const [groupFilter, setGroupFilter] = useState('all')
  const [selectedRow, setSelectedRow] = useState<any>(null)
  const [flowStatus, setFlowStatus] = useState<Record<string, string>>({})
  const navigate = useNavigate()

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['price-cockpit', view],
    queryFn: () => thematicApi.getPriceCockpit({ shopId: 1, days: 7, view }),
  })

  const pushMutation = useMutation({
    mutationFn: (row: any) => thematicApi.pushActionToStrategy({
      shopId: 1,
      sourcePage: 'price',
      sku: row.sku,
      issueSummary: `价格分析（${view === 'daily' ? '日常' : view === 'campaign' ? '平台活动' : '自建促销'}）：${row.competitiveness} 区 / 价差 ${formatCurrency(row.priceGap)}`,
      recommendedAction: row.recommendation,
      strategyType: 'pricing',
      priority: row.competitiveness === 'red' ? 'P0' : 'P1',
      operator: 'price_ui',
    }),
    onSuccess: (resp: any, row: any) => {
      setFlowStatus((prev) => ({ ...prev, [row.sku]: '已推入策略' }))
      message.success('已推送至策略清单，请在决策队列继续确认')
    },
    onError: (e: any) => message.error(`推送失败: ${e.message}`),
  })

  const rows = useMemo(() => {
    const source = data?.batchRecommendations || []
    if (groupFilter === 'all') return source
    return source.filter((x: any) => x.group === groupFilter)
  }, [data, groupFilter])

  const zoneChart = {
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie', radius: ['35%', '70%'],
      data: [
        { name: '绿区', value: rows.filter((x: any) => x.competitiveness === 'green').length, itemStyle: { color: competitivenessColorMap.green } },
        { name: '黄区', value: rows.filter((x: any) => x.competitiveness === 'yellow').length, itemStyle: { color: competitivenessColorMap.yellow } },
        { name: '红区', value: rows.filter((x: any) => x.competitiveness === 'red').length, itemStyle: { color: competitivenessColorMap.red } },
      ],
    }],
  }

  const groupChart = {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: (data?.groupedStrategies || []).map((g: any) => strategyGroupLabels[g.key] || g.label) },
    yAxis: { type: 'value' },
    series: [{ type: 'bar', data: (data?.groupedStrategies || []).map((g: any) => g.count) }],
  }

  const columns: any[] = [
    { title: 'SKU', dataIndex: 'sku', key: 'sku', width: 120, render: (v: string) => displayOrDash(v) },
    { title: '策略分组', dataIndex: 'group', key: 'group', width: 130, render: (v: string) => <Tag>{strategyGroupLabels[v] || v}</Tag> },
    { title: '当前成交价', dataIndex: 'ourPrice', key: 'ourPrice', width: 120, render: (v: number) => <Text strong>{formatCurrency(v)}</Text> },
    { title: '参考价', dataIndex: 'marketPrice', key: 'marketPrice', width: 120, render: (v: number) => formatCurrency(v) },
    { title: '价差', dataIndex: 'priceGap', key: 'priceGap', width: 120, render: (v: number) => <Text type={v > 0 ? 'danger' : 'success'}>{formatCurrency(v)}</Text> },
    { title: '平台活动净利率', dataIndex: 'margin', key: 'margin', width: 130, render: (v: number) => formatPercent(v, 1, true) },
    { title: '自建促销净利率', dataIndex: 'promoMargin', key: 'promoMargin', width: 130, render: (v: number, r: any) => formatPercent(v ?? r.margin, 1, true) },
    { title: '订单', dataIndex: 'orders', key: 'orders', width: 80, render: (v: number) => formatInteger(v) },
    { title: '购买件数', dataIndex: 'itemsPurchased', key: 'itemsPurchased', width: 100, render: (v: number) => formatInteger(v) },
    { title: '活动天数', dataIndex: 'promoDaysCount', key: 'promoDaysCount', width: 100, render: (v: number) => formatInteger(v) },
    { title: '折扣率', dataIndex: 'discountPct', key: 'discountPct', width: 90, render: (v: number) => formatPercent(v, 1, true) },
    { title: '价格指数状态', dataIndex: 'priceIndexStatus', key: 'priceIndexStatus', width: 120, render: (v: string) => displayOrDash(v) },
    { title: 'ROAS', dataIndex: 'roas', key: 'roas', width: 90, render: (v: number) => formatRate(v, 2) },
    { title: '推荐策略', dataIndex: 'recommendation', key: 'recommendation', width: 300, ellipsis: true, render: (v: string) => <Tooltip title={displayOrDash(v)}><Text strong>{displayOrDash(v)}</Text></Tooltip> },
    { title: '风险等级', dataIndex: 'competitiveness', key: 'competitiveness', width: 90, render: (v: string) => <OpsRiskTag level={v === 'red' ? 'critical' : v === 'yellow' ? 'warning' : 'normal'} /> },
    { title: '动作去向', key: 'flowStatus', width: 120, render: (_: any, row: any) => <Tag color={flowStatus[row.sku] ? 'processing' : 'default'}>{flowStatus[row.sku] || '未推送'}</Tag> },
    {
      title: '操作', key: 'action', width: 200,
      render: (_: any, row: any) => (
        <Space>
          <Button size="small" onClick={() => setSelectedRow(row)}>解释</Button>
          <Button size="small" type="primary" icon={<SendOutlined />} loading={pushMutation.isPending} onClick={() => pushMutation.mutate(row)}>推策略</Button>
        </Space>
      ),
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      <OpsPageHeader title="💰 价格竞争力决策驾驶舱" subtitle="先看高风险与高机会分组，再批量下发策略进入决策。" />
      <OpsConclusion
        title="价格结论"
        desc={`当前红区风险 ${formatInteger(data?.summary?.redZone || 0)} 个，优先处理利润受损与高价差SKU，再推进活动参与与促销分组。`}
        actionText="去决策队列"
        onAction={() => navigate('/decision')}
        level="warning"
      />
      <div style={{ height: 16 }} />

      <Tabs activeKey={view} onChange={(k) => setView(k as any)} items={[
        { key: 'daily', label: '日常价格视图' },
        { key: 'campaign', label: '平台活动视图' },
        { key: 'promo', label: '自建促销视图' },
      ]} />

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} lg={6}><Card><Statistic title="SKU 总数" value={data?.summary?.totalSku || 0} prefix={<DollarOutlined />} formatter={(v) => formatInteger(v)} /></Card></Col>
        <Col xs={24} lg={6}><Card><Statistic title="红区风险" value={data?.summary?.redZone || 0} prefix={<WarningOutlined />} valueStyle={{ color: '#f5222d' }} formatter={(v) => formatInteger(v)} /></Card></Col>
        <Col xs={24} lg={6}><Card><Statistic title="平均价差" value={data?.summary?.avgPriceGap || 0} formatter={(v) => formatCurrency(v)} /></Card></Col>
        <Col xs={24} lg={6}><Card><Statistic title="平均毛利率" value={data?.summary?.avgMargin || 0} formatter={(v) => formatPercent(v, 1, true)} prefix={<CheckCircleOutlined />} /></Card></Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} lg={12}><Card title="竞争力区域分布"><LazyEChart option={zoneChart} style={{ height: 320 }} /></Card></Col>
        <Col xs={24} lg={12}><Card title="策略分组管理（引流/标准/高毛利/清仓/活动）"><LazyEChart option={groupChart} style={{ height: 320 }} /></Card></Col>
      </Row>

      <Tabs
        defaultActiveKey="insight"
        items={[
          {
            key: 'insight',
            label: '问题与解释（首屏）',
            children: (
              <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
                <Col xs={24} lg={8}>
                  <Card title="问题识别">
                    {data?.issues?.length ? <List size="small" dataSource={data?.issues || []} renderItem={(x: any) => <List.Item>{displayOrDash(x.sku)} / 价差{formatCurrency(x.priceGap)} / 毛利{formatPercent(x.margin, 1, true)}</List.Item>} /> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无问题" />}
                  </Card>
                </Col>
                <Col xs={24} lg={16}>
                  <Card title="推荐解释面板" size="small">
                    {(data?.explanations?.length ? data.explanations : [
                      { title: '价格建议', content: '当前价格处于可接受区间，可维持并观察。' },
                      { title: '活动建议', content: '平台活动折扣过深时，建议提价后再参与，避免利润透支。' },
                      { title: '利润建议', content: '当前利润偏低时，不建议继续放量，优先修复毛利结构。' },
                      { title: '库存联动', content: '库存风险较高时，建议先补货并收敛广告投放。' },
                    ]).map((x: any, i: number) => <div key={i} style={{ marginBottom: 8 }}><Text strong>{x.title}：</Text>{x.content}</div>)}
                  </Card>
                </Col>
              </Row>
            ),
          },
          {
            key: 'detail',
            label: '批量推荐表（深度分析）',
            children: (
              <Card title="批量推荐表" extra={<Space><Select value={groupFilter} onChange={setGroupFilter} style={{ width: 220 }} options={[{ value: 'all', label: '全部分组' }, ...(data?.groupedStrategies || []).map((g: any) => ({ value: g.key, label: `${strategyGroupLabels[g.key] || g.label} (${formatInteger(g.count)})` }))]} /><Button icon={<ThunderboltOutlined />} onClick={() => navigate('/decision')}>去决策队列</Button><Button onClick={() => refetch()}>刷新</Button></Space>}>
                <Table rowKey="sku" dataSource={rows} columns={columns} loading={isLoading} locale={{ emptyText: '暂无数据' }} scroll={{ x: 1850, y: 460 }} pagination={{ pageSize: 8 }} size="small" tableLayout="fixed" />
              </Card>
            ),
          },
        ]}
      />

      <Drawer title="推荐解释" open={!!selectedRow} onClose={() => setSelectedRow(null)} width={520}>
        {selectedRow && (
          <Space direction="vertical" style={{ width: '100%' }}>
            <Text strong>{displayOrDash(selectedRow.sku)}</Text>
            <Text>当前视图：{view === 'daily' ? '日常价格视图' : view === 'campaign' ? '平台活动视图' : '自建促销视图'}</Text>
            <Text>分组：{strategyGroupLabels[selectedRow.group] || selectedRow.group}</Text>
            <Text>价差：{formatCurrency(selectedRow.priceGap)}</Text>
            <Text>毛利率：{formatPercent(selectedRow.margin, 1, true)}</Text>
            <Text>建议：{displayOrDash(selectedRow.recommendation)}</Text>
            <Button type="primary" onClick={() => pushMutation.mutate(selectedRow)}>推送到策略/决策链路</Button>
          </Space>
        )}
      </Drawer>
    </div>
  )
}
