import { Alert, Card, Col, Descriptions, Row, Select, Skeleton, Space, Table, Tag } from 'antd'
import { DatabaseOutlined, DeploymentUnitOutlined } from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'

import { useMemo, useState } from 'react'

import DataImportV2 from '../DataImportV2'
import { ingestionApi } from '../../services/ingestion'
import type { DatasetRegistryItem } from '../../types'

export default function DataWorkspacePage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['dataset-registry'],
    queryFn: () => ingestionApi.getDatasetRegistry(),
    staleTime: 5 * 60 * 1000,
  })


  const rows = data?.datasets || []
  const datasetOptions = useMemo(() => rows.map((row: DatasetRegistryItem) => ({
    label: `${row.label || row.datasetKind} (${row.importProfile})`,
    value: `${row.datasetKind}::${row.importProfile}`,
    datasetKind: row.datasetKind,
    importProfile: row.importProfile,
  })), [rows])
  const [selectedDatasetKey, setSelectedDatasetKey] = useState<string>('orders::ozon_orders_report')
  const selectedDataset = datasetOptions.find((item) => item.value === selectedDatasetKey) || datasetOptions[0] || {
    value: 'orders::ozon_orders_report',
    datasetKind: 'orders',
    importProfile: 'ozon_orders_report',
    label: '订单/商品经营报表 (ozon_orders_report)',
  }
  const columns = [
    { title: '数据集', dataIndex: 'label', key: 'label', render: (_: string, row: DatasetRegistryItem) => <Space><Tag color="blue">{row.datasetKind}</Tag><span>{row.label || row.datasetKind}</span></Space> },
    { title: '平台', dataIndex: 'platform', key: 'platform', render: (v: string) => <Tag>{v || 'generic'}</Tag> },
    { title: '来源', dataIndex: 'sourceType', key: 'sourceType' },
    { title: '核心字段', dataIndex: 'requiredCoreFields', key: 'requiredCoreFields', render: (vals: string[]) => <Space wrap>{(vals || []).map((x) => <Tag key={x} color="red">{x}</Tag>)}</Space> },
    { title: '可选字段', dataIndex: 'optionalCommonFields', key: 'optionalCommonFields', render: (vals: string[]) => <span>{(vals || []).slice(0, 6).join(' / ') || '—'}</span> },
    { title: '落点', dataIndex: 'loaderTarget', key: 'loaderTarget', render: (v: string) => <code>{v || '—'}</code> },
  ]

  return (
    <div style={{ padding: 24 }}>
      <Alert
        type="info"
        showIcon
        message="Data Workspace（过渡版）"
        description="本页不替代现有 DataImportV2，而是在其上增加数据集注册表与统一批次契约视图，开始把导入页收口为工作台。"
        style={{ marginBottom: 16 }}
      />

      <Row gutter={[16, 16]}>
        <Col xs={24} xl={8}>
          <Card title={<span><DeploymentUnitOutlined /> 数据集注册表摘要</span>}>
            {isLoading ? <Skeleton active paragraph={{ rows: 6 }} /> : (
              <Descriptions column={1} size="small">
                <Descriptions.Item label="Contract Version">{data?.contractVersion || 'p1.v1'}</Descriptions.Item>
                <Descriptions.Item label="已注册数据集">{rows.length}</Descriptions.Item>
                <Descriptions.Item label="当前策略">orders / ads / reviews 先落地</Descriptions.Item>
                <Descriptions.Item label="当前导入数据集">{selectedDataset.datasetKind}</Descriptions.Item>
                <Descriptions.Item label="当前导入 Profile">{selectedDataset.importProfile}</Descriptions.Item>
              </Descriptions>
            )}
          </Card>
        </Col>
        <Col xs={24} xl={16}>
          <Card title={<span><DatabaseOutlined /> 数据集注册表</span>} extra={<Select style={{ minWidth: 320 }} value={selectedDatasetKey} onChange={setSelectedDatasetKey} options={datasetOptions} placeholder="选择导入数据集" />}>
            {error ? (
              <Alert type="warning" showIcon message="注册表读取失败" description="后端 /api/import/dataset-registry 或 /api/ingestion/dataset-registry 尚不可用。" />
            ) : (
              <Table
                rowKey={(row: DatasetRegistryItem) => `${row.datasetKind}-${row.importProfile}`}
                dataSource={rows}
                columns={columns as any}
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
      <DataImportV2 datasetKind={selectedDataset.datasetKind} importProfile={selectedDataset.importProfile} />
    </div>
  )
}
