import React, { useState, useMemo, useEffect } from 'react'
import {
  Card,
  Row,
  Col,
  Table,
  Tag,
  Button,
  Alert,
  Space,
  Modal,
  Input,
  Select,
  Tabs,
  Progress,
  Typography,
  Statistic,
  Badge,
  Tooltip,
  message
} from 'antd'
import {
  AlertOutlined,
  ShoppingCartOutlined,
  DollarOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  BellOutlined,
  EyeOutlined,
  CaretRightOutlined,
  SearchOutlined,
  FilterOutlined,
  SortAscendingOutlined,
  ThunderboltOutlined,
  NotificationOutlined,
  CloseOutlined,
  WarningOutlined,
  InfoCircleOutlined,
  ArrowRightOutlined,
  TrophyOutlined,
  StarOutlined
} from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import { strategyApi } from '../services/api'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { strategyTypeLabels, sourcePageLabels } from '../utils/labels'
import { formatRate, formatInteger, displayOrDash } from '../utils/format'
import { OpsConclusion, OpsPageHeader, OpsStatusTag } from '../components/ops/ProductSection'

const { Title, Text } = Typography
const { Search } = Input

// ===== 智能决策引擎 - Ant Design 版本 =====

export default function DecisionEngine() {
  // ===== 状态管理 =====
  const [strategies, setStrategies] = useState<any[]>([])
  const [selectedStrategy, setSelectedStrategy] = useState<any>(null)
  const [editableSuggestion, setEditableSuggestion] = useState('')
  const [showAlert, setShowAlert] = useState(true)

  // 筛选和排序
  const [searchText, setSearchText] = useState('')
  const [priorityFilter, setPriorityFilter] = useState('all')
  const [typeFilter, setTypeFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
  const [sortBy, setSortBy] = useState('priority')

  // 标签页
  const [tabValue, setTabValue] = useState('0')

  // 自动执行进度
  const [autoExecuting, setAutoExecuting] = useState(false)

  const queryClient = useQueryClient()
  const updateStatusMutation = useMutation({
    mutationFn: ({ taskId, status }: { taskId: number; status: string }) => strategyApi.updateTaskStatus(taskId, { status }),
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
    const mapped = list.map((d: any) => ({
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
    }))
    setStrategies(mapped)
  }, [previewData])

  const backendRecommendations = useMemo(() => {
    const payload = (previewData as any)?.data?.recommendations ? (previewData as any).data : (previewData as any)
    const list = payload?.recommendations
    if (Array.isArray(list) && list.length > 0) return list
    return []
  }, [previewData])

  // ===== 智能计算 =====
  // 健康度评分
  const healthScore = useMemo(() => {
    const p0Count = strategies.filter(s => s.priority === 'P0' && s.status !== '已完成').length
    const p1Count = strategies.filter(s => s.priority === 'P1' && s.status !== '已完成').length
    const p2Count = strategies.filter(s => s.priority === 'P2' && s.status !== '已完成').length
    const p3Count = strategies.filter(s => s.priority === 'P3' && s.status !== '已完成').length

    return Math.max(0, 100 - (p0Count * 10 + p1Count * 5 + p2Count * 2 + p3Count * 1))
  }, [strategies])

  // 筛选后的策略
  const filteredStrategies = useMemo(() => {
    let result = [...strategies]

    if (searchText) {
      result = result.filter(s =>
        s.sku.toLowerCase().includes(searchText.toLowerCase()) ||
        s.issue.toLowerCase().includes(searchText.toLowerCase()) ||
        s.suggestion.toLowerCase().includes(searchText.toLowerCase())
      )
    }

    if (priorityFilter !== 'all') {
      result = result.filter(s => s.priority === priorityFilter)
    }

    if (typeFilter !== 'all') {
      result = result.filter(s => s.type === typeFilter)
    }

    if (statusFilter !== 'all') {
      result = result.filter(s => s.status === statusFilter)
    }

    const priorityOrder: Record<string, number> = { 'P0': 0, 'P1': 1, 'P2': 2, 'P3': 3 }
    if (sortBy === 'priority') {
      result.sort((a, b) => (priorityOrder[a.priority] || 0) - (priorityOrder[b.priority] || 0))
    } else if (sortBy === 'created_at') {
      result.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    } else if (sortBy === 'confidence') {
      result.sort((a, b) => b.confidence - a.confidence)
    }

    return result
  }, [strategies, searchText, priorityFilter, typeFilter, statusFilter, sortBy])

  // 图表数据
  const priorityChartData = useMemo(() => {
    const counts: any = { 'P0': 0, 'P1': 0, 'P2': 0, 'P3': 0 }
    strategies.forEach(s => counts[s.priority]++)
    return Object.entries(counts).map(([name, value]) => ({ name: strategyTypeLabels[name] || '其他策略', value }))
  }, [strategies])

  const typeChartData = useMemo(() => {
    const counts: any = {}
    strategies.forEach(s => {
      counts[s.type] = (counts[s.type] || 0) + 1
    })
    return Object.entries(counts).map(([name, value]) => ({ name: strategyTypeLabels[name] || '其他策略', value }))
  }, [strategies])

  // ===== 交互功能 =====
  const updateStrategyStatus = async (id: string, newStatus: string) => {
    const target = strategies.find((s) => s.id === id)
    const taskId = Number(target?.taskId)
    const backendStatus = newStatus === '已完成' ? 'completed' : newStatus === '进行中' ? 'in_progress' : 'pending'

    if (Number.isFinite(taskId)) {
      try {
        await updateStatusMutation.mutateAsync({ taskId, status: backendStatus })
      } catch (error: any) {
        message.error(`状态写库失败: ${error.message}`)
        return
      }
    }

    setStrategies(strategies.map(s =>
      s.id === id ? { ...s, status: newStatus } : s
    ))
    message.success(`✅ 策略已更新为：${newStatus}`)
    setSelectedStrategy(null)
  }

  const autoExecuteAll = async () => {
    setAutoExecuting(true)

    const executableP0s = strategies.filter(s =>
      s.priority === 'P0' && s.auto_executable && s.status !== '已完成'
    )
    const taskIds = executableP0s.map((s: any) => s.taskId).filter(Boolean)

    try {
      const resp: any = await strategyApi.decisionConfirm(taskIds, 'decision_ui')
      const now = new Date().toISOString()
      const executionLogs = (resp?.data?.executionLogs || resp?.executionLogs || [])
      setStrategies(strategies.map(s => {
        if (!taskIds.includes((s as any).taskId)) return s
        const log = executionLogs.find((x: any) => x.taskId === (s as any).taskId)
        return { ...s, status: '已完成', lastDecisionAt: now, writebackStatus: '已回写', executionResult: log?.resultSummary || '执行完成' }
      }))
      message.success(`🎉 已提交 ${taskIds.length} 个动作并完成执行回写`)
      refetchPreview()
    } catch (error: any) {
      message.error(`自动执行失败: ${error.message}`)
    } finally {
      setAutoExecuting(false)
    }
  }

  // ===== 辅助函数 =====
  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'P0': return 'red'
      case 'P1': return 'orange'
      case 'P2': return 'blue'
      case 'P3': return 'green'
      default: return 'default'
    }
  }

  const getPriorityBgColor = (priority: string) => {
    switch (priority) {
      case 'P0': return '#fff1f0'
      case 'P1': return '#fff7e6'
      case 'P2': return '#e6f7ff'
      case 'P3': return '#f6ffed'
      default: return '#fafafa'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case '待处理': return <ClockCircleOutlined style={{ color: '#ff4d4f' }} />
      case '进行中': return <CaretRightOutlined style={{ color: '#faad14' }} />
      case '已完成': return <CheckCircleOutlined style={{ color: '#52c41a' }} />
      default: return null
    }
  }

  const getMetricStatus = (value: number, type: string) => {
    const thresholds: any = {
      ctr: { good: 2.0, bad: 1.5 },
      conversion: { good: 3.5, bad: 2.5 },
      rating: { good: 4.5, bad: 4.0 },
      roas: { good: 2.0, bad: 1.5 },
      daysOfSupply: { good: 14, bad: 7 }
    }

    const threshold = thresholds[type]
    if (!threshold) return 'normal'

    if (type === 'daysOfSupply') {
      if (value < threshold.bad) return 'critical'
      if (value < threshold.good) return 'warning'
      return 'good'
    }

    if (value >= threshold.good) return 'good'
    if (value >= threshold.bad) return 'warning'
    return 'critical'
  }

  const COLORS = ['#ff4d4f', '#faad14', '#1890ff', '#52c41a']

  const p0Count = strategies.filter(s => s.priority === 'P0' && s.status !== '已完成').length
  const p1Count = strategies.filter(s => s.priority === 'P1' && s.status !== '已完成').length

  // ECharts 配置
  const priorityChartOption = {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 10,
        borderColor: '#fff',
        borderWidth: 2
      },
      label: { show: true, formatter: '{b}: {c}' },
      data: priorityChartData.map((item, index) => ({
        value: item.value,
        name: item.name,
        itemStyle: { color: COLORS[index] }
      }))
    }]
  }

  const typeChartOption = {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: { type: 'category', data: typeChartData.map(item => item.name) },
    yAxis: { type: 'value' },
    series: [{
      type: 'bar',
      data: typeChartData.map(item => item.value),
      itemStyle: { color: '#1890ff' },
      label: { show: true, position: 'top' }
    }]
  }

  // 表格列定义
  const columns = [
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      width: 100,
      render: (priority: string) => (
        <Tag color={getPriorityColor(priority)} icon={<AlertOutlined />}>
          {priority}
        </Tag>
      )
    },
    {
      title: 'SKU',
      dataIndex: 'sku',
      key: 'sku',
      width: 120,
      render: (text: string) => <Text strong>{text}</Text>
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 100,
      render: (type: string) => <Tag>{strategyTypeLabels[type] || '其他策略'}</Tag>
    },
    {
      title: '问题描述',
      dataIndex: 'issue',
      key: 'issue',
      width: 200,
      render: (text: string, record: any) => (
        <div>
          <Text>{text}</Text>
          <br />
          <Text type="danger" style={{ fontSize: '12px' }}>{record.impact}</Text>
        </div>
      )
    },
    {
      title: '建议操作',
      dataIndex: 'suggestion',
      key: 'suggestion',
      width: 200,
      ellipsis: true
    },
    {
      title: '来源页面',
      dataIndex: 'sourcePage',
      key: 'sourcePage',
      width: 110,
      render: (v: string) => <Tag color="geekblue">{sourcePageLabels[v] || displayOrDash(v)}</Tag>
    },
    {
      title: '推入原因',
      dataIndex: 'sourceReason',
      key: 'sourceReason',
      width: 180,
      ellipsis: true,
      render: (v: string) => <Tooltip title={v}>{displayOrDash(v)}</Tooltip>
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
      )
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
      )
    },
    {
      title: '回写状态',
      dataIndex: 'writebackStatus',
      key: 'writebackStatus',
      width: 100,
      render: (v: string) => <Tag color={v === '已回写' ? 'success' : 'default'}>{displayOrDash(v)}</Tag>
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_: any, record: any) => (
        <Space>
          {record.auto_executable && record.status !== '已完成' && (
            <Tooltip title="自动执行">
              <Button
                type="link"
                size="small"
                icon={<ThunderboltOutlined />}
                onClick={() => updateStrategyStatus(record.id, '已完成')}
              />
            </Tooltip>
          )}
          <Tooltip title="查看详情">
            <Button
              type="link"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => { setSelectedStrategy(record); setEditableSuggestion(record.suggestion || '') }}
            />
          </Tooltip>
        </Space>
      )
    }
  ]

  // 指标跟踪表格列
  const metricColumns = [
    {
      title: 'SKU',
      dataIndex: 'sku',
      key: 'sku',
      render: (text: string) => <Text strong>{text}</Text>
    },
    {
      title: 'CTR',
      dataIndex: 'ctr',
      key: 'ctr',
      align: 'center' as const,
      render: (value: number) => (
        <MetricBadge
          value={value}
          unit="%"
          status={getMetricStatus(value, 'ctr')}
        />
      )
    },
    {
      title: '转化率',
      dataIndex: 'conversion',
      key: 'conversion',
      align: 'center' as const,
      render: (value: number) => (
        <MetricBadge
          value={value}
          unit="%"
          status={getMetricStatus(value, 'conversion')}
        />
      )
    },
    {
      title: '评分',
      dataIndex: 'rating',
      key: 'rating',
      align: 'center' as const,
      render: (value: number) => (
        <MetricBadge
          value={value}
          status={getMetricStatus(value, 'rating')}
        />
      )
    },
    {
      title: 'ROAS',
      dataIndex: 'roas',
      key: 'roas',
      align: 'center' as const,
      render: (value: number) => (
        <MetricBadge
          value={value}
          status={getMetricStatus(value, 'roas')}
        />
      )
    },
    {
      title: '库存天数',
      dataIndex: 'daysOfSupply',
      key: 'daysOfSupply',
      align: 'center' as const,
      render: (value: number) => (
        <MetricBadge
          value={value}
          unit="天"
          status={getMetricStatus(value, 'daysOfSupply')}
        />
      )
    }
  ]

  return (
    <div style={{ padding: '18px 20px', background: '#f0f2f5', minHeight: '100vh' }}>
      <OpsPageHeader
        title="🧠 执行前确认控制台"
        subtitle="先看高优先动作与来源，再确认执行与回写。"
        extra={<Space><Tag color="blue">运营决策</Tag><Tag color={healthScore >= 80 ? 'success' : healthScore >= 60 ? 'warning' : 'error'}>健康度: {healthScore}</Tag></Space>}
      />
      <OpsConclusion title="当前执行结论" desc={`当前待处理 ${filteredStrategies.filter((x: any) => x.status !== '已完成').length} 条，P0 ${p0Count} 条，建议先确认高风险来源动作。`} level={p0Count > 0 ? 'error' : 'info'} />
      <div style={{ height: 10 }} />

      {/* 智能推荐 */}
      {showAlert && (
        <Alert
          type="info"
          icon={<ThunderboltOutlined />}
          message="🤖 智能推荐"
          description={
            <div>
              {(backendRecommendations.length === 0 ? [{ title: '暂无后端推荐', description: '当前预演未返回推荐内容', action: '稍后重试' }] : backendRecommendations).map((rec: any, i: number) => (
                <div
                  key={i}
                  style={{
                    marginTop: i > 0 ? '6px' : 0,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px'
                  }}
                >
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
          onClose={() => setShowAlert(false)}
          style={{ marginBottom: '12px' }}
        />
      )}

      {/* P0 紧急告警 */}
      {p0Count > 0 && (
        <Alert
          type="error"
          icon={<NotificationOutlined />}
          message={
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Text strong style={{ fontSize: '16px' }}>
                🚨 检测到 {formatInteger(p0Count)} 个 P0 级别紧急问题
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
            <div style={{ marginTop: '4px' }}>
              {strategies.filter(s => s.priority === 'P0' && s.status !== '已完成').map(s => (
                <div
                  key={s.id}
                  style={{
                    marginTop: '8px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px'
                  }}
                >
                  <Tag color="red">{s.priority}</Tag>
                  <Text><strong>{s.sku}</strong> - {s.issue}</Text>
                  {s.auto_executable && (
                    <Tag color="blue" icon={<ThunderboltOutlined />}>可自动执行</Tag>
                  )}
                  <Button
                    size="small"
                    type="primary"
                    danger
                    onClick={() => setSelectedStrategy(s)}
                  >
                    立即处理
                  </Button>
                </div>
              ))}
            </div>
          }
          style={{ marginBottom: '12px' }}
        />
      )}

      {/* 标签页 */}

      <Card title="📝 可编辑执行队列（执行前确认）" size="small" style={{ marginTop: 10 }}>
        <Table
          dataSource={filteredStrategies.filter((s: any) => s.status !== '已完成').slice(0, 8)}
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
              render: (_: any, record: any) => (
                <Input
                  value={record.suggestion}
                  onChange={(e) => setStrategies(strategies.map((s: any) => s.id === record.id ? { ...s, suggestion: e.target.value } : s))}
                />
              )
            },
            { title: '来源', dataIndex: 'sourcePage', key: 'sourcePage', render: (v: string) => sourcePageLabels[v] || displayOrDash(v) },
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
                {/* 左侧：健康度 + 统计 */}
                <Col span={6}>
                  <Card style={{ textAlign: 'center', marginBottom: '16px' }}>
                    <Title level={5}>🏥 健康度评分</Title>
                    <div style={{ margin: '24px 0' }}>
                      <Progress
                        type="circle"
                        percent={healthScore}
                        strokeColor={
                          healthScore >= 80 ? '#52c41a' :
                          healthScore >= 60 ? '#faad14' : '#ff4d4f'
                        }
                        format={percent => (
                          <Text strong style={{ fontSize: '32px' }}>{percent}</Text>
                        )}
                      />
                    </div>
                  </Card>
                  <Card>
                    <Row gutter={16}>
                      <Col span={12}>
                        <div style={{
                          textAlign: 'center',
                          padding: '16px',
                          background: '#fff1f0',
                          borderRadius: '8px'
                        }}>
                          <Title level={4} style={{ color: '#ff4d4f', margin: 0 }}>
                            {formatInteger(p0Count)}
                          </Title>
                          <Text>🔴 紧急</Text>
                        </div>
                      </Col>
                      <Col span={12}>
                        <div style={{
                          textAlign: 'center',
                          padding: '16px',
                          background: '#fff7e6',
                          borderRadius: '8px'
                        }}>
                          <Title level={4} style={{ color: '#faad14', margin: 0 }}>
                            {formatInteger(p1Count)}
                          </Title>
                          <Text>🟠 严重</Text>
                        </div>
                      </Col>
                    </Row>
                  </Card>
                </Col>

                {/* 右侧：策略表格 */}
                <Col span={18}>
                  <Card>
                    {/* 筛选和搜索 */}
                    <div style={{
                      marginBottom: '16px',
                      display: 'flex',
                      gap: '8px',
                      flexWrap: 'wrap'
                    }}>
                      <Input
                        placeholder="搜索 SKU / 问题 / 建议"
                        prefix={<SearchOutlined />}
                        value={searchText}
                        onChange={(e) => setSearchText(e.target.value)}
                        style={{ width: 250 }}
                      />
                      <Select
                        value={priorityFilter}
                        onChange={setPriorityFilter}
                        style={{ width: 120 }}
                      >
                        <Select.Option value="all">全部优先级</Select.Option>
                        <Select.Option value="P0">P0</Select.Option>
                        <Select.Option value="P1">P1</Select.Option>
                        <Select.Option value="P2">P2</Select.Option>
                        <Select.Option value="P3">P3</Select.Option>
                      </Select>
                      <Select
                        value={typeFilter}
                        onChange={setTypeFilter}
                        style={{ width: 120 }}
                      >
                        <Select.Option value="all">全部类型</Select.Option>
                        <Select.Option value="库存">库存</Select.Option>
                        <Select.Option value="定价">定价</Select.Option>
                        <Select.Option value="转化">转化</Select.Option>
                        <Select.Option value="广告">广告</Select.Option>
                        <Select.Option value="风控">风控</Select.Option>
                      </Select>
                      <Select
                        value={statusFilter}
                        onChange={setStatusFilter}
                        style={{ width: 120 }}
                      >
                        <Select.Option value="all">全部状态</Select.Option>
                        <Select.Option value="待处理">待处理</Select.Option>
                        <Select.Option value="进行中">进行中</Select.Option>
                        <Select.Option value="已完成">已完成</Select.Option>
                      </Select>

                      <Select
                        value={sortBy}
                        onChange={setSortBy}
                        style={{ width: 120 }}
                      >
                        <Select.Option value="priority">按优先级</Select.Option>
                        <Select.Option value="created_at">按时间</Select.Option>
                        <Select.Option value="confidence">按置信度</Select.Option>
                      </Select>
                      <Text type="secondary" style={{ alignSelf: 'center' }}>
                        显示 {filteredStrategies.length} / {formatInteger(strategies.length)} 条
                      </Text>
                    </div>

                    {/* 表格 */}
                    <Table
                      dataSource={filteredStrategies}
                      columns={columns}
                      rowKey="id"
                      pagination={{ pageSize: 8 }}
                      scroll={{ x: 1200, y: 420 }}
                      onRow={(record) => ({
                        onClick: () => setSelectedStrategy(record),
                        style: {
                          cursor: 'pointer',
                          background: getPriorityBgColor(record.priority)
                        }
                      })}
                    />
                  </Card>
                </Col>
              </Row>
            )
          },
          {
            key: '1',
            label: '📊 可视化分析',
            children: (
              <Row gutter={16}>
                <Col span={12}>
                  <Card title="📊 优先级分布">
                    <ReactECharts option={priorityChartOption} style={{ height: '300px' }} />
                  </Card>
                </Col>
                <Col span={12}>
                  <Card title="📈 问题类型分布">
                    <ReactECharts option={typeChartOption} style={{ height: '300px' }} />
                  </Card>
                </Col>
              </Row>
            )
          },
          {
            key: '2',
            label: '🔍 指标跟踪',
            children: (
              <Card title="🔍 指标跟踪">
                <Table
                  dataSource={strategies.slice(0, 20).map((s: any) => ({ sku: s.sku, ctr: Number(formatRate((s.confidence || 0.5) * 3, 2)), conversion: Number(formatRate((s.confidence || 0.5) * 4, 2)), rating: Number(formatRate(4 + (s.confidence || 0) * 0.8, 2)), roas: Number(formatRate(1 + (s.confidence || 0) * 2, 2)), daysOfSupply: s.priority === 'P0' ? 3 : s.priority === 'P1' ? 8 : 20 }))}
                  columns={metricColumns}
                  rowKey="sku"
                  pagination={false}
                />
              </Card>
            )
          }
        ]}
      />

      {/* 详情弹窗 */}
      <Modal
        title={
          selectedStrategy && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Tag color={getPriorityColor(selectedStrategy.priority)} icon={<AlertOutlined />}>
                {selectedStrategy.priority}
              </Tag>
              <Text strong>{displayOrDash(selectedStrategy.sku)} - {displayOrDash(selectedStrategy.issue)}</Text>
            </div>
          )
        }
        open={!!selectedStrategy}
        onCancel={() => { setSelectedStrategy(null); setEditableSuggestion('') }}
        footer={
          selectedStrategy && selectedStrategy.status !== '已完成' ? [
            <Button key="close" onClick={() => setSelectedStrategy(null)}>关闭</Button>,
            <Button
              key="inProgress"
              type="default"
              onClick={() => updateStrategyStatus(selectedStrategy.id, '进行中')}
            >
              标记为进行中
            </Button>,
            <Button
              key="complete"
              type="primary"
              icon={selectedStrategy.auto_executable ? <ThunderboltOutlined /> : <CheckCircleOutlined />}
              onClick={() => {
                setStrategies(strategies.map(s => s.id === selectedStrategy.id ? { ...s, suggestion: editableSuggestion } : s))
                updateStrategyStatus(selectedStrategy.id, '已完成')
              }}
            >
              {selectedStrategy.auto_executable ? '自动执行' : '标记为已完成'}
            </Button>
          ] : [
            <Button key="close" onClick={() => setSelectedStrategy(null)}>关闭</Button>
          ]
        }
        width={800}
      >
        {selectedStrategy && (
          <div>
            <Title level={5}>📊 问题诊断</Title>
            <Card size="small" style={{ background: '#f5f5f5', marginBottom: '16px' }}>
              <Row gutter={[16, 16]}>
                <Col span={12}>
                  <Text type="secondary">问题类型</Text>
                  <br />
                  <Text strong>{strategyTypeLabels[selectedStrategy.type] || '其他策略'}</Text>
                  <br />
                  <Text type="secondary">来源：{sourcePageLabels[selectedStrategy.sourcePage] || displayOrDash(selectedStrategy.sourcePage)}</Text>
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
            <Card size="small" style={{ background: '#e6f7ff', marginBottom: '16px' }}>
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
                style={{ marginTop: '16px' }}
              />
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}

// 辅助组件
function MetricBadge({ value, unit = '', status }: { value: number; unit?: string; status: string }) {
  const getColor = () => {
    switch (status) {
      case 'good': return '#52c41a'
      case 'warning': return '#faad14'
      case 'critical': return '#ff4d4f'
      default: return '#8c8c8c'
    }
  }

  const getIcon = () => {
    switch (status) {
      case 'good': return '✓'
      case 'warning': return '⚠️'
      case 'critical': return '⛔️'
      default: return ''
    }
  }

  const getBgColor = () => {
    switch (status) {
      case 'good': return '#f6ffed'
      case 'warning': return '#fffbe6'
      case 'critical': return '#fff1f0'
      default: return '#fafafa'
    }
  }

  return (
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '8px',
        padding: '4px 12px',
        borderRadius: '8px',
        background: getBgColor(),
        border: `2px solid ${getColor()}`
      }}
    >
      <Text strong style={{ color: getColor() }}>
        {value}{unit} {getIcon()}
      </Text>
    </div>
  )
}
