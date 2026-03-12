import { Row, Col, Card, Statistic, Table, Tag, Progress, Divider, Button, Space, List, Skeleton, Alert, Empty, Tabs } from 'antd'
import { ArrowUpOutlined, ArrowDownOutlined, ShoppingCartOutlined, DollarOutlined, WarningOutlined, RocketOutlined, ThunderboltOutlined, CheckCircleOutlined } from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import dayjs from 'dayjs'
import { dashboardApi } from '../services/api'
import type { DashboardMetrics } from '../types'
import { formatCurrency, formatInteger, formatPercent, displayOrDash } from '../utils/format'
import { statusLabels, strategyTypeLabels } from '../utils/labels'
import { OpsConclusion, OpsPageHeader, OpsRiskTag } from '../components/ops/ProductSection'

export default function Dashboard() {
  const [dateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs]>([dayjs().subtract(7, 'days'), dayjs()])

  const { data: metrics, isLoading, error, refetch } = useQuery<DashboardMetrics>({
    queryKey: ['dashboard', dateRange],
    queryFn: () => dashboardApi.getOverview(),
    staleTime: 5 * 60 * 1000,
  })

  const opening = (metrics as any)?.openingWorkbench

  const trendChartOption = {
    title: { text: '7日营收趋势', left: 'center' },
    tooltip: { trigger: 'axis' },
    legend: { data: ['营收', '订单数'], bottom: 0 },
    xAxis: { type: 'category', data: metrics?.trends?.dates || [] },
    yAxis: [{ type: 'value', name: '营收 (¥)' }, { type: 'value', name: '订单数' }],
    series: [
      { name: '营收', type: 'line', data: metrics?.trends?.revenue || [], smooth: true, itemStyle: { color: '#1890ff' } },
      { name: '订单数', type: 'bar', yAxisIndex: 1, data: metrics?.trends?.orders || [], itemStyle: { color: '#52c41a' } },
    ],
  }

  const topSkuColumns = [
    { title: 'SKU', dataIndex: 'sku', key: 'sku', render: (text: string, r: any) => <Tag color={r.abcClass === 'A' ? 'red' : r.abcClass === 'B' ? 'orange' : 'blue'}>{displayOrDash(text)}</Tag> },
    { title: '营收', dataIndex: 'revenue', key: 'revenue', render: (v: number) => formatCurrency(v) },
    { title: '订单数', dataIndex: 'orders', key: 'orders', render: (v: number) => formatInteger(v) },
    { title: '毛利率', dataIndex: 'margin', key: 'margin', render: (v: number) => formatPercent(v, 1, true) },
    { title: 'ABC分类', dataIndex: 'abcClass', key: 'abcClass', render: (v: string) => <Tag>{displayOrDash(v)}</Tag> },
  ]

  const mustHandleColumns = [
    { title: '优先级', dataIndex: 'type', key: 'type', render: (v: string) => <Tag color={v === 'P0' ? 'red' : v === 'P1' ? 'orange' : 'gold'}>{displayOrDash(v)}</Tag> },
    { title: 'SKU', dataIndex: 'sku', key: 'sku', render: (v: string) => displayOrDash(v) },
    { title: '事项', dataIndex: 'message', key: 'message', render: (v: string) => displayOrDash(v) },
    { title: '动作', dataIndex: 'action', key: 'action', render: (v: string) => displayOrDash(v) },
  ]

  const deltaText = (value?: number | null) => {
    if (value == null) return '对比期数据不足'
    const pct = formatPercent(Math.abs(value), 1, true)
    return value >= 0 ? `较上期 +${pct}` : `较上期 -${pct}`
  }

  const deltaIcon = (value?: number | null) => {
    if (value == null) return null
    return value >= 0 ? <ArrowUpOutlined style={{ color: '#52c41a' }} /> : <ArrowDownOutlined style={{ color: '#f5222d' }} />
  }

  const alertColumns = [
    ...mustHandleColumns.slice(0, 1).map((c: any) => ({
      ...c,
      title: '风险',
      render: (v: string) => <OpsRiskTag level={v === 'P0' ? 'critical' : v === 'P1' ? 'warning' : 'normal'} />,
    })),
    ...mustHandleColumns.slice(1),
  ]

  if (isLoading) {
    return <div style={{ padding: 24 }}><Skeleton active paragraph={{ rows: 12 }} /></div>
  }

  if (error) {
    return (
      <div style={{ padding: 24 }}>
        <Alert type="error" showIcon message="运营总览加载失败" description="后端数据暂不可用，请重试" action={<Button onClick={() => refetch()}>重试</Button>} />
      </div>
    )
  }

  const recentItems = [
    ...((opening?.recentChanges?.recentImports || []).map((x: any) => `导入 #${x.batchId}（${statusLabels[x.status] || x.status}）：成功 ${formatInteger(x.successCount)} / 错误 ${formatInteger(x.errorCount)}`)),
    ...((opening?.recentChanges?.recentStrategies || []).map((x: any) => `策略 #${x.taskId}（${x.priority}）${statusLabels[x.status] || x.status} / ${strategyTypeLabels[x.strategyType] || x.strategyType || '策略任务'}`)),
    ...((opening?.recentChanges?.recentExecution || []).map((x: any) => `执行 #${x.taskId || x.executionId || x.snapshotId} / ${displayOrDash(x.resultSummary || x.reportType)}`)),
  ]

  return (
    <div style={{ padding: '24px' }}>
      <OpsPageHeader title="📊 运营总览总控台" subtitle="先看今日结论与优先动作，再进入趋势、告警与SKU明细。" />
      <OpsConclusion
        title="今日最重要事项"
        desc={`当前待处理 ${(opening?.todaySummary?.pendingAlerts || 0) + (opening?.todaySummary?.pendingStrategies || 0)} 项，建议先处理 P0/P1 风险后再推进增量动作。`}
        level="warning"
      />
      <div style={{ height: 16 }} />

      <Card title={<span><RocketOutlined /> 经营开工台</span>} extra={<Space><Button type="primary" icon={<ThunderboltOutlined />}>一键拉起今日任务</Button><Button icon={<CheckCircleOutlined />}>更新晨会结论</Button></Space>}>
        <Row gutter={[16, 16]}>
          <Col xs={24} lg={8}><Card><Statistic title="今日营收" value={opening?.todaySummary?.todayRevenue || 0} formatter={(v) => formatCurrency(v)} /></Card></Col>
          <Col xs={24} lg={8}><Card><Statistic title="今日订单" value={opening?.todaySummary?.todayOrders || 0} formatter={(v) => formatInteger(v)} prefix={<ShoppingCartOutlined />} /></Card></Col>
          <Col xs={24} lg={8}><Card><Statistic title="待处理事项" value={(opening?.todaySummary?.pendingAlerts || 0) + (opening?.todaySummary?.pendingStrategies || 0)} formatter={(v) => formatInteger(v)} /><Progress percent={Math.min(100, ((opening?.todaySummary?.pendingAlerts || 0) + (opening?.todaySummary?.pendingStrategies || 0)) * 5)} showInfo={false} /></Card></Col>
        </Row>

        <Divider />

        <Row gutter={[16, 16]}>
          <Col xs={24} lg={12}>
            <Card title="今日必处理面板（问题识别 / 推荐动作）">
              <Table dataSource={opening?.mustHandleToday || []} columns={mustHandleColumns} locale={{ emptyText: '暂无必处理事项' }} pagination={false} size="small" rowKey={(r: any, i: number) => `${r.sku}-${i}`} />
            </Card>
          </Col>
          <Col xs={24} lg={12}>
            <Card title="最近变化（导入 / 策略 / 执行）">
              {recentItems.length ? <List size="small" bordered dataSource={recentItems} renderItem={(item) => <List.Item>{item}</List.Item>} /> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无最近变化" />}
            </Card>
          </Col>
        </Row>
      </Card>

      <Divider />

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}><Card><Statistic title="总营收" value={metrics?.totalRevenue || 0} formatter={(v) => formatCurrency(v)} prefix={<DollarOutlined />} /><div style={{ marginTop: 8 }}>{deltaIcon(metrics?.kpiDeltas?.revenue)} {deltaText(metrics?.kpiDeltas?.revenue)}</div></Card></Col>
        <Col xs={24} sm={12} lg={6}><Card><Statistic title="订单总数" value={metrics?.totalOrders || 0} formatter={(v) => formatInteger(v)} prefix={<ShoppingCartOutlined />} /><div style={{ marginTop: 8 }}>{deltaIcon(metrics?.kpiDeltas?.orders)} {deltaText(metrics?.kpiDeltas?.orders)}</div></Card></Col>
        <Col xs={24} sm={12} lg={6}><Card><Statistic title="客单价" value={metrics?.avgOrderValue || 0} formatter={(v) => formatCurrency(v)} /><div style={{ marginTop: 8 }}>{deltaIcon(metrics?.kpiDeltas?.avgOrderValue)} {deltaText(metrics?.kpiDeltas?.avgOrderValue)}</div></Card></Col>
        <Col xs={24} sm={12} lg={6}><Card><Statistic title="平均毛利率" value={metrics ? metrics.profitMargin : 0} formatter={(v) => formatPercent(v, 1, true)} /><Progress percent={(metrics ? metrics.profitMargin : 0) * 100} showInfo={false} /></Card></Col>
      </Row>

      <Divider />

      <Tabs
        defaultActiveKey="trend"
        items={[
          {
            key: 'trend',
            label: '趋势与告警',
            children: (
              <Row gutter={[16, 16]}>
                <Col xs={24} lg={16}><Card title="趋势区：7日营收与订单"><ReactECharts option={trendChartOption} style={{ height: '320px' }} /></Card></Col>
                <Col xs={24} lg={8}><Card title={<span><WarningOutlined /> 告警区：紧急事项</span>}><Table dataSource={metrics?.alerts || []} columns={alertColumns} locale={{ emptyText: '暂无告警' }} pagination={false} size="small" rowKey="sku" scroll={{ y: 280 }} /></Card></Col>
              </Row>
            ),
          },
          {
            key: 'sku',
            label: 'Top SKU / 告警明细',
            children: (
              <Card title="🏆 Top 5 SKU（按营收）"><Table dataSource={metrics?.topSkus || []} columns={topSkuColumns} locale={{ emptyText: '暂无数据' }} pagination={false} size="small" rowKey="sku" scroll={{ y: 300 }} /></Card>
            ),
          },
        ]}
      />
    </div>
  )
}
