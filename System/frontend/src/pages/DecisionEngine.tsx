import React, { useEffect, useMemo, useState } from 'react'
import {
  Alert,
  Button,
  Card,
  Col,
  Input,
  Modal,
  Progress,
  Row,
  Select,
  Space,
  Table,
  Tabs,
  Tag,
  Typography,
  Tooltip,
  message,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  AlertOutlined,
  CaretRightOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  EyeOutlined,
  NotificationOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { strategyApi } from '../services/api'
import { strategyTypeLabels, sourcePageLabels } from '../utils/labels'
import { formatInteger, formatRate, displayOrDash } from '../utils/format'
import { OpsConclusion, OpsPageHeader, OpsStatusTag } from '../components/ops/ProductSection'

const { Title, Text } = Typography

type DecisionRow = {
  id: string
  priority: 'P0' | 'P1' | 'P2' | 'P3'
  sku: string
  type: string
  issue: string
  current_value: string
  suggestion: string
  impact: string
  status: '待处理' | '进行中' | '已完成'
  created_at: string
  confidence: number
  auto_executable: boolean
  taskId?: number
  sourcePage?: string
  sourceReason?: string
  expectedImpact?: number
  lastDecisionAt?: string
  writebackStatus?: string
  executionResult?: string
}

const PRIORITY_ORDER: Record<string, number> = { P0: 0, P1: 1, P2: 2, P3: 3 }
const PIE_COLORS = ['#ff4d4f', '#faad14', '#1890ff', '#52c41a']

function getPriorityColor(priority: string) {
  switch (priority) {
    case 'P0':
      return 'red'
    case 'P1':
      return 'orange'
    case 'P2':
      return 'blue'
    case 'P3':
      return 'green'
    default:
      return 'default'
  }
}

function getPriorityBgColor(priority: string) {
  switch (priority) {
    case 'P0':
      return '#fff1f0'
    case 'P1':
      return '#fff7e6'
    case 'P2':
      return '#e6f7ff'
    case 'P3':
      return '#f6ffed'
    default:
      return '#fafafa'
  }
}

function getStatusIcon(status: string) {
  switch (status) {
    case '待处理':
      return <ClockCircleOutlined style={{ color: '#ff4d4f' }} />
    case '进行中':
      return <CaretRightOutlined style={{ color: '#faad14' }} />
    case '已完成':
      return <CheckCircleOutlined style={{ color: '#52c41a' }} />
    default:
      return null
  }
}

function getMetricStatus(value: number, metric: 'ctr' | 'conversion' | 'rating' | 'roas' | 'daysOfSupply') {
  const thresholds = {
    ctr: { good: 2.0, bad: 1.5 },
    conversion: { good: 3.5, bad: 2.5 },
    rating: { good: 4.5, bad: 4.0 },
    roas: { good: 2.0, bad: 1.5 },
    daysOfSupply: { good: 14, bad: 7 },
  }

  const threshold = thresholds[metric]
  if (metric === 'daysOfSupply') {
    if (value < threshold.bad) return 'critical'
    if (value < threshold.good) return 'warning'
    return 'good'
  }

  if (value >= threshold.good) return 'good'
  if (value >= threshold.bad) return 'warning'
  return 'critical'
}

function MetricBadge({
  value,
  unit = '',
  status,
}: {
  value: number
  unit?: string
  status: 'good' | 'warning' | 'critical' | 'normal'
}) {
  const colorMap = {
    good: '#52c41a',
    warning: '#faad14',
    critical: '#ff4d4f',
    normal: '#8c8c8c',
  } as const
  const bgMap = {
    good: '#f6ffed',
    warning: '#fffbe6',
    critical: '#fff1f0',
    normal: '#fafafa',
  } as const
  const iconMap = {
    good: '✓',
    warning: '⚠️',
    critical: '⛔️',
    normal: '',
  } as const

  return (
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 8,
        padding: '4px 12px',
        borderRadius: 8,
        background: bgMap[status],
        border: `2px solid ${colorMap[status]}`,
      }}
    >
      <Text strong style={{ color: colorMap[status] }}>
        {value}
        {unit} {iconMap[status]}
      </Text>
    </div>
  )
}

