import {
  Alert,
  Card,
  Col,
  Descriptions,
  Empty,
  Row,
  Select,
  Skeleton,
  Space,
  Table,
  Tabs,
  Tag,
  Timeline,
  Typography,
} from 'antd'
import { DatabaseOutlined, DeploymentUnitOutlined, ReloadOutlined } from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { Suspense, lazy, useEffect, useMemo, useState } from 'react'

import { ingestionApi } from '../../services/ingestion'
import type { DatasetRegistryItem, WorkspaceBatchDetail, WorkspaceBatchListItem } from '../../types'

const DataImportV2 = lazy(() => import('../DataImportV2'))

function renderGateTag(value?: string) {
  if (!value) return <Tag>—</Tag>
  if (value === 'passed') return <Tag color="green">通过</Tag>
  if (value === 'risk') return <Tag color="orange">风险</Tag>
  if (value === 'failed') return <Tag color="red">失败</Tag>
  return <Tag>{value}</Tag>
}

function renderBatchStatus(value?: string) {
  if (!value) return <Tag>—</Tag>
  const color =
    value === 'imported'
      ? 'green'
      : value === 'validated'
      ? 'blue'
      : value === 'blocked'
      ? 'orange'
      : value === 'partially_imported'
      ? 'gold'
      : value === 'failed'
      ? 'red'
      : 'default'
  return <Tag color={color}>{value}</Tag>
}

function renderConfirmStatus(value?: string) {
  if (!value) return '—'
  if (value === 'success') return '成功'
  if (value === 'failed') return '失败'
  return value
}

