import { useMemo, useState } from 'react'
import { Alert, Button, Card, Col, Descriptions, Drawer, Input, Row, Space, Statistic, Table, Tag, Timeline, Typography, message } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'

import {
  actionQueueApi,
  type ActionBulkCommandDetailResponse,
  type ActionBulkCommandHistoryResponse,
  type ActionBulkCommandLineageSummaryResponse,
  type ActionBulkCommandRelatedResponse,
  type ActionBulkCommandResponse,
  type ActionBulkCommandTimelineResponse,
  type ActionDashboardResponse,
  type ActionFailureBucketsResponse,
  type ActionJobAuditResponse,
  type ActionJobDetailResponse,
  type ActionJobEventsResponse,
  type ActionJobRecord,
  type ActionMetricsResponse,
  type ActionStoreOverviewResponse,
  type ActionWorkerCommandAuditDetailResponse,
  type ActionWorkerCommandAuditResponse,
  type ActionWorkerLeaseAuditResponse,
  type ActionWorkerOverviewResponse,
  type ActionWorkerStaleResponse,
} from '../../services/actionQueue'

function renderStatusTag(value?: string | null) {
  if (!value) return <Tag>—</Tag>
  const color =
    value === 'succeeded'
      ? 'green'
      : value === 'failed'
      ? 'red'
      : value === 'dead_letter'
      ? 'magenta'
      : value === 'running'
      ? 'blue'
      : value === 'queued'
      ? 'gold'
      : 'default'
  return <Tag color={color}>{value}</Tag>
}

function renderSummaryCards(summary?: Record<string, number>) {
  if (!summary) return null
  return (
    <Row gutter={[12, 12]}>
      {Object.entries(summary).map(([key, value]) => (
        <Col xs={12} md={8} xl={6} key={key}>
          <Card size="small">
            <Statistic title={key} value={value} />
          </Card>
        </Col>
      ))}
    </Row>
  )
}