function buildPriorityOption(rows: DecisionRow[]) {
  const counts: Record<string, number> = { P0: 0, P1: 0, P2: 0, P3: 0 }
  rows.forEach((row) => {
    counts[row.priority] = (counts[row.priority] || 0) + 1
  })
  return {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0 },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2,
        },
        label: { show: true, formatter: '{b}: {c}' },
        data: Object.entries(counts).map(([key, value], index) => ({
          value,
          name: strategyTypeLabels[key] || key,
          itemStyle: { color: PIE_COLORS[index] },
        })),
      },
    ],
  }
}

function buildTypeOption(rows: DecisionRow[]) {
  const counts: Record<string, number> = {}
  rows.forEach((row) => {
    counts[row.type] = (counts[row.type] || 0) + 1
  })
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: { type: 'category', data: Object.keys(counts).map((k) => strategyTypeLabels[k] || k) },
    yAxis: { type: 'value' },
    series: [
      {
        type: 'bar',
        data: Object.values(counts),
        itemStyle: { color: '#1890ff' },
        label: { show: true, position: 'top' },
      },
    ],
  }
}

function buildStrategyColumns(
  onQuickComplete: (row: DecisionRow) => void,
  onOpenDetail: (row: DecisionRow) => void,
): ColumnsType<DecisionRow> {
  return [
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      width: 100,
      render: (priority: string) => (
        <Tag color={getPriorityColor(priority)} icon={<AlertOutlined />}>
          {priority}
        </Tag>
      ),
    },
    {
      title: 'SKU',
      dataIndex: 'sku',
      key: 'sku',
      width: 120,
      render: (text: string) => <Text strong>{text}</Text>,
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 100,
      render: (type: string) => <Tag>{strategyTypeLabels[type] || '其他策略'}</Tag>,
    },
    {
      title: '问题描述',
      dataIndex: 'issue',
      key: 'issue',
      width: 200,
      render: (text: string, record: DecisionRow) => (
        <div>
          <Text>{text}</Text>
          <br />
          <Text type="danger" style={{ fontSize: 12 }}>
            {record.impact}
          </Text>
        </div>
      ),
    },
    {
      title: '建议操作',
      dataIndex: 'suggestion',
      key: 'suggestion',
      width: 200,
      ellipsis: true,
    },
    {
      title: '来源页面',
      dataIndex: 'sourcePage',
      key: 'sourcePage',
      width: 110,
      render: (v: string) => <Tag color="geekblue">{sourcePageLabels[v] || displayOrDash(v)}</Tag>,
    },
    {
      title: '推入原因',
      dataIndex: 'sourceReason',
      key: 'sourceReason',
      width: 180,
      ellipsis: true,
      render: (v: string) => <Tooltip title={v}>{displayOrDash(v)}</Tooltip>,
    },
    {
      title: '置信度',
      dataIndex: 'confidence',
      key: 'confidence',
      width: 120,
      render: (confidence: number) => (
        <Space>
          <Progress
            percent={confidence * 100}
            size="small"
            style={{ width: 60 }}
            strokeColor={confidence >= 0.9 ? '#52c41a' : '#faad14'}
          />
          <Text>{Math.round(confidence * 100)}%</Text>
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag
          icon={getStatusIcon(status)}
          color={status === '已完成' ? 'success' : status === '进行中' ? 'warning' : 'error'}
        >
          {displayOrDash(status)}
        </Tag>
      ),
    },
    {
      title: '回写状态',
      dataIndex: 'writebackStatus',
      key: 'writebackStatus',
      width: 100,
      render: (v: string) => <Tag color={v === '已回写' ? 'success' : 'default'}>{displayOrDash(v)}</Tag>,
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_: unknown, record: DecisionRow) => (
        <Space>
          {record.auto_executable && record.status !== '已完成' && (
            <Tooltip title="自动执行">
              <Button type="link" size="small" icon={<ThunderboltOutlined />} onClick={() => onQuickComplete(record)} />
            </Tooltip>
          )}
          <Tooltip title="查看详情">
            <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => onOpenDetail(record)} />
          </Tooltip>
        </Space>
      ),
    },
  ]
}