export default function DataWorkspacePage() {
  const [workspaceMode, setWorkspaceMode] = useState<'overview' | 'execute'>('overview')

  const { data, isLoading, error } = useQuery({
    queryKey: ['dataset-registry'],
    queryFn: () => ingestionApi.getDatasetRegistry(),
    staleTime: 5 * 60 * 1000,
  })

  const {
    data: recentBatchData,
    isLoading: isBatchListLoading,
    refetch: refetchBatchList,
  } = useQuery({
    queryKey: ['workspace-batches', 20],
    queryFn: () => ingestionApi.listBatches(20),
    staleTime: 30 * 1000,
  })

  const rows = data?.datasets || []
  const datasetOptions = useMemo(
    () =>
      rows.map((row: DatasetRegistryItem) => ({
        label: `${row.label || row.datasetKind} (${row.importProfile})`,
        value: `${row.datasetKind}::${row.importProfile}`,
        datasetKind: row.datasetKind,
        importProfile: row.importProfile,
      })),
    [rows],
  )

  const [selectedDatasetKey, setSelectedDatasetKey] = useState<string>('orders::ozon_orders_report')
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null)

  const selectedDataset =
    datasetOptions.find((item) => item.value === selectedDatasetKey) ||
    datasetOptions[0] || {
      value: 'orders::ozon_orders_report',
      datasetKind: 'orders',
      importProfile: 'ozon_orders_report',
      label: '订单/商品经营报表 (ozon_orders_report)',
    }

  const recentBatches = recentBatchData?.items || []

  useEffect(() => {
    if (!selectedSessionId && recentBatches.length > 0) {
      setSelectedSessionId(Number(recentBatches[0].sessionId))
    }
  }, [recentBatches, selectedSessionId])

  const {
    data: selectedBatchDetail,
    isLoading: isBatchDetailLoading,
  } = useQuery<WorkspaceBatchDetail | null>({
    queryKey: ['workspace-batch-detail', selectedSessionId],
    queryFn: async () => {
      if (!selectedSessionId) return null
      return ingestionApi.getBatch(selectedSessionId)
    },
    enabled: !!selectedSessionId,
    staleTime: 15 * 1000,
  })

  const registryColumns = [
    {
      title: '数据集',
      dataIndex: 'label',
      key: 'label',
      render: (_: string, row: DatasetRegistryItem) => (
        <Space>
          <Tag color="blue">{row.datasetKind}</Tag>
          <span>{row.label || row.datasetKind}</span>
        </Space>
      ),
    },
    { title: '平台', dataIndex: 'platform', key: 'platform', render: (v: string) => <Tag>{v || 'generic'}</Tag> },
    { title: '来源', dataIndex: 'sourceType', key: 'sourceType' },
    {
      title: '核心字段',
      dataIndex: 'requiredCoreFields',
      key: 'requiredCoreFields',
      render: (vals: string[]) => <Space wrap>{(vals || []).map((x) => <Tag key={x} color="red">{x}</Tag>)}</Space>,
    },
    {
      title: '可选字段',
      dataIndex: 'optionalCommonFields',
      key: 'optionalCommonFields',
      render: (vals: string[]) => <span>{(vals || []).slice(0, 6).join(' / ') || '—'}</span>,
    },
    { title: '落点', dataIndex: 'loaderTarget', key: 'loaderTarget', render: (v: string) => <code>{v || '—'}</code> },
  ]

  const batchColumns = [
    {
      title: '批次',
      key: 'workspaceBatchId',
      render: (_: unknown, row: WorkspaceBatchListItem) => (
        <Space direction="vertical" size={0}>
          <Typography.Text strong>{row.workspaceBatchId || `session-${row.sessionId}`}</Typography.Text>
          <Typography.Text type="secondary">{row.fileName || '—'}</Typography.Text>
        </Space>
      ),
    },
    {
      title: '状态',
      key: 'status',
      render: (_: unknown, row: WorkspaceBatchListItem) => (
        <Space wrap>
          {renderBatchStatus(row.batchStatus)}
          {renderGateTag(row.importabilityStatus)}
        </Space>
      ),
    },
    {
      title: '导入结果',
      key: 'importedRows',
      render: (_: unknown, row: WorkspaceBatchListItem) => (
        <Space direction="vertical" size={0}>
          <span>入库: {row.importedRows ?? 0}</span>
          <span>隔离: {row.quarantineCount ?? 0}</span>
        </Space>
      ),
    },
    {
      title: '时间',
      dataIndex: 'updatedAt',
      key: 'updatedAt',
      render: (v: string) => <span>{v || '—'}</span>,
    },
  ]

  const detail = selectedBatchDetail
  const finalSnapshot = detail?.finalSnapshot || detail?.confirmSnapshot || detail?.parseSnapshot
  const timelineItems =
    detail?.timeline?.map((item, index) => ({
      key: `${item.eventType || 'event'}-${index}`,
      children: (
        <Space direction="vertical" size={4}>
          <Space wrap>
            <Tag color="blue">{item.eventType || '事件'}</Tag>
            {renderBatchStatus(item.batchStatus)}
            {renderGateTag(item.importabilityStatus)}
            <Typography.Text type="secondary">{item.recordedAt || '—'}</Typography.Text>
          </Space>
          <Typography.Text>
            状态: {item.status || '—'} / 最终: {item.finalStatus || '—'}
          </Typography.Text>
          <Typography.Text>
            入库: {item.importedRows ?? 0} / 隔离: {item.quarantineCount ?? 0}
          </Typography.Text>
          {item.reasons?.length ? (
            <Typography.Text type="secondary">原因: {item.reasons.join(' | ')}</Typography.Text>
          ) : null}
        </Space>
      ),
    })) || []

  return (
    <div style={{ padding: 24 }}>
      <Alert
        type="info"
        showIcon
        message="数据工作台"
        description="默认先看工作台总览，再进入导入执行。系统设置只保留配置，不再承载日常导入主流程。"
        style={{ marginBottom: 16 }}
      />

      <Card
        style={{ marginBottom: 16 }}
        title="工作台模式"
        extra={
          <Space>
            <Tag color="blue">{selectedDataset.datasetKind}</Tag>
            <Tag color="purple">{selectedDataset.importProfile}</Tag>
          </Space>
        }
      >
        <Tabs
          activeKey={workspaceMode}
          onChange={(value) => setWorkspaceMode(value as 'overview' | 'execute')}
          type="card"
          items={[
            { key: 'overview', label: '工作台总览' },
            { key: 'execute', label: '导入执行' },
          ]}
        />
      </Card>

      {workspaceMode === 'overview' ? (
        <>
          <Row gutter={[16, 16]}>
            <Col xs={24} xl={8}>
              <Card title={<span><DeploymentUnitOutlined /> 数据集注册表摘要</span>}>
                {isLoading ? (
                  <Skeleton active paragraph={{ rows: 6 }} />
                ) : (
                  <Descriptions column={1} size="small">
                    <Descriptions.Item label="契约版本">{data?.contractVersion || 'p1.v1'}</Descriptions.Item>
                    <Descriptions.Item label="已注册数据集">{rows.length}</Descriptions.Item>
                    <Descriptions.Item label="当前策略">orders / ads / reviews 先落地</Descriptions.Item>
                    <Descriptions.Item label="当前导入数据集">{selectedDataset.datasetKind}</Descriptions.Item>
                    <Descriptions.Item label="当前导入 Profile">{selectedDataset.importProfile}</Descriptions.Item>
                  </Descriptions>
                )}
              </Card>
            </Col>
            <Col xs={24} xl={16}>
              <Card
                title={<span><DatabaseOutlined /> 数据集注册表</span>}
                extra={
                  <Select
                    style={{ minWidth: 320 }}
                    value={selectedDatasetKey}
                    onChange={setSelectedDatasetKey}
                    options={datasetOptions}
                    placeholder="选择导入数据集"
                  />
                }
              >
                {error ? (
                  <Alert
                    type="warning"
                    showIcon
                    message="注册表读取失败"
                    description="后端 /api/import/dataset-registry 或 /api/ingestion/dataset-registry 尚不可用。"
                  />
                ) : (
                  <Table
                    rowKey={(row: DatasetRegistryItem) => `${row.datasetKind}-${row.importProfile}`}
                    dataSource={rows}
                    columns={registryColumns as any}
                    size="small"
                    pagination={false}
                    locale={{ emptyText: '暂无已注册数据集' }}
                    scroll={{ x: 960 }}
                  />
                )}
              </Card>
            </Col>
          </Row>

          <div style={{ height: 16 }} />

          <Row gutter={[16, 16]}>
            <Col xs={24} xl={10}>
              <Card
                title="最近批次"
                extra={<ReloadOutlined onClick={() => refetchBatchList()} style={{ cursor: 'pointer' }} />}
              >
                <Table
                  rowKey={(row: WorkspaceBatchListItem) => `${row.workspaceBatchId || 'ws'}-${row.sessionId}`}
                  dataSource={recentBatches}
                  columns={batchColumns as any}
                  size="small"
                  pagination={{ pageSize: 6, showSizeChanger: false }}
                  loading={isBatchListLoading}
                  locale={{ emptyText: '暂无最近批次' }}
                  onRow={(row: WorkspaceBatchListItem) => ({
                    onClick: () => setSelectedSessionId(Number(row.sessionId)),
                    style: {
                      cursor: 'pointer',
                      background: Number(row.sessionId) === Number(selectedSessionId) ? '#fafafa' : undefined,
                    },
                  })}
                />
              </Card>
            </Col>

            <Col xs={24} xl={14}>
              <Card title="批次详情">
                {isBatchDetailLoading ? (
                  <Skeleton active paragraph={{ rows: 8 }} />
                ) : !detail ? (
                  <Empty description="尚未选择批次" />
                ) : (
                  <Space direction="vertical" style={{ width: '100%' }} size="middle">
                    <Descriptions size="small" bordered column={2}>
                      <Descriptions.Item label="批次ID">{detail.workspaceBatchId || '—'}</Descriptions.Item>
                      <Descriptions.Item label="数据库批次ID">{detail.dbBatchId || '—'}</Descriptions.Item>
                      <Descriptions.Item label="sessionId">{detail.sessionId || '—'}</Descriptions.Item>
                      <Descriptions.Item label="文件">{detail.fileName || '—'}</Descriptions.Item>
                      <Descriptions.Item label="数据集">{detail.datasetKind || '—'}</Descriptions.Item>
                      <Descriptions.Item label="Profile">{detail.importProfile || '—'}</Descriptions.Item>
                      <Descriptions.Item label="批次状态">{renderBatchStatus(finalSnapshot?.batchStatus)}</Descriptions.Item>
                      <Descriptions.Item label="导入门禁">{renderGateTag(finalSnapshot?.importabilityStatus)}</Descriptions.Item>
                      <Descriptions.Item label="传输状态">{renderGateTag(finalSnapshot?.transportStatus)}</Descriptions.Item>
                      <Descriptions.Item label="语义状态">{renderGateTag(finalSnapshot?.semanticStatus)}</Descriptions.Item>
                      <Descriptions.Item label="入库行数">{finalSnapshot?.importedRows ?? detail.importedRows ?? 0}</Descriptions.Item>
                      <Descriptions.Item label="隔离行数">{finalSnapshot?.quarantineCount ?? detail.quarantineCount ?? 0}</Descriptions.Item>
                    </Descriptions>

                    <Descriptions size="small" bordered column={2} title="解析摘要">
                      <Descriptions.Item label="解析状态">{detail.parseResultMeta?.status || '—'}</Descriptions.Item>
                      <Descriptions.Item label="最终状态">{detail.parseResultMeta?.finalStatus || '—'}</Descriptions.Item>
                      <Descriptions.Item label="映射覆盖率">{detail.parseResultMeta?.mappingCoverage ?? '—'}</Descriptions.Item>
                      <Descriptions.Item label="已映射字段">{detail.parseResultMeta?.mappedCount ?? '—'}</Descriptions.Item>
                      <Descriptions.Item label="未映射字段">{detail.parseResultMeta?.unmappedCount ?? '—'}</Descriptions.Item>
                      <Descriptions.Item label="工作表">{detail.parseResultMeta?.selectedSheet || '—'}</Descriptions.Item>
                    </Descriptions>

                    <Descriptions size="small" bordered column={2} title="确认摘要">
                      <Descriptions.Item label="确认状态">{renderConfirmStatus(detail.confirmResultMeta?.status)}</Descriptions.Item>
                      <Descriptions.Item label="入库行数">{detail.confirmResultMeta?.importedRows ?? '—'}</Descriptions.Item>
                      <Descriptions.Item label="错误行数">{detail.confirmResultMeta?.errorRows ?? '—'}</Descriptions.Item>
                      <Descriptions.Item label="事实装载错误">{detail.confirmResultMeta?.factLoadErrors ?? '—'}</Descriptions.Item>
                      <Descriptions.Item label="隔离行数">{detail.confirmResultMeta?.quarantineCount ?? '—'}</Descriptions.Item>
                      <Descriptions.Item label="更新时间">{detail.updatedAt || '—'}</Descriptions.Item>
                    </Descriptions>

                    <Card size="small" title="事件时间线">
                      {timelineItems.length ? <Timeline items={timelineItems} /> : <Empty description="暂无事件时间线" />}
                    </Card>
                  </Space>
                )}
              </Card>
            </Col>
          </Row>
        </>
      ) : (
        <Card
          title="导入执行"
          extra={
            <Space>
              <Tag color="blue">{selectedDataset.datasetKind}</Tag>
              <Tag color="purple">{selectedDataset.importProfile}</Tag>
            </Space>
          }
        >
          <Suspense fallback={<Skeleton active paragraph={{ rows: 8 }} />}>
            <DataImportV2
              key={`${selectedDataset.datasetKind}::${selectedDataset.importProfile}`}
              datasetKind={selectedDataset.datasetKind}
              importProfile={selectedDataset.importProfile}
            />
          </Suspense>
        </Card>
      )}
    </div>
  )
}