export default function ActionJobsPage() {
  const [batchRef, setBatchRef] = useState<string>('')
  const [selectedJobId, setSelectedJobId] = useState<string>()
  const [selectedAuditEventId, setSelectedAuditEventId] = useState<string>()
  const [selectedStaleJobIds, setSelectedStaleJobIds] = useState<Array<string | number>>([])
  const [auditWorkerId, setAuditWorkerId] = useState<string>('')
  const [auditEventType, setAuditEventType] = useState<string>('')
  const [auditActionCode, setAuditActionCode] = useState<string>('')
  const [lastBulkResult, setLastBulkResult] = useState<ActionBulkCommandResponse>()
  const [selectedBulkCommandId, setSelectedBulkCommandId] = useState<string>()
  const [bulkHistoryCommand, setBulkHistoryCommand] = useState<string>('')
  const [bulkHistoryWorkerId, setBulkHistoryWorkerId] = useState<string>('')
  const [bulkHistoryActionCode, setBulkHistoryActionCode] = useState<string>('')
  const [bulkHistoryResultMode, setBulkHistoryResultMode] = useState<string>('')
  const [bulkHistoryParentBulkCommandId, setBulkHistoryParentBulkCommandId] = useState<string>('')
  const [bulkHistoryHasChildren, setBulkHistoryHasChildren] = useState<string>('')
  const [bulkHistoryLineageDepth, setBulkHistoryLineageDepth] = useState<string>('')
  const [bulkHistorySelection, setBulkHistorySelection] = useState<string>('')
  const [bulkHistoryReexecuteCommand, setBulkHistoryReexecuteCommand] = useState<string>('')
  const [bulkHistoryCommandMode, setBulkHistoryCommandMode] = useState<string>('')
  const [bulkHistorySourceBulkCommandId, setBulkHistorySourceBulkCommandId] = useState<string>('')
  const [bulkHistoryOffset, setBulkHistoryOffset] = useState<number>(0)
  const [bulkTimelineEventType, setBulkTimelineEventType] = useState<string>('')
  const [bulkTimelineCommand, setBulkTimelineCommand] = useState<string>('')
  const [bulkTimelineActionCode, setBulkTimelineActionCode] = useState<string>('')
  const [bulkTimelineLineageDepth, setBulkTimelineLineageDepth] = useState<string>('')
  const [bulkTimelineCommandMode, setBulkTimelineCommandMode] = useState<string>('')
  const [bulkTimelineSourceBulkCommandId, setBulkTimelineSourceBulkCommandId] = useState<string>('')
  const [messageApi, contextHolder] = message.useMessage()
  const normalizedBatchRef = batchRef.trim() || undefined
  const normalizedAuditWorkerId = auditWorkerId.trim() || undefined
  const normalizedAuditEventType = auditEventType.trim() || undefined
  const normalizedAuditActionCode = auditActionCode.trim() || undefined
  const normalizedBulkHistoryCommand = bulkHistoryCommand.trim() || undefined
  const normalizedBulkHistoryWorkerId = bulkHistoryWorkerId.trim() || undefined
  const normalizedBulkHistoryActionCode = bulkHistoryActionCode.trim() || undefined
  const normalizedBulkHistoryResultMode = bulkHistoryResultMode.trim() || undefined
  const normalizedBulkHistoryParentBulkCommandId = bulkHistoryParentBulkCommandId.trim() || undefined
  const normalizedBulkHistoryHasChildren = bulkHistoryHasChildren.trim() || undefined
  const normalizedBulkHistoryLineageDepth = bulkHistoryLineageDepth.trim() ? Number(bulkHistoryLineageDepth.trim()) : undefined
  const normalizedBulkHistorySelection = bulkHistorySelection.trim() || undefined
  const normalizedBulkHistoryReexecuteCommand = bulkHistoryReexecuteCommand.trim() || undefined
  const normalizedBulkHistoryCommandMode = bulkHistoryCommandMode.trim() || undefined
  const normalizedBulkHistorySourceBulkCommandId = bulkHistorySourceBulkCommandId.trim() || undefined
  const normalizedBulkTimelineEventType = bulkTimelineEventType.trim() || undefined
  const normalizedBulkTimelineCommand = bulkTimelineCommand.trim() || undefined
  const normalizedBulkTimelineActionCode = bulkTimelineActionCode.trim() || undefined
  const normalizedBulkTimelineLineageDepth = bulkTimelineLineageDepth.trim() ? Number(bulkTimelineLineageDepth.trim()) : undefined
  const normalizedBulkTimelineCommandMode = bulkTimelineCommandMode.trim() || undefined
  const normalizedBulkTimelineSourceBulkCommandId = bulkTimelineSourceBulkCommandId.trim() || undefined

  const dashboardQuery = useQuery<ActionDashboardResponse>({
    queryKey: ['action-jobs-dashboard', normalizedBatchRef],
    queryFn: () => actionQueueApi.getDashboard(normalizedBatchRef),
    staleTime: 30_000,
  })

  const metricsQuery = useQuery<ActionMetricsResponse>({
    queryKey: ['action-jobs-metrics', normalizedBatchRef],
    queryFn: () => actionQueueApi.getMetrics(normalizedBatchRef),
    staleTime: 30_000,
  })

  const failureQuery = useQuery<ActionFailureBucketsResponse>({
    queryKey: ['action-jobs-failure', normalizedBatchRef],
    queryFn: () => actionQueueApi.getFailureBuckets(normalizedBatchRef),
    staleTime: 30_000,
  })

  const workerQuery = useQuery<ActionWorkerOverviewResponse>({
    queryKey: ['action-jobs-worker', normalizedBatchRef],
    queryFn: () => actionQueueApi.getWorkerOverview(normalizedBatchRef),
    staleTime: 15_000,
  })

  const staleQuery = useQuery<ActionWorkerStaleResponse>({
    queryKey: ['action-jobs-stale', normalizedBatchRef],
    queryFn: () => actionQueueApi.getWorkerStaleJobs(normalizedBatchRef),
    staleTime: 15_000,
  })

  const storeQuery = useQuery<ActionStoreOverviewResponse>({
    queryKey: ['action-jobs-store', normalizedBatchRef],
    queryFn: () => actionQueueApi.getStoreOverview(normalizedBatchRef),
    staleTime: 30_000,
  })

  const leaseAuditQuery = useQuery<ActionWorkerLeaseAuditResponse>({
    queryKey: ['action-jobs-lease-audit', normalizedBatchRef, normalizedAuditWorkerId, normalizedAuditEventType, normalizedAuditActionCode],
    queryFn: () => actionQueueApi.getWorkerLeaseAudit(normalizedBatchRef, {
      workerId: normalizedAuditWorkerId,
      eventType: normalizedAuditEventType,
      actionCode: normalizedAuditActionCode,
    }),
    staleTime: 15_000,
  })

  const commandAuditQuery = useQuery<ActionWorkerCommandAuditResponse>({
    queryKey: ['action-jobs-command-audit', normalizedBatchRef, normalizedAuditWorkerId, normalizedAuditEventType, normalizedAuditActionCode],
    queryFn: () => actionQueueApi.getWorkerCommandAudit(normalizedBatchRef, {
      workerId: normalizedAuditWorkerId,
      eventType: normalizedAuditEventType,
      actionCode: normalizedAuditActionCode,
    }),
    staleTime: 15_000,
  })

  const commandAuditDetailQuery = useQuery<ActionWorkerCommandAuditDetailResponse>({
    queryKey: ['action-jobs-command-audit-detail', selectedAuditEventId],
    queryFn: () => actionQueueApi.getWorkerCommandAuditDetail(selectedAuditEventId as string),
    enabled: Boolean(selectedAuditEventId),
    staleTime: 15_000,
  })

  const bulkHistoryQuery = useQuery<ActionBulkCommandHistoryResponse>({
    queryKey: ['action-jobs-bulk-history', normalizedBatchRef, normalizedBulkHistoryCommand, normalizedBulkHistoryWorkerId, normalizedBulkHistoryActionCode, normalizedBulkHistoryResultMode, normalizedBulkHistoryParentBulkCommandId, normalizedBulkHistoryHasChildren, normalizedBulkHistoryLineageDepth, normalizedBulkHistorySelection, normalizedBulkHistoryReexecuteCommand, normalizedBulkHistoryCommandMode, normalizedBulkHistorySourceBulkCommandId, bulkHistoryOffset],
    queryFn: () => actionQueueApi.getBulkCommandHistory({ batchRef: normalizedBatchRef, command: normalizedBulkHistoryCommand, workerId: normalizedBulkHistoryWorkerId, actionCode: normalizedBulkHistoryActionCode, resultMode: normalizedBulkHistoryResultMode, parentBulkCommandId: normalizedBulkHistoryParentBulkCommandId, hasChildren: normalizedBulkHistoryHasChildren, lineageDepth: normalizedBulkHistoryLineageDepth, selection: normalizedBulkHistorySelection, reexecuteCommand: normalizedBulkHistoryReexecuteCommand, commandMode: normalizedBulkHistoryCommandMode, sourceBulkCommandId: normalizedBulkHistorySourceBulkCommandId, offset: bulkHistoryOffset, limit: 10 }),
    staleTime: 15_000,
  })

  const bulkDetailQuery = useQuery<ActionBulkCommandDetailResponse>({
    queryKey: ['action-jobs-bulk-detail', selectedBulkCommandId],
    queryFn: () => actionQueueApi.getBulkCommandDetail(selectedBulkCommandId as string),
    enabled: Boolean(selectedBulkCommandId),
    staleTime: 15_000,
  })

  const bulkRelatedQuery = useQuery<ActionBulkCommandRelatedResponse>({
    queryKey: ['action-jobs-bulk-related', selectedBulkCommandId],
    queryFn: () => actionQueueApi.getBulkCommandRelated(selectedBulkCommandId as string),
    enabled: Boolean(selectedBulkCommandId),
    staleTime: 15_000,
  })

  const bulkTimelineQuery = useQuery<ActionBulkCommandTimelineResponse>({
    queryKey: ['action-jobs-bulk-timeline', selectedBulkCommandId, normalizedBulkTimelineEventType, normalizedBulkTimelineCommand, normalizedBulkTimelineActionCode, normalizedBulkTimelineLineageDepth, normalizedBulkTimelineCommandMode, normalizedBulkTimelineSourceBulkCommandId],
    queryFn: () => actionQueueApi.getBulkCommandTimeline(selectedBulkCommandId as string, { eventType: normalizedBulkTimelineEventType, command: normalizedBulkTimelineCommand, actionCode: normalizedBulkTimelineActionCode, lineageDepth: normalizedBulkTimelineLineageDepth, commandMode: normalizedBulkTimelineCommandMode, sourceBulkCommandId: normalizedBulkTimelineSourceBulkCommandId, limit: 20 }),
    enabled: Boolean(selectedBulkCommandId),
    staleTime: 15_000,
  })

  const bulkLineageSummaryQuery = useQuery<ActionBulkCommandLineageSummaryResponse>({
    queryKey: ['action-jobs-bulk-lineage-summary', selectedBulkCommandId, normalizedBulkTimelineEventType, normalizedBulkTimelineActionCode, normalizedBulkTimelineLineageDepth, normalizedBulkTimelineCommandMode, normalizedBulkTimelineSourceBulkCommandId, normalizedBulkHistorySelection, normalizedBulkHistoryReexecuteCommand],
    queryFn: () => actionQueueApi.getBulkCommandLineageSummary(selectedBulkCommandId as string, { eventType: normalizedBulkTimelineEventType, actionCode: normalizedBulkTimelineActionCode, lineageDepth: normalizedBulkTimelineLineageDepth, commandMode: normalizedBulkTimelineCommandMode, sourceBulkCommandId: normalizedBulkTimelineSourceBulkCommandId, selection: normalizedBulkHistorySelection, reexecuteCommand: normalizedBulkHistoryReexecuteCommand, limit: 10 }),
    enabled: Boolean(selectedBulkCommandId),
    staleTime: 15_000,
  })

  const jobDetailQuery = useQuery<ActionJobDetailResponse>({
    queryKey: ['action-jobs-detail', selectedJobId],
    queryFn: () => actionQueueApi.getJobDetail(selectedJobId as string),
    enabled: Boolean(selectedJobId),
    staleTime: 15_000,
  })

  const jobEventsQuery = useQuery<ActionJobEventsResponse>({
    queryKey: ['action-jobs-events', selectedJobId],
    queryFn: () => actionQueueApi.getJobEvents(selectedJobId as string),
    enabled: Boolean(selectedJobId),
    staleTime: 15_000,
  })

  const jobAuditQuery = useQuery<ActionJobAuditResponse>({
    queryKey: ['action-jobs-audit', selectedJobId],
    queryFn: () => actionQueueApi.getJobAudit(selectedJobId as string),
    enabled: Boolean(selectedJobId),
    staleTime: 15_000,
  })

  const isLoading =
    dashboardQuery.isLoading ||
    metricsQuery.isLoading ||
    failureQuery.isLoading ||
    workerQuery.isLoading ||
    staleQuery.isLoading ||
    storeQuery.isLoading ||
    leaseAuditQuery.isLoading ||
    commandAuditQuery.isLoading ||
    bulkHistoryQuery.isLoading

  const errorText = useMemo(() => {
    return [dashboardQuery.error, metricsQuery.error, failureQuery.error, workerQuery.error, staleQuery.error, storeQuery.error, leaseAuditQuery.error, commandAuditQuery.error, bulkHistoryQuery.error]
      .filter(Boolean)
      .map((item) => (item instanceof Error ? item.message : '动作队列读取失败'))
      .join('；')
  }, [dashboardQuery.error, failureQuery.error, leaseAuditQuery.error, commandAuditQuery.error, bulkHistoryQuery.error, metricsQuery.error, staleQuery.error, storeQuery.error, workerQuery.error])

  const applyBulkLinkedFilters = (mode: 'history' | 'timeline', payload?: Record<string, unknown> | null) => {
    const filters = (payload || {}) as Record<string, unknown>
    if (mode === 'history') {
      setBulkHistoryOffset(0)
      setBulkHistoryParentBulkCommandId(String(filters.parentBulkCommandId || ''))
      setBulkHistorySourceBulkCommandId(String(filters.sourceBulkCommandId || filters.focusBulkCommandId || ''))
      setBulkHistoryLineageDepth(filters.lineageDepth !== undefined && filters.lineageDepth !== null ? String(filters.lineageDepth) : '')
      setBulkHistoryCommandMode(String(filters.commandMode || ''))
      setBulkHistorySelection(String(filters.selection || ''))
      setBulkHistoryReexecuteCommand(String(filters.reexecuteCommand || ''))
    } else {
      setBulkTimelineSourceBulkCommandId(String(filters.sourceBulkCommandId || filters.focusBulkCommandId || ''))
      if (filters.lineageDepth !== undefined && filters.lineageDepth !== null) {
        setBulkTimelineLineageDepth(String(filters.lineageDepth))
      }
      if (filters.commandMode !== undefined) {
        setBulkTimelineCommandMode(String(filters.commandMode || ''))
      }
      if (filters.actionCode !== undefined) {
        setBulkTimelineActionCode(String(filters.actionCode || ''))
      }
      if (filters.eventType !== undefined) {
        setBulkTimelineEventType(String(filters.eventType || ''))
      }
    }
  }

  const refreshAll = async () => {
    await Promise.all([
      dashboardQuery.refetch(),
      metricsQuery.refetch(),
      failureQuery.refetch(),
      workerQuery.refetch(),
      staleQuery.refetch(),
      storeQuery.refetch(),
      leaseAuditQuery.refetch(),
      commandAuditQuery.refetch(),
      bulkHistoryQuery.refetch(),
      bulkDetailQuery.refetch(),
      bulkRelatedQuery.refetch(),
      bulkTimelineQuery.refetch(),
      bulkLineageSummaryQuery.refetch(),
      commandAuditDetailQuery.refetch(),
      jobDetailQuery.refetch(),
      jobEventsQuery.refetch(),
      jobAuditQuery.refetch(),
    ])
  }

  const releaseStaleJobs = async () => {
    try {
      const payload = await actionQueueApi.releaseStaleJobs(normalizedBatchRef)
      messageApi.success(`已释放 stale 作业 ${payload.summary?.releasedJobs ?? 0} 个`)
      await refreshAll()
    } catch (error) {
      const text = error instanceof Error ? error.message : 'stale 作业释放失败'
      messageApi.error(text)
    }
  }

  const releaseSelectedStaleJobs = async () => {
    const jobIds = selectedStaleJobIds.map((item) => String(item)).filter(Boolean)
    if (!jobIds.length) {
      messageApi.warning('请先选择要释放的 stale 作业')
      return
    }
    try {
      const payload: ActionBulkCommandResponse = await actionQueueApi.executeBulkCommand('release-lease', jobIds, { reason: 'frontend_bulk_release_stale' })
      setLastBulkResult(payload)
      messageApi.success(`批量释放完成：成功 ${payload.summary?.succeededJobs ?? 0} 个，失败 ${payload.summary?.failedJobs ?? 0} 个`)
      setSelectedStaleJobIds([])
      await refreshAll()
    } catch (error) {
      const text = error instanceof Error ? error.message : '批量释放 stale 作业失败'
      messageApi.error(text)
    }
  }

  const rerunBulkHistory = async (command: string) => {
    if (!selectedBulkCommandId) {
      messageApi.warning('请先选择一个批量命令历史')
      return
    }
    try {
      const payload = await actionQueueApi.reexecuteBulkCommand(selectedBulkCommandId, {
        selection: 'failed',
        command,
        reason: `frontend_reexecute_${command}`,
      })
      setLastBulkResult(payload)
      setSelectedBulkCommandId(String(payload.bulkCommandId || selectedBulkCommandId))
      messageApi.success(`历史失败项再执行完成：成功 ${payload.summary?.succeededJobs ?? 0} 个，失败 ${payload.summary?.failedJobs ?? 0} 个`)
      await refreshAll()
    } catch (error) {
      const text = error instanceof Error ? error.message : '历史失败项再执行失败'
      messageApi.error(text)
    }
  }

  const rerunBulkHistoryAcrossLineage = async (command: string) => {
    if (!selectedBulkCommandId) {
      messageApi.warning('请先选择一个批量命令历史')
      return
    }
    try {
      const payload = await actionQueueApi.executeLineageBulkCommand(selectedBulkCommandId, {
        selection: 'failed',
        command,
        scope: 'entire_lineage',
        reason: `frontend_lineage_reexecute_${command}`,
      })
      setLastBulkResult(payload)
      setSelectedBulkCommandId(String(payload.bulkCommandId || selectedBulkCommandId))
      messageApi.success(`lineage 失败项批量执行完成：成功 ${payload.summary?.succeededJobs ?? 0} 个，失败 ${payload.summary?.failedJobs ?? 0} 个`)
      await refreshAll()
    } catch (error) {
      const text = error instanceof Error ? error.message : 'lineage 失败项批量执行失败'
      messageApi.error(text)
    }
  }

  const jobColumns = [
    {
      title: '作业',
      key: 'job',
      render: (_: unknown, row: ActionJobRecord) => (
        <Space direction="vertical" size={0}>
          <Typography.Text strong>{row.jobId}</Typography.Text>
          <Typography.Text type="secondary">{row.requestId || '—'}</Typography.Text>
        </Space>
      ),
    },
    {
      title: '状态',
      key: 'status',
      render: (_: unknown, row: ActionJobRecord) => (
        <Space wrap>
          {renderStatusTag(row.jobStatus)}
          {renderStatusTag(row.queueStatus)}
        </Space>
      ),
    },
    { title: '动作', dataIndex: 'actionCode', key: 'actionCode' },
    { title: '批次', dataIndex: 'batchRef', key: 'batchRef' },
    { title: 'Worker', dataIndex: 'workerId', key: 'workerId', render: (value: string | null | undefined) => value || '—' },
    {
      title: '推荐操作',
      dataIndex: 'recommendedOperation',
      key: 'recommendedOperation',
      render: (value: string | null | undefined) => (value ? <Tag color="purple">{value}</Tag> : '—'),
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      {contextHolder}
      <Alert
        type="info"
        showIcon
        message="动作队列看板 / Tracking"
        description="本页连接 P5.8 Action Async Queue 查询面，用于查看 summary、metrics、failure buckets、worker/store skeleton，并支持作业 drill-down。"
        style={{ marginBottom: 16 }}
      />

      <Card
        title="筛选"
        style={{ marginBottom: 16 }}
        extra={
          <Space>
            <Button onClick={releaseStaleJobs}>释放过期租约</Button>
            <Button onClick={releaseSelectedStaleJobs}>释放选中 stale</Button>
            <Button icon={<ReloadOutlined />} onClick={refreshAll}>刷新</Button>
          </Space>
        }
      >
        <Space wrap>
          <Input
            placeholder="按 batchRef 过滤，例如 batch-r8"
            style={{ width: 320 }}
            value={batchRef}
            onChange={(event) => setBatchRef(event.target.value)}
            allowClear
          />
          <Typography.Text type="secondary">当前过滤：{normalizedBatchRef || '全部批次'}</Typography.Text>
        </Space>
      </Card>

      <Card title="审计筛选" size="small" style={{ marginBottom: 16 }}>
        <Space wrap>
          <Input
            placeholder="workerId 过滤"
            style={{ width: 180 }}
            value={auditWorkerId}
            onChange={(event) => setAuditWorkerId(event.target.value)}
            allowClear
          />
          <Input
            placeholder="eventType 过滤"
            style={{ width: 220 }}
            value={auditEventType}
            onChange={(event) => setAuditEventType(event.target.value)}
            allowClear
          />
          <Input
            placeholder="actionCode 过滤"
            style={{ width: 180 }}
            value={auditActionCode}
            onChange={(event) => setAuditActionCode(event.target.value)}
            allowClear
          />
          <Typography.Text type="secondary">筛选会同时作用于 lease audit 与 command audit。</Typography.Text>
        </Space>
      </Card>

      {lastBulkResult ? (
        <Card title="最近批量命令结果" size="small" style={{ marginBottom: 16 }}>
          <Descriptions column={1} size="small" style={{ marginBottom: 12 }}>
            <Descriptions.Item label="命令">{lastBulkResult.command || '—'}</Descriptions.Item>
            <Descriptions.Item label="请求/成功/失败">{lastBulkResult.summary?.requestedJobs ?? 0} / {lastBulkResult.summary?.succeededJobs ?? 0} / {lastBulkResult.summary?.failedJobs ?? 0}</Descriptions.Item>
            <Descriptions.Item label="结果状态汇总">
              <Space wrap>
                {Object.entries(lastBulkResult.itemStatusSummary || {}).map(([key, value]) => (
                  <Tag key={key} color="blue">{key}: {value}</Tag>
                ))}
              </Space>
            </Descriptions.Item>
            <Descriptions.Item label="失败原因汇总">
              <Space wrap>
                {Object.entries(lastBulkResult.errorReasonSummary || {}).map(([key, value]) => (
                  <Tag key={key} color="red">{key}: {value}</Tag>
                ))}
              </Space>
            </Descriptions.Item>
          </Descriptions>
          <Row gutter={[16, 16]}>
            <Col xs={24} xl={12}>
              <Table<ActionJobRecord>
                rowKey={(row) => row.jobId}
                dataSource={lastBulkResult.items || []}
                size="small"
                pagination={false}
                scroll={{ x: 720 }}
                onRow={(row) => ({ onClick: () => { setSelectedAuditEventId(undefined); setSelectedJobId(row.jobId) } })}
                columns={jobColumns}
              />
            </Col>
            <Col xs={24} xl={12}>
              <Table<Record<string, unknown>>
                rowKey={(row) => `${String(row.jobId || '')}-${String(row.reason || '')}`}
                dataSource={lastBulkResult.errors || []}
                size="small"
                pagination={false}
                locale={{ emptyText: '没有失败明细' }}
                columns={[
                  { title: '作业', dataIndex: 'jobId', key: 'jobId' },
                  { title: '原因', dataIndex: 'reason', key: 'reason', render: (value: unknown) => <Tag color="red">{String(value || '—')}</Tag> },
                ]}
              />
            </Col>
          </Row>
        </Card>
      ) : null}

      {errorText ? <Alert type="warning" showIcon message="动作队列接口读取失败" description={errorText} style={{ marginBottom: 16 }} /> : null}

      <Card title="批量命令历史" loading={bulkHistoryQuery.isLoading} style={{ marginBottom: 16 }}>
        <Space wrap style={{ marginBottom: 12 }}>
          <Input placeholder="筛选命令" value={bulkHistoryCommand} onChange={(e) => { setBulkHistoryOffset(0); setBulkHistoryCommand(e.target.value) }} style={{ width: 140 }} />
          <Input placeholder="筛选 Worker" value={bulkHistoryWorkerId} onChange={(e) => { setBulkHistoryOffset(0); setBulkHistoryWorkerId(e.target.value) }} style={{ width: 140 }} />
          <Input placeholder="筛选动作" value={bulkHistoryActionCode} onChange={(e) => { setBulkHistoryOffset(0); setBulkHistoryActionCode(e.target.value) }} style={{ width: 140 }} />
          <Input placeholder="结果模式 succeeded/partial/failed" value={bulkHistoryResultMode} onChange={(e) => { setBulkHistoryOffset(0); setBulkHistoryResultMode(e.target.value) }} style={{ width: 220 }} />
          <Input placeholder="父结果 bulkCommandId" value={bulkHistoryParentBulkCommandId} onChange={(e) => { setBulkHistoryOffset(0); setBulkHistoryParentBulkCommandId(e.target.value) }} style={{ width: 180 }} />
          <Input placeholder="hasChildren true/false" value={bulkHistoryHasChildren} onChange={(e) => { setBulkHistoryOffset(0); setBulkHistoryHasChildren(e.target.value) }} style={{ width: 160 }} />
          <Input placeholder="depth 0/1/2" value={bulkHistoryLineageDepth} onChange={(e) => { setBulkHistoryOffset(0); setBulkHistoryLineageDepth(e.target.value) }} style={{ width: 120 }} />
          <Input placeholder="selection failed/all/succeeded" value={bulkHistorySelection} onChange={(e) => { setBulkHistoryOffset(0); setBulkHistorySelection(e.target.value) }} style={{ width: 220 }} />
          <Input placeholder="reexecuteCommand" value={bulkHistoryReexecuteCommand} onChange={(e) => { setBulkHistoryOffset(0); setBulkHistoryReexecuteCommand(e.target.value) }} style={{ width: 180 }} />
          <Input placeholder="commandMode direct/reexecute/lineage" value={bulkHistoryCommandMode} onChange={(e) => { setBulkHistoryOffset(0); setBulkHistoryCommandMode(e.target.value) }} style={{ width: 220 }} />
          <Input placeholder="sourceBulkCommandId" value={bulkHistorySourceBulkCommandId} onChange={(e) => { setBulkHistoryOffset(0); setBulkHistorySourceBulkCommandId(e.target.value) }} style={{ width: 180 }} />
          <Button onClick={() => { setBulkHistoryOffset(0); setBulkHistoryCommand(''); setBulkHistoryWorkerId(''); setBulkHistoryActionCode(''); setBulkHistoryResultMode(''); setBulkHistoryParentBulkCommandId(''); setBulkHistoryHasChildren(''); setBulkHistoryLineageDepth(''); setBulkHistorySelection(''); setBulkHistoryReexecuteCommand(''); setBulkHistoryCommandMode(''); setBulkHistorySourceBulkCommandId('') }}>清空筛选</Button>
        </Space>
        <Descriptions column={1} size="small" style={{ marginBottom: 12 }}>
          <Descriptions.Item label="历史命令总数">{bulkHistoryQuery.data?.summary?.totalCommands ?? 0}</Descriptions.Item>
          <Descriptions.Item label="命令类型汇总">
            <Space wrap>
              {Object.entries(bulkHistoryQuery.data?.commandSummary || {}).map(([key, value]) => (
                <Tag key={key} color="geekblue">{key}: {value}</Tag>
              ))}
            </Space>
          </Descriptions.Item>
          <Descriptions.Item label="结果模式汇总">
            <Space wrap>
              {Object.entries(bulkHistoryQuery.data?.resultModeSummary || {}).map(([key, value]) => (
                <Tag key={key} color={key === 'failed' ? 'red' : key === 'partial' ? 'orange' : 'green'}>{key}: {value}</Tag>
              ))}
            </Space>
          </Descriptions.Item>
          <Descriptions.Item label="Lineage 汇总">
            <Space wrap>
              {Object.entries((bulkHistoryQuery.data as Record<string, any> | undefined)?.lineageSummary || {}).map(([key, value]) => (
                <Tag key={key} color="cyan">{key}: {String(value)}</Tag>
              ))}
            </Space>
          </Descriptions.Item>
          <Descriptions.Item label="Selection 汇总">
            <Space wrap>
              {Object.entries((bulkHistoryQuery.data?.selectionSummary || {})).map(([key, value]) => (
                <Tag key={key} color="gold">{key}: {String(value)}</Tag>
              ))}
            </Space>
          </Descriptions.Item>
          <Descriptions.Item label="Re-execute 命令汇总">
            <Space wrap>
              {Object.entries((bulkHistoryQuery.data?.reexecuteCommandSummary || {})).map(([key, value]) => (
                <Tag key={key} color="volcano">{key}: {String(value)}</Tag>
              ))}
            </Space>
          </Descriptions.Item>
          <Descriptions.Item label="Command Mode 汇总">
            <Space wrap>
              {Object.entries((bulkHistoryQuery.data?.commandModeSummary || {})).map(([key, value]) => (
                <Tag key={key} color="purple">{key}: {String(value)}</Tag>
              ))}
            </Space>
          </Descriptions.Item>
          <Descriptions.Item label="联动筛选状态">
            <Space wrap>
              {Object.entries(((bulkHistoryQuery.data as Record<string, any> | undefined)?.linkedFilterSummary || {})).map(([key, value]) => (
                <Tag key={key} color="cyan">{key}: {String(value)}</Tag>
              ))}
            </Space>
          </Descriptions.Item>
        </Descriptions>
        <Table
          rowKey={(row) => String((row as Record<string, unknown>).bulkCommandId || '')}
          dataSource={bulkHistoryQuery.data?.items || []}
          size="small"
          pagination={false}
          scroll={{ x: 860 }}
          onRow={(row) => ({ onClick: () => setSelectedBulkCommandId(String((row as Record<string, unknown>).bulkCommandId || '')) })}
          columns={[
            { title: '批量命令', dataIndex: 'bulkCommandId', key: 'bulkCommandId' },
            { title: '命令', dataIndex: 'command', key: 'command', render: (value: string) => <Tag color="purple">{value}</Tag> },
            { title: '模式', dataIndex: 'commandMode', key: 'commandMode', render: (value: string) => <Tag color="magenta">{value || 'direct'}</Tag> },
            { title: '结果模式', dataIndex: 'resultMode', key: 'resultMode', render: (value: string) => renderStatusTag(value) },
            { title: '操作人', dataIndex: 'operator', key: 'operator', render: (value: string | null | undefined) => value || '—' },
            { title: '成功/失败', key: 'summary', render: (_: unknown, row: Record<string, any>) => `${row.summary?.succeededJobs ?? 0} / ${row.summary?.failedJobs ?? 0}` },
            { title: '深度', key: 'lineageDepth', render: (_: unknown, row: Record<string, any>) => String(row.lineage?.lineageDepth ?? 0) },
            { title: '子结果', key: 'childCount', render: (_: unknown, row: Record<string, any>) => String(row.lineage?.childCount ?? 0) },
            { title: 'selection', key: 'selection', render: (_: unknown, row: Record<string, any>) => String(row.selection || 'direct') },
            { title: 'sourceResults', key: 'sourceBulkCommandIds', render: (_: unknown, row: Record<string, any>) => String((row.sourceBulkCommandIds || []).length) },
            { title: '导航', key: 'navigation', render: (_: unknown, row: Record<string, any>) => <Tag color="cyan">{String(row.navigation?.rootBulkCommandId || row.bulkCommandId || '—')}</Tag> },
            { title: '时间', dataIndex: 'eventAt', key: 'eventAt' },
          ]}
        />
        <Space style={{ marginTop: 12 }}>
          <Button disabled={(bulkHistoryQuery.data?.pagination as Record<string, any> | undefined)?.offset <= 0} onClick={() => setBulkHistoryOffset((value) => Math.max(value - 10, 0))}>上一页</Button>
          <Button disabled={!((bulkHistoryQuery.data?.pagination as Record<string, any> | undefined)?.hasMore)} onClick={() => setBulkHistoryOffset((value) => value + 10)}>下一页</Button>
          <Typography.Text type="secondary">已返回 {String((bulkHistoryQuery.data?.pagination as Record<string, any> | undefined)?.returned ?? 0)} / {String(bulkHistoryQuery.data?.total ?? 0)}</Typography.Text>
        </Space>
      </Card>

      <Card title="Summary" loading={isLoading} style={{ marginBottom: 16 }}>
        {renderSummaryCards(dashboardQuery.data?.summary)}
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} xl={8}>
          <Card title="Metrics" loading={metricsQuery.isLoading}>
            <Descriptions column={1} size="small">
              <Descriptions.Item label="总作业数">{metricsQuery.data?.summary?.totalJobs ?? 0}</Descriptions.Item>
              <Descriptions.Item label="活跃作业数">{metricsQuery.data?.summary?.activeJobs ?? 0}</Descriptions.Item>
              <Descriptions.Item label="Queue Lag 样本">{String(metricsQuery.data?.queueLagMetrics?.samples ?? 0)}</Descriptions.Item>
              <Descriptions.Item label="Run Duration 样本">{String(metricsQuery.data?.runDurationMetrics?.samples ?? 0)}</Descriptions.Item>
              <Descriptions.Item label="Turnaround 样本">{String(metricsQuery.data?.turnaroundMetrics?.samples ?? 0)}</Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
        <Col xs={24} xl={8}>
          <Card title="Failure Buckets" loading={failureQuery.isLoading}>
            <Descriptions column={1} size="small">
              <Descriptions.Item label="失败总数">{failureQuery.data?.summary?.totalFailedJobs ?? 0}</Descriptions.Item>
              <Descriptions.Item label="失败原因分类">
                <Space wrap>
                  {Object.entries(failureQuery.data?.reasonBucketSummary || {}).map(([key, value]) => (
                    <Tag key={key} color="red">{key}: {value}</Tag>
                  ))}
                </Space>
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
        <Col xs={24} xl={8}>
          <Card title="Stale Detection" loading={staleQuery.isLoading}>
            <Descriptions column={1} size="small">
              <Descriptions.Item label="Stale Jobs">{staleQuery.data?.summary?.staleJobs ?? 0}</Descriptions.Item>
              <Descriptions.Item label="Oldest Stale Seconds">{String(staleQuery.data?.summary?.oldestStaleSeconds ?? 0)}</Descriptions.Item>
              <Descriptions.Item label="Lease TTL Seconds">{String(staleQuery.data?.summary?.leaseTtlSeconds ?? 0)}</Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
      </Row>

      <div style={{ height: 16 }} />

      <Row gutter={[16, 16]}>
        <Col xs={24} xl={8}>
          <Card title="Worker Overview" loading={workerQuery.isLoading}>
            <Descriptions column={1} size="small">
              <Descriptions.Item label="排队作业">{workerQuery.data?.summary?.queuedJobs ?? 0}</Descriptions.Item>
              <Descriptions.Item label="运行作业">{workerQuery.data?.summary?.runningJobs ?? 0}</Descriptions.Item>
              <Descriptions.Item label="活跃租约">{workerQuery.data?.summary?.leasedJobs ?? 0}</Descriptions.Item>
              <Descriptions.Item label="疑似卡住">{workerQuery.data?.summary?.stalledJobs ?? 0}</Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
        <Col xs={24} xl={8}>
          <Card title="Store Overview" loading={storeQuery.isLoading}>
            <Descriptions column={1} size="small">
              <Descriptions.Item label="请求数">{storeQuery.data?.summary?.totalRequests ?? 0}</Descriptions.Item>
              <Descriptions.Item label="作业数">{storeQuery.data?.summary?.totalJobs ?? 0}</Descriptions.Item>
              <Descriptions.Item label="Job Events">{storeQuery.data?.summary?.totalJobEvents ?? 0}</Descriptions.Item>
              <Descriptions.Item label="Push 幂等键">{storeQuery.data?.summary?.pushIdempotencyEntries ?? 0}</Descriptions.Item>
              <Descriptions.Item label="命令幂等键">{storeQuery.data?.summary?.commandIdempotencyEntries ?? 0}</Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
        <Col xs={24} xl={8}>
          <Card title="Drill-down Usage" size="small">
            <Typography.Paragraph type="secondary" style={{ marginBottom: 8 }}>
              点击任意 Latest Jobs / Worker Queue / Stale Job Candidates 行，可查看作业详情、审计摘要与事件时间线。
            </Typography.Paragraph>
            <Space wrap>
              {jobAuditQuery.data?.availableCommands?.map((cmd) => (
                <Tag key={cmd} color="purple">{cmd}</Tag>
              ))}
            </Space>
          </Card>
        </Col>
      </Row>

      <div style={{ height: 16 }} />

      <Row gutter={[16, 16]}>
        <Col xs={24} xl={12}>
          <Card title="Latest Jobs" loading={dashboardQuery.isLoading}>
            <Table<ActionJobRecord>
              rowKey={(row) => row.jobId}
              dataSource={dashboardQuery.data?.latestJobs || []}
              columns={jobColumns}
              size="small"
              pagination={false}
              scroll={{ x: 880 }}
              onRow={(row) => ({ onClick: () => { setSelectedAuditEventId(undefined); setSelectedJobId(row.jobId) } })}
            />
          </Card>
        </Col>
        <Col xs={24} xl={12}>
          <Card title="Worker Queue / Next Jobs" loading={workerQuery.isLoading}>
            <Table<ActionJobRecord>
              rowKey={(row) => row.jobId}
              dataSource={workerQuery.data?.nextJobs || []}
              columns={jobColumns}
              size="small"
              pagination={false}
              scroll={{ x: 880 }}
              onRow={(row) => ({ onClick: () => { setSelectedAuditEventId(undefined); setSelectedJobId(row.jobId) } })}
            />
          </Card>
        </Col>
      </Row>

      <div style={{ height: 16 }} />

      <Card title={`Stale Job Candidates${selectedStaleJobIds.length ? ` · 已选 ${selectedStaleJobIds.length}` : ''}`} loading={staleQuery.isLoading} style={{ marginBottom: 16 }}>
        <Table<ActionJobRecord>
          rowKey={(row) => row.jobId}
          dataSource={staleQuery.data?.items || []}
          columns={jobColumns}
          size="small"
          pagination={false}
          scroll={{ x: 880 }}
          rowSelection={{ selectedRowKeys: selectedStaleJobIds, onChange: (keys) => setSelectedStaleJobIds(keys) }}
          onRow={(row) => ({ onClick: () => { setSelectedAuditEventId(undefined); setSelectedJobId(row.jobId) } })}
        />
      </Card>

      <Card title="Worker Lease Audit" loading={leaseAuditQuery.isLoading} style={{ marginBottom: 16 }}>
        <Descriptions column={1} size="small" style={{ marginBottom: 12 }}>
          <Descriptions.Item label="Claim Events">{leaseAuditQuery.data?.summary?.claimEvents ?? 0}</Descriptions.Item>
          <Descriptions.Item label="Heartbeat Events">{leaseAuditQuery.data?.summary?.heartbeatEvents ?? 0}</Descriptions.Item>
          <Descriptions.Item label="Release Events">{leaseAuditQuery.data?.summary?.releaseEvents ?? 0}</Descriptions.Item>
          <Descriptions.Item label="Worker Success / Failed">
            {(leaseAuditQuery.data?.summary?.succeededEvents ?? 0)} / {(leaseAuditQuery.data?.summary?.failedEvents ?? 0)}
          </Descriptions.Item>
        </Descriptions>
        <Table<Record<string, unknown>>
          rowKey={(row) => String(row.eventId || row.jobId || '')}
          dataSource={leaseAuditQuery.data?.items || []}
          size="small"
          pagination={false}
          scroll={{ x: 920 }}
          onRow={(row) => ({ onClick: () => { if (row.jobId) setSelectedJobId(String(row.jobId)); if (row.eventId) setSelectedAuditEventId(String(row.eventId)) } })}
          columns={[
            { title: '事件', dataIndex: 'eventType', key: 'eventType', render: (value: unknown) => <Tag color="blue">{String(value || '—')}</Tag> },
            { title: '作业', dataIndex: 'jobId', key: 'jobId' },
            { title: 'Worker', dataIndex: 'workerId', key: 'workerId', render: (value: unknown) => String(value || '—') },
            { title: '动作', dataIndex: 'actionCode', key: 'actionCode', render: (value: unknown) => String(value || '—') },
            { title: '时间', dataIndex: 'eventAt', key: 'eventAt', render: (value: unknown) => String(value || '—') },
          ]}
        />
      </Card>

      <Card title="Worker Command Audit" loading={commandAuditQuery.isLoading} style={{ marginBottom: 16 }}>
        <Descriptions column={1} size="small" style={{ marginBottom: 12 }}>
          <Descriptions.Item label="Stale Release Events">{commandAuditQuery.data?.summary?.staleReleaseEvents ?? 0}</Descriptions.Item>
          <Descriptions.Item label="Retry / Redrive">{(commandAuditQuery.data?.summary?.retryEvents ?? 0)} / {(commandAuditQuery.data?.summary?.redriveEvents ?? 0)}</Descriptions.Item>
          <Descriptions.Item label="Dead Letter Events">{commandAuditQuery.data?.summary?.deadLetterEvents ?? 0}</Descriptions.Item>
          <Descriptions.Item label="命令类型汇总">
            <Space wrap>
              {Object.entries(commandAuditQuery.data?.commandTypeSummary || {}).map(([key, value]) => (
                <Tag key={key} color="purple">{key}: {value}</Tag>
              ))}
            </Space>
          </Descriptions.Item>
        </Descriptions>
        <Table<Record<string, unknown>>
          rowKey={(row) => String(row.eventId || row.jobId || '')}
          dataSource={commandAuditQuery.data?.items || []}
          size="small"
          pagination={false}
          scroll={{ x: 920 }}
          onRow={(row) => ({ onClick: () => { if (row.jobId) setSelectedJobId(String(row.jobId)); if (row.eventId) setSelectedAuditEventId(String(row.eventId)) } })}
          columns={[
            { title: '事件', dataIndex: 'eventType', key: 'eventType', render: (value: unknown) => <Tag color="purple">{String(value || '—')}</Tag> },
            { title: '作业', dataIndex: 'jobId', key: 'jobId' },
            { title: 'Worker', dataIndex: 'workerId', key: 'workerId', render: (value: unknown) => String(value || '—') },
            { title: '动作', dataIndex: 'actionCode', key: 'actionCode', render: (value: unknown) => String(value || '—') },
            { title: '时间', dataIndex: 'eventAt', key: 'eventAt', render: (value: unknown) => String(value || '—') },
          ]}
        />
      </Card>

      <Drawer
        title={selectedJobId ? `动作作业详情 · ${selectedJobId}` : '动作作业详情'}
        width={720}
        open={Boolean(selectedJobId)}
        onClose={() => { setSelectedJobId(undefined); setSelectedAuditEventId(undefined) }}
      >
        <Descriptions column={1} size="small" bordered>
          <Descriptions.Item label="作业状态">{jobDetailQuery.data?.jobStatus || '—'}</Descriptions.Item>
          <Descriptions.Item label="队列状态">{jobDetailQuery.data?.queueStatus || '—'}</Descriptions.Item>
          <Descriptions.Item label="请求">{jobDetailQuery.data?.requestId || '—'}</Descriptions.Item>
          <Descriptions.Item label="批次">{jobDetailQuery.data?.batchRef || '—'}</Descriptions.Item>
          <Descriptions.Item label="动作">{jobDetailQuery.data?.actionCode || '—'}</Descriptions.Item>
          <Descriptions.Item label="Worker">{jobDetailQuery.data?.workerId || '—'}</Descriptions.Item>
          <Descriptions.Item label="推荐操作">{jobAuditQuery.data?.recommendedOperation || '—'}</Descriptions.Item>
          <Descriptions.Item label="失败原因">{jobAuditQuery.data?.failureReason || '—'}</Descriptions.Item>
        </Descriptions>

        <div style={{ height: 16 }} />

        <Card size="small" title="Audit Metrics" loading={jobAuditQuery.isLoading} style={{ marginBottom: 16 }}>
          <Descriptions column={1} size="small">
            <Descriptions.Item label="事件总数">{String(jobAuditQuery.data?.timelineTotal ?? 0)}</Descriptions.Item>
            <Descriptions.Item label="Event Types">
              <Space wrap>
                {Object.entries(jobAuditQuery.data?.eventTypeSummary || {}).map(([key, value]) => (
                  <Tag key={key}>{key}: {value}</Tag>
                ))}
              </Space>
            </Descriptions.Item>
          </Descriptions>
        </Card>

        <Card size="small" title="Command Audit Drill-down" loading={commandAuditDetailQuery.isLoading} style={{ marginBottom: 16 }}>
          {selectedAuditEventId ? (
            <Descriptions column={1} size="small">
              <Descriptions.Item label="Event">{String(commandAuditDetailQuery.data?.commandAudit?.eventType || '—')}</Descriptions.Item>
              <Descriptions.Item label="EventId">{selectedAuditEventId}</Descriptions.Item>
              <Descriptions.Item label="Actor">{String(commandAuditDetailQuery.data?.commandAudit?.actor || '—')}</Descriptions.Item>
              <Descriptions.Item label="Worker">{String(commandAuditDetailQuery.data?.commandAudit?.workerId || '—')}</Descriptions.Item>
              <Descriptions.Item label="消息">{String(commandAuditDetailQuery.data?.commandAudit?.message || '—')}</Descriptions.Item>
            </Descriptions>
          ) : (
            <Typography.Text type="secondary">点击 Worker Command Audit 表中的记录，可查看命令审计明细。</Typography.Text>
          )}
        </Card>

        <Card size="small" title="Timeline" loading={jobEventsQuery.isLoading}>
          <Timeline
            items={(jobEventsQuery.data?.events || []).map((event, index) => ({
              children: (
                <Space direction="vertical" size={0}>
                  <Typography.Text strong>{String(event['eventType'] || 'event')}</Typography.Text>
                  <Typography.Text type="secondary">{String(event['eventAt'] || '')}</Typography.Text>
                  <Typography.Text>{String(event['message'] || '')}</Typography.Text>
                </Space>
              ),
              color: String(event['status'] || '') === 'failed' ? 'red' : String(event['status'] || '') === 'succeeded' ? 'green' : 'blue',
            }))}
          />
        </Card>
      </Drawer>

      <Drawer
        title="批量命令结果明细"
        width={720}
        open={Boolean(selectedBulkCommandId)}
        onClose={() => setSelectedBulkCommandId(undefined)}
      >
        <Descriptions column={1} bordered size="small" style={{ marginBottom: 16 }}>
          <Descriptions.Item label="bulkCommandId">{bulkDetailQuery.data?.bulkCommandId || '—'}</Descriptions.Item>
          <Descriptions.Item label="命令">{String((bulkDetailQuery.data?.bulkCommand as Record<string, unknown> | undefined)?.command || '—')}</Descriptions.Item>
          <Descriptions.Item label="命令模式">{String((bulkDetailQuery.data?.bulkCommand as Record<string, any> | undefined)?.commandMode || 'direct')}</Descriptions.Item>
          <Descriptions.Item label="成功/失败">{String((bulkDetailQuery.data?.bulkCommand as Record<string, any> | undefined)?.summary?.succeededJobs ?? 0)} / {String((bulkDetailQuery.data?.bulkCommand as Record<string, any> | undefined)?.summary?.failedJobs ?? 0)}</Descriptions.Item>
          <Descriptions.Item label="可再执行失败项">{String((bulkDetailQuery.data?.secondaryActions as Record<string, any> | undefined)?.failedJobCount ?? 0)}</Descriptions.Item>
          <Descriptions.Item label="根结果">{String((bulkDetailQuery.data?.lineage as Record<string, any> | undefined)?.rootBulkCommandId ?? '—')}</Descriptions.Item>
          <Descriptions.Item label="来源结果">{String((bulkDetailQuery.data?.lineage as Record<string, any> | undefined)?.reexecuteOf ?? '—')}</Descriptions.Item>
          <Descriptions.Item label="子结果数量">{String((bulkDetailQuery.data?.lineage as Record<string, any> | undefined)?.childCount ?? 0)}</Descriptions.Item>
          <Descriptions.Item label="Lineage 深度">{String((bulkDetailQuery.data?.lineage as Record<string, any> | undefined)?.lineageDepth ?? 0)}</Descriptions.Item>
          <Descriptions.Item label="祖先链">{(((bulkDetailQuery.data?.lineage as Record<string, any> | undefined)?.ancestorBulkCommandIds || []) as string[]).join(' → ') || '—'}</Descriptions.Item>
          <Descriptions.Item label="lineageScope">{String((bulkDetailQuery.data?.bulkCommand as Record<string, any> | undefined)?.lineageScope || '—')}</Descriptions.Item>
          <Descriptions.Item label="sourceResults">{(((bulkDetailQuery.data?.bulkCommand as Record<string, any> | undefined)?.sourceBulkCommandIds || []) as string[]).join(', ') || '—'}</Descriptions.Item>
        </Descriptions>
        <Typography.Title level={5}>关联结果链路</Typography.Title>
        <Space wrap style={{ marginBottom: 12 }}>
          {Object.entries((bulkRelatedQuery.data?.commandSummary || {})).map(([key, value]) => (
            <Tag key={key} color="blue">{key}: {String(value)}</Tag>
          ))}
          {Object.entries((bulkRelatedQuery.data?.resultModeSummary || {})).map(([key, value]) => (
            <Tag key={key} color="purple">{key}: {String(value)}</Tag>
          ))}
        </Space>
        <Table<Record<string, unknown>>
          rowKey={(row) => String(row.bulkCommandId || '')}
          dataSource={bulkRelatedQuery.data?.items || []}
          size="small"
          pagination={false}
          style={{ marginBottom: 16 }}
          onRow={(row) => ({ onClick: () => setSelectedBulkCommandId(String(row.bulkCommandId || '')) })}
          columns={[
            { title: '结果', dataIndex: 'bulkCommandId', key: 'bulkCommandId' },
            { title: '命令', dataIndex: 'command', key: 'command' },
            { title: '模式', dataIndex: 'resultMode', key: 'resultMode', render: (value: unknown) => renderStatusTag(String(value || '—')) },
            { title: '来源', key: 'reexecuteOf', render: (_: unknown, row: Record<string, unknown>) => String((row.lineage as Record<string, unknown> | undefined)?.reexecuteOf || '—') },
            { title: '当前', key: 'isCurrent', render: (_: unknown, row: Record<string, unknown>) => Boolean(row.isCurrent) ? <Tag color="green">current</Tag> : <Tag>linked</Tag> },
          ]}
        />
        <Space wrap style={{ marginBottom: 16 }}>
          {((bulkDetailQuery.data?.secondaryActions as Record<string, any> | undefined)?.rerunnableCommands || []).map((cmd: string) => (
            <Button key={cmd} onClick={() => rerunBulkHistory(cmd)}>{`对失败项执行 ${cmd}`}</Button>
          ))}
          {((bulkDetailQuery.data?.secondaryActions as Record<string, any> | undefined)?.rerunnableCommands || []).map((cmd: string) => (
            <Button key={`lineage-${cmd}`} type="dashed" onClick={() => rerunBulkHistoryAcrossLineage(cmd)}>{`对 lineage 失败项执行 ${cmd}`}</Button>
          ))}
          <Button type="default" onClick={() => applyBulkLinkedFilters('history', (bulkLineageSummaryQuery.data?.linkedHistoryFilters as Record<string, unknown> | undefined) || (bulkDetailQuery.data?.navigationContext as Record<string, unknown> | undefined))}>联动到历史筛选</Button>
          <Button type="default" onClick={() => applyBulkLinkedFilters('timeline', (bulkLineageSummaryQuery.data?.linkedTimelineFilters as Record<string, unknown> | undefined) || (bulkDetailQuery.data?.navigationContext as Record<string, unknown> | undefined))}>联动到时间线筛选</Button>
        </Space>
        <Card size="small" title="Lineage Summary" loading={bulkLineageSummaryQuery.isLoading} style={{ marginBottom: 16 }}>
          {renderSummaryCards(bulkLineageSummaryQuery.data?.summary)}
          <div style={{ height: 12 }} />
          <Space wrap style={{ marginBottom: 8 }}>
            {Object.entries((bulkLineageSummaryQuery.data?.commandModeSummary || {})).map(([key, value]) => (
              <Tag key={key} color="magenta">{key}: {String(value)}</Tag>
            ))}
            {Object.entries((bulkLineageSummaryQuery.data?.eventTypeSummary || {})).map(([key, value]) => (
              <Tag key={key} color="blue">{key}: {String(value)}</Tag>
            ))}
            {Object.entries((bulkLineageSummaryQuery.data?.selectionSummary || {})).map(([key, value]) => (
              <Tag key={key} color="gold">{key}: {String(value)}</Tag>
            ))}
            {Object.entries((bulkLineageSummaryQuery.data?.reexecuteCommandSummary || {})).map(([key, value]) => (
              <Tag key={key} color="volcano">{key}: {String(value)}</Tag>
            ))}
          </Space>
          <Table<Record<string, unknown>>
            rowKey={(row) => String(row.bulkCommandId || '')}
            dataSource={bulkLineageSummaryQuery.data?.latestResults || []}
            size="small"
            pagination={false}
            locale={{ emptyText: '没有关联 lineage 结果' }}
            onRow={(row) => ({ onClick: () => setSelectedBulkCommandId(String(row.bulkCommandId || '')) })}
            columns={[
              { title: '结果', dataIndex: 'bulkCommandId', key: 'bulkCommandId' },
              { title: '命令', dataIndex: 'command', key: 'command' },
              { title: '模式', dataIndex: 'commandMode', key: 'commandMode', render: (value: unknown) => <Tag color="magenta">{String(value || 'direct')}</Tag> },
              { title: '结果模式', dataIndex: 'resultMode', key: 'resultMode', render: (value: unknown) => renderStatusTag(String(value || '—')) },
              { title: '时间', dataIndex: 'eventAt', key: 'eventAt' },
            ]}
          />
        </Card>
        <Typography.Title level={5}>结果时间线</Typography.Title>
        <Space wrap style={{ marginBottom: 12 }}>
          <Input placeholder="eventType" value={bulkTimelineEventType} onChange={(e) => setBulkTimelineEventType(e.target.value)} style={{ width: 140 }} />
          <Input placeholder="command" value={bulkTimelineCommand} onChange={(e) => setBulkTimelineCommand(e.target.value)} style={{ width: 140 }} />
          <Input placeholder="actionCode" value={bulkTimelineActionCode} onChange={(e) => setBulkTimelineActionCode(e.target.value)} style={{ width: 140 }} />
          <Input placeholder="depth" value={bulkTimelineLineageDepth} onChange={(e) => setBulkTimelineLineageDepth(e.target.value)} style={{ width: 100 }} />
          <Input placeholder="commandMode" value={bulkTimelineCommandMode} onChange={(e) => setBulkTimelineCommandMode(e.target.value)} style={{ width: 140 }} />
          <Input placeholder="sourceBulkCommandId" value={bulkTimelineSourceBulkCommandId} onChange={(e) => setBulkTimelineSourceBulkCommandId(e.target.value)} style={{ width: 180 }} />
          <Button onClick={() => { setBulkTimelineEventType(''); setBulkTimelineCommand(''); setBulkTimelineActionCode(''); setBulkTimelineLineageDepth(''); setBulkTimelineCommandMode(''); setBulkTimelineSourceBulkCommandId('') }}>清空时间线筛选</Button>
        </Space>
        <Space wrap style={{ marginBottom: 12 }}>
          {Object.entries((bulkTimelineQuery.data?.commandSummary || {})).map(([key, value]) => (
            <Tag key={key} color="blue">{key}: {String(value)}</Tag>
          ))}
          {Object.entries((bulkTimelineQuery.data?.resultModeSummary || {})).map(([key, value]) => (
            <Tag key={key} color="geekblue">{key}: {String(value)}</Tag>
          ))}
          {Object.entries((bulkTimelineQuery.data?.eventTypeSummary || {})).map(([key, value]) => (
            <Tag key={key} color="purple">{key}: {String(value)}</Tag>
          ))}
          {Object.entries((bulkTimelineQuery.data?.actionCodeSummary || {})).map(([key, value]) => (
            <Tag key={key} color="gold">{key}: {String(value)}</Tag>
          ))}
          {Object.entries((bulkTimelineQuery.data?.commandModeSummary || {})).map(([key, value]) => (
            <Tag key={key} color="magenta">{key}: {String(value)}</Tag>
          ))}
          {Object.entries((bulkTimelineQuery.data?.lineageSummary || {})).map(([key, value]) => (
            <Tag key={key} color="cyan">{key}: {String(value)}</Tag>
          ))}
        </Space>
        <Table<Record<string, unknown>>
          rowKey={(row) => `${String(row.bulkCommandId || '')}-${String(row.eventAt || '')}`}
          dataSource={bulkTimelineQuery.data?.items || []}
          size="small"
          pagination={false}
          style={{ marginBottom: 16 }}
          onRow={(row) => ({ onClick: () => setSelectedBulkCommandId(String(row.bulkCommandId || '')) })}
          columns={[
            { title: '时间', dataIndex: 'eventAt', key: 'eventAt' },
            { title: '结果', dataIndex: 'bulkCommandId', key: 'bulkCommandId' },
            { title: '事件', dataIndex: 'eventType', key: 'eventType', render: (value: unknown) => <Tag>{String(value || '—')}</Tag> },
            { title: '命令', dataIndex: 'command', key: 'command' },
            { title: '动作', key: 'actionCodes', render: (_: unknown, row: Record<string, any>) => String((row.actionCodes || []).join(', ') || '—') },
            { title: '模式', dataIndex: 'resultMode', key: 'resultMode', render: (value: unknown) => renderStatusTag(String(value || '—')) },
            { title: '深度', key: 'lineageDepth', render: (_: unknown, row: Record<string, any>) => String(row.lineage?.lineageDepth ?? 0) },
          ]}
        />
        <Typography.Title level={5}>失败原因汇总</Typography.Title>
        <Space wrap style={{ marginBottom: 16 }}>
          {Object.entries(((bulkDetailQuery.data?.bulkCommand as Record<string, any> | undefined)?.errorReasonSummary || {})).map(([key, value]) => (
            <Tag key={key} color="red">{key}: {String(value)}</Tag>
          ))}
        </Space>
        <Typography.Title level={5}>成功项</Typography.Title>
        <Table
          rowKey={(row) => String((row as Record<string, unknown>).jobId || '')}
          dataSource={((bulkDetailQuery.data?.bulkCommand as Record<string, any> | undefined)?.items || [])}
          size="small"
          pagination={false}
          scroll={{ x: 720 }}
          onRow={(row) => ({ onClick: () => { setSelectedBulkCommandId(undefined); setSelectedJobId(String((row as Record<string, unknown>).jobId || '')) } })}
          columns={jobColumns}
        />
        <Typography.Title level={5} style={{ marginTop: 16 }}>失败项</Typography.Title>
        <Table<Record<string, unknown>>
          rowKey={(row) => `${String(row.jobId || '')}-${String(row.reason || '')}`}
          dataSource={((bulkDetailQuery.data?.bulkCommand as Record<string, any> | undefined)?.errors || [])}
          size="small"
          pagination={false}
          scroll={{ x: 720 }}
          columns={[
            { title: '作业', dataIndex: 'jobId', key: 'jobId' },
            { title: '原因', dataIndex: 'reason', key: 'reason', render: (value: unknown) => <Tag color="red">{String(value || '—')}</Tag> },
          ]}
        />
      </Drawer>
    </div>
  )
}