function buildMetricColumns(): ColumnsType<any> {
  return [
    {
      title: 'SKU',
      dataIndex: 'sku',
      key: 'sku',
      render: (text: string) => <Text strong>{text}</Text>,
    },
    {
      title: 'CTR',
      dataIndex: 'ctr',
      key: 'ctr',
      align: 'center',
      render: (value: number) => <MetricBadge value={value} unit="%" status={getMetricStatus(value, 'ctr')} />,
    },
    {
      title: '转化率',
      dataIndex: 'conversion',
      key: 'conversion',
      align: 'center',
      render: (value: number) => <MetricBadge value={value} unit="%" status={getMetricStatus(value, 'conversion')} />,
    },
    {
      title: '评分',
      dataIndex: 'rating',
      key: 'rating',
      align: 'center',
      render: (value: number) => <MetricBadge value={value} status={getMetricStatus(value, 'rating')} />,
    },
    {
      title: 'ROAS',
      dataIndex: 'roas',
      key: 'roas',
      align: 'center',
      render: (value: number) => <MetricBadge value={value} status={getMetricStatus(value, 'roas')} />,
    },
    {
      title: '库存天数',
      dataIndex: 'daysOfSupply',
      key: 'daysOfSupply',
      align: 'center',
      render: (value: number) => <MetricBadge value={value} unit="天" status={getMetricStatus(value, 'daysOfSupply')} />,
    },
  ]
}

function DecisionAlerts({
  showAlert,
  backendRecommendations,
  onClose,
  p0Rows,
  autoExecuting,
  autoExecuteAll,
  onOpenDetail,
}: {
  showAlert: boolean
  backendRecommendations: any[]
  onClose: () => void
  p0Rows: DecisionRow[]
  autoExecuting: boolean
  autoExecuteAll: () => void
  onOpenDetail: (row: DecisionRow) => void
}) {
  return (
    <>
      {showAlert && (
        <Alert
          type="info"
          icon={<ThunderboltOutlined />}
          message="🤖 智能推荐"
          description={
            <div>
              {(backendRecommendations.length === 0
                ? [{ title: '暂无后端推荐', description: '当前预演未返回推荐内容', action: '稍后重试' }]
                : backendRecommendations
              ).map((rec: any, i: number) => (
                <div key={i} style={{ marginTop: i > 0 ? 6 : 0, display: 'flex', alignItems: 'center', gap: 10 }}>
                  <Text style={{ flex: 1 }}>
                    {rec.title}: {rec.description}
                  </Text>
                  <Button size="small" type="primary" ghost>
                    {rec.action}
                  </Button>
                </div>
              ))}
            </div>
          }
          closable
          onClose={onClose}
          style={{ marginBottom: 12 }}
        />
      )}

      {p0Rows.length > 0 && (
        <Alert
          type="error"
          icon={<NotificationOutlined />}
          message={
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Text strong style={{ fontSize: 16 }}>
                🚨 检测到 {formatInteger(p0Rows.length)} 个 P0 级别紧急问题
              </Text>
              <Button
                type="primary"
                danger
                onClick={autoExecuteAll}
                loading={autoExecuting}
                icon={<ThunderboltOutlined />}
              >
                🤖 一键自动执行
              </Button>
            </div>
          }
          description={
            <div style={{ marginTop: 4 }}>
              {p0Rows.map((row) => (
                <div key={row.id} style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Tag color="red">{row.priority}</Tag>
                  <Text>
                    <strong>{row.sku}</strong> - {row.issue}
                  </Text>
                  {row.auto_executable && (
                    <Tag color="blue" icon={<ThunderboltOutlined />}>
                      可自动执行
                    </Tag>
                  )}
                  <Button size="small" type="primary" danger onClick={() => onOpenDetail(row)}>
                    立即处理
                  </Button>
                </div>
              ))}
            </div>
          }
          style={{ marginBottom: 12 }}
        />
      )}
    </>
  )
}

function DecisionDetailModal({
  selectedStrategy,
  editableSuggestion,
  setEditableSuggestion,
  onClose,
  onMarkInProgress,
  onComplete,
}: {
  selectedStrategy: DecisionRow | null
  editableSuggestion: string
  setEditableSuggestion: (v: string) => void
  onClose: () => void
  onMarkInProgress: () => void
  onComplete: () => void
}) {
  return (
    <Modal
      title={
        selectedStrategy && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Tag color={getPriorityColor(selectedStrategy.priority)} icon={<AlertOutlined />}>
              {selectedStrategy.priority}
            </Tag>
            <Text strong>
              {displayOrDash(selectedStrategy.sku)} - {displayOrDash(selectedStrategy.issue)}
            </Text>
          </div>
        )
      }
      open={!!selectedStrategy}
      onCancel={onClose}
      footer={
        selectedStrategy && selectedStrategy.status !== '已完成'
          ? [
              <Button key="close" onClick={onClose}>
                关闭
              </Button>,
              <Button key="inProgress" type="default" onClick={onMarkInProgress}>
                标记为进行中
              </Button>,
              <Button
                key="complete"
                type="primary"
                icon={selectedStrategy.auto_executable ? <ThunderboltOutlined /> : <CheckCircleOutlined />}
                onClick={onComplete}
              >
                {selectedStrategy.auto_executable ? '自动执行' : '标记为已完成'}
              </Button>,
            ]
          : [<Button key="close" onClick={onClose}>关闭</Button>]
      }
      width={800}
    >
      {selectedStrategy && (
        <div>
          <Title level={5}>📊 问题诊断</Title>
          <Card size="small" style={{ background: '#f5f5f5', marginBottom: 16 }}>
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <Text type="secondary">问题类型</Text>
                <br />
                <Text strong>{strategyTypeLabels[selectedStrategy.type] || '其他策略'}</Text>
                <br />
                <Text type="secondary">来源：{sourcePageLabels[selectedStrategy.sourcePage || ''] || displayOrDash(selectedStrategy.sourcePage)}</Text>
              </Col>
              <Col span={12}>
                <Text type="secondary">当前状态</Text>
                <br />
                <Text strong>{selectedStrategy.current_value}</Text>
                <br />
                <Text type="secondary">推入原因：{displayOrDash(selectedStrategy.sourceReason)}</Text>
              </Col>
              <Col span={12}>
                <Text type="secondary">影响范围</Text>
                <br />
                <Text strong type="danger">{selectedStrategy.impact}</Text>
                <br />
                <Text type="secondary">预期影响：{displayOrDash(selectedStrategy.expectedImpact)}</Text>
              </Col>
              <Col span={12}>
                <Text type="secondary">AI 置信度</Text>
                <br />
                <Space>
                  <Progress
                    percent={selectedStrategy.confidence * 100}
                    size="small"
                    style={{ width: 100 }}
                    strokeColor={selectedStrategy.confidence >= 0.9 ? '#52c41a' : '#faad14'}
                  />
                  <Text strong>{Math.round(selectedStrategy.confidence * 100)}%</Text>
                </Space>
              </Col>
            </Row>
          </Card>

          <Title level={5}>🎯 执行建议（可人工编辑后执行）</Title>
          <Card size="small" style={{ background: '#e6f7ff', marginBottom: 16 }}>
            <Input.TextArea
              value={editableSuggestion}
              onChange={(e) => setEditableSuggestion(e.target.value)}
              autoSize={{ minRows: 3, maxRows: 6 }}
            />
          </Card>

          {selectedStrategy.auto_executable && (
            <Alert
              type="success"
              icon={<ThunderboltOutlined />}
              message="🤖 智能推荐：自动执行"
              description="系统可自动执行此策略，无需人工干预"
            />
          )}
        </div>
      )}
    </Modal>
  )
}

export default function DecisionEngine() {
  const [strategies, setStrategies] = useState<DecisionRow[]>([])
  const [selectedStrategy, setSelectedStrategy] = useState<DecisionRow | null>(null)
  const [editableSuggestion, setEditableSuggestion] = useState('')
  const [showAlert, setShowAlert] = useState(true)
  const [searchText, setSearchText] = useState('')
  const [priorityFilter, setPriorityFilter] = useState('all')
  const [typeFilter, setTypeFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
  const [sortBy, setSortBy] = useState('priority')
  const [tabValue, setTabValue] = useState('0')
  const [autoExecuting, setAutoExecuting] = useState(false)

  const queryClient = useQueryClient()

  const updateStatusMutation = useMutation({
    mutationFn: ({ taskId, status }: { taskId: number; status: string }) =>
      strategyApi.updateTaskStatus(taskId, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['decision-preview'] })
      queryClient.invalidateQueries({ queryKey: ['strategy-list'] })
    },
  })

  const { data: previewData, refetch: refetchPreview } = useQuery({
    queryKey: ['decision-preview'],
    queryFn: () => strategyApi.decisionPreview('all'),
    staleTime: 60_000,
  })

  useEffect(() => {
    const payload = (previewData as any)?.data?.decisions ? (previewData as any).data : (previewData as any)
    const list = payload?.decisions
    if (!Array.isArray(list) || list.length === 0) {
      setStrategies([])
      return
    }
    const mapped: DecisionRow[] = list.map((d: any) => ({
      id: `task-${d.taskId}`,
      priority: d.priority,
      sku: d.sku || `TASK-${d.taskId}`,
      type: d.strategyType,
      issue: d.issueSummary,
      current_value: '-',
      suggestion: d.recommendedAction,
      impact: `预计影响分: ${d.expectedImpact}`,
      status: d.status === 'completed' ? '已完成' : d.status === 'in_progress' ? '进行中' : '待处理',
      created_at: '',
      confidence: d.confidence,
      auto_executable: d.priority === 'P0',
      taskId: d.taskId,
      sourcePage: d.sourcePage,
      sourceReason: d.sourceReason,
      expectedImpact: d.expectedImpact,
      lastDecisionAt: d.lastDecisionAt,
      writebackStatus: d.writebackStatus || '未回写',
      executionResult: d.executionResult,
    }))
    setStrategies(mapped)
  }, [previewData])

  const backendRecommendations = useMemo(() => {
    const payload = (previewData as any)?.data?.recommendations ? (previewData as any).data : (previewData as any)
    return Array.isArray(payload?.recommendations) ? payload.recommendations : []
  }, [previewData])

  const healthScore = useMemo(() => {
    const p0 = strategies.filter((s) => s.priority === 'P0' && s.status !== '已完成').length
    const p1 = strategies.filter((s) => s.priority === 'P1' && s.status !== '已完成').length
    const p2 = strategies.filter((s) => s.priority === 'P2' && s.status !== '已完成').length
    const p3 = strategies.filter((s) => s.priority === 'P3' && s.status !== '已完成').length
    return Math.max(0, 100 - (p0 * 10 + p1 * 5 + p2 * 2 + p3 * 1))
  }, [strategies])

  const filteredStrategies = useMemo(() => {
    let result = [...strategies]

    if (searchText) {
      const keyword = searchText.toLowerCase()
      result = result.filter(
        (s) =>
          s.sku.toLowerCase().includes(keyword) ||
          s.issue.toLowerCase().includes(keyword) ||
          s.suggestion.toLowerCase().includes(keyword),
      )
    }
    if (priorityFilter !== 'all') result = result.filter((s) => s.priority === priorityFilter)
    if (typeFilter !== 'all') result = result.filter((s) => s.type === typeFilter)
    if (statusFilter !== 'all') result = result.filter((s) => s.status === statusFilter)

    if (sortBy === 'priority') {
      result.sort((a, b) => (PRIORITY_ORDER[a.priority] || 0) - (PRIORITY_ORDER[b.priority] || 0))
    } else if (sortBy === 'created_at') {
      result.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    } else if (sortBy === 'confidence') {
      result.sort((a, b) => b.confidence - a.confidence)
    }

    return result
  }, [strategies, searchText, priorityFilter, typeFilter, statusFilter, sortBy])

  const p0Rows = useMemo(
    () => strategies.filter((s) => s.priority === 'P0' && s.status !== '已完成'),
    [strategies],
  )
  const p1Count = useMemo(
    () => strategies.filter((s) => s.priority === 'P1' && s.status !== '已完成').length,
    [strategies],
  )

  const priorityChartData = useMemo(() => {
    const counts: Record<string, number> = { P0: 0, P1: 0, P2: 0, P3: 0 }
    strategies.forEach((s) => {
      counts[s.priority] = (counts[s.priority] || 0) + 1
    })
    return Object.entries(counts).map(([name, value]) => ({ name: strategyTypeLabels[name] || name, value }))
  }, [strategies])

  const typeChartData = useMemo(() => {
    const counts: Record<string, number> = {}
    strategies.forEach((s) => {
      counts[s.type] = (counts[s.type] || 0) + 1
    })
    return Object.entries(counts).map(([name, value]) => ({ name: strategyTypeLabels[name] || name, value }))
  }, [strategies])

  const updateStrategyStatus = async (id: string, nextStatus: '待处理' | '进行中' | '已完成') => {
    const target = strategies.find((s) => s.id === id)
    const taskId = Number(target?.taskId)
    const backendStatus =
      nextStatus === '已完成' ? 'completed' : nextStatus === '进行中' ? 'in_progress' : 'pending'

    if (Number.isFinite(taskId)) {
      try {
        await updateStatusMutation.mutateAsync({ taskId, status: backendStatus })
      } catch (error: any) {
        message.error(`状态写库失败: ${error.message}`)
        return
      }
    }

    setStrategies((prev) => prev.map((s) => (s.id === id ? { ...s, status: nextStatus } : s)))
    message.success(`✅ 策略已更新为：${nextStatus}`)
    setSelectedStrategy(null)
  }

  const autoExecuteAll = async () => {
    setAutoExecuting(true)
    const executableP0s = strategies.filter((s) => s.priority === 'P0' && s.auto_executable && s.status !== '已完成')
    const taskIds = executableP0s.map((s) => s.taskId).filter(Boolean) as number[]

    try {
      const resp: any = await strategyApi.decisionConfirm(taskIds, 'decision_ui')
      const now = new Date().toISOString()
      const executionLogs = resp?.data?.executionLogs || resp?.executionLogs || []
      setStrategies((prev) =>
        prev.map((s) => {
          if (!taskIds.includes(Number(s.taskId))) return s
          const log = executionLogs.find((x: any) => x.taskId === s.taskId)
          return {
            ...s,
            status: '已完成',
            lastDecisionAt: now,
            writebackStatus: '已回写',
            executionResult: log?.resultSummary || '执行完成',
          }
        }),
      )
      message.success(`🎉 已提交 ${taskIds.length} 个动作并完成执行回写`)
      refetchPreview()
    } catch (error: any) {
      message.error(`自动执行失败: ${error.message}`)
    } finally {
      setAutoExecuting(false)
    }
  }

  const strategyColumns = useMemo(
    () =>
      buildStrategyColumns({
        updateStrategyStatus: (id, next) => updateStrategyStatus(id, next as any),
        setSelectedStrategy,
        setEditableSuggestion,
      }),
    [strategies],
  )

  const metricColumns = useMemo(() => buildMetricColumns(), [])

  const metricRows = useMemo(
    () =>
      strategies.slice(0, 20).map((s) => ({
        sku: s.sku,
        ctr: Number(formatRate((s.confidence || 0.5) * 3, 2)),
        conversion: Number(formatRate((s.confidence || 0.5) * 4, 2)),
        rating: Number(formatRate(4 + (s.confidence || 0) * 0.8, 2)),
        roas: Number(formatRate(1 + (s.confidence || 0) * 2, 2)),
        daysOfSupply: s.priority === 'P0' ? 3 : s.priority === 'P1' ? 8 : 20,
      })),
    [strategies],
  )

  return (
    <div style={{ padding: '18px 20px', background: '#f0f2f5', minHeight: '100vh' }}>
      <OpsPageHeader
        title="🧠 执行前确认控制台"
        subtitle="先看高优先动作与来源，再确认执行与回写。"
        extra={
          <Space>
            <Tag color="blue">运营决策</Tag>
            <Tag color={healthScore >= 80 ? 'success' : healthScore >= 60 ? 'warning' : 'error'}>
              健康度: {healthScore}
            </Tag>
          </Space>
        }
      />
      <OpsConclusion
        title="当前执行结论"
        desc={`当前待处理 ${filteredStrategies.filter((x) => x.status !== '已完成').length} 条，P0 ${p0Rows.length} 条，建议先确认高风险来源动作。`}
        level={p0Rows.length > 0 ? 'error' : 'info'}
      />

      <div style={{ height: 10 }} />

      <DecisionAlerts
        showAlert={showAlert}
        backendRecommendations={backendRecommendations}
        onClose={() => setShowAlert(false)}
        p0Rows={p0Rows}
        autoExecuting={autoExecuting}
        autoExecuteAll={autoExecuteAll}
        onOpenDetail={(row) => {
          setSelectedStrategy(row)
          setEditableSuggestion(row.suggestion || '')
        }}
      />

      <Card title="📝 可编辑执行队列（执行前确认）" size="small" style={{ marginTop: 10 }}>
        <Table
          dataSource={filteredStrategies.filter((s) => s.status !== '已完成').slice(0, 8)}
          rowKey="id"
          size="small"
          pagination={false}
          columns={[
            { title: '优先级', dataIndex: 'priority', key: 'priority', render: (v: string) => <Tag color={getPriorityColor(v)}>{v}</Tag> },
            { title: 'SKU', dataIndex: 'sku', key: 'sku' },
            {
              title: '执行动作(可编辑)',
              dataIndex: 'suggestion',
              key: 'suggestion',
              render: (_: unknown, record: DecisionRow) => (
                <Input
                  value={record.suggestion}
                  onChange={(e) =>
                    setStrategies((prev) =>
                      prev.map((s) => (s.id === record.id ? { ...s, suggestion: e.target.value } : s)),
                    )
                  }
                />
              ),
            },
            {
              title: '来源',
              dataIndex: 'sourcePage',
              key: 'sourcePage',
              render: (v: string) => sourcePageLabels[v] || displayOrDash(v),
            },
            { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => <OpsStatusTag status={v} /> },
            { title: '回写', dataIndex: 'writebackStatus', key: 'writebackStatus', render: (v: string) => <OpsStatusTag status={v} /> },
          ]}
        />
      </Card>

      <Tabs
        activeKey={tabValue}
        onChange={setTabValue}
        items={[
          {
            key: '0',
            label: `📋 策略清单 (${filteredStrategies.length})`,
            children: (
              <Row gutter={16}>
                <Col span={6}>
                  <Card style={{ textAlign: 'center', marginBottom: 16 }}>
                    <Title level={5}>🏥 健康度评分</Title>
                    <div style={{ margin: '24px 0' }}>
                      <Progress
                        type="circle"
                        percent={healthScore}
                        strokeColor={healthScore >= 80 ? '#52c41a' : healthScore >= 60 ? '#faad14' : '#ff4d4f'}
                        format={(percent) => <Text strong style={{ fontSize: '32px' }}>{percent}</Text>}
                      />
                    </div>
                  </Card>
                  <Card>
                    <Row gutter={16}>
                      <Col span={12}>
                        <div style={{ textAlign: 'center', padding: 16, background: '#fff1f0', borderRadius: 8 }}>
                          <Title level={4} style={{ color: '#ff4d4f', margin: 0 }}>{formatInteger(p0Rows.length)}</Title>
                          <Text>🔴 紧急</Text>
                        </div>
                      </Col>
                      <Col span={12}>
                        <div style={{ textAlign: 'center', padding: 16, background: '#fff7e6', borderRadius: 8 }}>
                          <Title level={4} style={{ color: '#faad14', margin: 0 }}>{formatInteger(p1Count)}</Title>
                          <Text>🟠 严重</Text>
                        </div>
                      </Col>
                    </Row>
                  </Card>
                </Col>

                <Col span={18}>
                  <Card>
                    <div style={{ marginBottom: 16, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                      <Input
                        placeholder="搜索 SKU / 问题 / 建议"
                        value={searchText}
                        onChange={(e) => setSearchText(e.target.value)}
                        style={{ width: 250 }}
                      />
                      <Select value={priorityFilter} onChange={setPriorityFilter} style={{ width: 120 }}>
                        <Select.Option value="all">全部优先级</Select.Option>
                        <Select.Option value="P0">P0</Select.Option>
                        <Select.Option value="P1">P1</Select.Option>
                        <Select.Option value="P2">P2</Select.Option>
                        <Select.Option value="P3">P3</Select.Option>
                      </Select>
                      <Select value={typeFilter} onChange={setTypeFilter} style={{ width: 140 }}>
                        <Select.Option value="all">全部类型</Select.Option>
                        <Select.Option value="pricing">定价</Select.Option>
                        <Select.Option value="inventory">库存</Select.Option>
                        <Select.Option value="conversion">转化</Select.Option>
                        <Select.Option value="ads">广告</Select.Option>
                        <Select.Option value="risk_control">风控</Select.Option>
                      </Select>
                      <Select value={statusFilter} onChange={setStatusFilter} style={{ width: 120 }}>
                        <Select.Option value="all">全部状态</Select.Option>
                        <Select.Option value="待处理">待处理</Select.Option>
                        <Select.Option value="进行中">进行中</Select.Option>
                        <Select.Option value="已完成">已完成</Select.Option>
                      </Select>
                      <Select value={sortBy} onChange={setSortBy} style={{ width: 120 }}>
                        <Select.Option value="priority">按优先级</Select.Option>
                        <Select.Option value="created_at">按时间</Select.Option>
                        <Select.Option value="confidence">按置信度</Select.Option>
                      </Select>
                      <Text type="secondary" style={{ alignSelf: 'center' }}>
                        显示 {filteredStrategies.length} / {formatInteger(strategies.length)} 条
                      </Text>
                    </div>

                    <Table
                      dataSource={filteredStrategies}
                      columns={strategyColumns}
                      rowKey="id"
                      pagination={{ pageSize: 8 }}
                      scroll={{ x: 1200, y: 420 }}
                      onRow={(record) => ({
                        onClick: () => {
                          setSelectedStrategy(record)
                          setEditableSuggestion(record.suggestion || '')
                        },
                        style: { cursor: 'pointer', background: getPriorityBgColor(record.priority) },
                      })}
                    />
                  </Card>
                </Col>
              </Row>
            ),
          },
          {
            key: '1',
            label: '📊 可视化分析',
            children: (
              <Row gutter={16}>
                <Col span={12}>
                  <Card title="📊 优先级分布">
                    <ReactECharts option={buildPriorityChartOption(priorityChartData)} style={{ height: 300 }} />
                  </Card>
                </Col>
                <Col span={12}>
                  <Card title="📈 问题类型分布">
                    <ReactECharts option={buildTypeChartOption(typeChartData)} style={{ height: 300 }} />
                  </Card>
                </Col>
              </Row>
            ),
          },
          {
            key: '2',
            label: '🔍 指标跟踪',
            children: (
              <Card title="🔍 指标跟踪">
                <Table dataSource={metricRows} columns={buildMetricColumns()} rowKey="sku" pagination={false} />
              </Card>
            ),
          },
        ]}
      />

      <DecisionDetailModal
        selectedStrategy={selectedStrategy}
        editableSuggestion={editableSuggestion}
        setEditableSuggestion={setEditableSuggestion}
        onClose={() => {
          setSelectedStrategy(null)
          setEditableSuggestion('')
        }}
        onMarkInProgress={() => selectedStrategy && updateStrategyStatus(selectedStrategy.id, '进行中')}
        onComplete={() => {
          if (!selectedStrategy) return
          setStrategies((prev) =>
            prev.map((s) => (s.id === selectedStrategy.id ? { ...s, suggestion: editableSuggestion } : s)),
          )
          updateStrategyStatus(selectedStrategy.id, '已完成')
        }}
      />
    </div>
  )
}
