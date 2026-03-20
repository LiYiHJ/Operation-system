import React from 'react'
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Progress,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
} from 'antd'
import type { EntityKeySuggestion, FieldMapping, ImportResult } from '../../types'
import type { SavedTemplate, StandardFieldConfig } from './shared'
import {
  UNMAPPED_VALUE,
  getSuggestionOverride,
  isIgnoredField,
  isMappedField,
  renderGateTag,
} from './shared'

type DisplayStats = {
  mappedCount: number
  unmappedCount: number
  mappingCoverage: number
  mappedConfidence: number
  rawColumns: number
}

type Props = {
  importResult: ImportResult
  selectedFileName?: string
  standardFieldRegistry: Record<string, StandardFieldConfig>
  savedTemplates: SavedTemplate[]
  acceptedEntityKeySuggestion: boolean
  entityKeySuggestion: EntityKeySuggestion | null
  semanticRisk: boolean
  displayStats: DisplayStats
  importing: boolean
  onManualMapping: (index: number, nextValue: string) => void
  onSaveTemplate: () => void
  onApplyTemplate: (template: SavedTemplate) => void
  onToggleAcceptedEntityKeySuggestion: (next: boolean) => void
  onConfirmImport: () => void
  onBackToUpload: () => void
}

export default function ImportMappingStep({
  importResult,
  selectedFileName,
  standardFieldRegistry,
  savedTemplates,
  acceptedEntityKeySuggestion,
  entityKeySuggestion,
  semanticRisk,
  displayStats,
  importing,
  onManualMapping,
  onSaveTemplate,
  onApplyTemplate,
  onToggleAcceptedEntityKeySuggestion,
  onConfirmImport,
  onBackToUpload,
}: Props) {
  const mappings = Array.isArray(importResult.fieldMappings) ? importResult.fieldMappings : []
  const canUseSuggestion =
    !!entityKeySuggestion?.field &&
    !!entityKeySuggestion?.sourceColumn &&
    !mappings.some((m) => m.standardField === 'sku')

  const columns = [
    {
      title: '原始字段',
      dataIndex: 'originalField',
      key: 'originalField',
      width: 220,
      render: (text: string) => <strong>{text}</strong>,
    },
    {
      title: '样本值',
      dataIndex: 'sampleValues',
      key: 'sampleValues',
      width: 260,
      render: (values: any[]) => {
        const display = Array.isArray(values) ? values.slice(0, 3).join(', ') : ''
        return <span>{display || '—'}</span>
      },
    },
    {
      title: '映射到',
      dataIndex: 'standardField',
      key: 'standardField',
      width: 240,
      render: (field: string | null, _: FieldMapping, index: number) => (
        <Select
          value={field || UNMAPPED_VALUE}
          style={{ width: '100%' }}
          onChange={(value) => onManualMapping(index, value)}
          options={[
            { value: UNMAPPED_VALUE, label: '不映射' },
            ...Object.entries(standardFieldRegistry).map(([key, config]) => ({
              value: key,
              label: `${config.required ? '[必填] ' : ''}${config.category} · ${config.name}`,
            })),
          ]}
          showSearch
          optionFilterProp="label"
        />
      ),
    },
    {
      title: '置信度',
      dataIndex: 'confidence',
      key: 'confidence',
      width: 140,
      render: (val: number) => (
        <Progress
          percent={(val || 0) * 100}
          size="small"
          status={val > 0.7 ? 'success' : val > 0.4 ? 'normal' : 'exception'}
          format={(percent) => `${percent?.toFixed(0)}%`}
        />
      ),
    },
    {
      title: '状态',
      key: 'status',
      width: 100,
      render: (_: any, record: FieldMapping) => {
        if (record.isManual) return <Tag color="blue">手动</Tag>
        if (isIgnoredField(record)) return <Tag>忽略</Tag>
        if (isMappedField(record)) return <Tag color="green">自动</Tag>
        return <Tag>未映射</Tag>
      },
    },
  ]

  return (
    <div>
      {mappings.length === 0 && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          message="后端未返回 fieldMappings，当前按回退模式展示统计与建议"
          description={
            <div>
              <div>已映射字段：{displayStats.mappedCount}</div>
              <div>待处理字段：{displayStats.unmappedCount}</div>
              <div>映射覆盖率：{(displayStats.mappingCoverage * 100).toFixed(1)}%</div>
              <div>若下方出现 SKU 建议，可直接接受建议后确认导入。</div>
            </div>
          }
        />
      )}

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card><Statistic title="已映射字段" value={displayStats.mappedCount} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="待处理字段" value={displayStats.unmappedCount} /></Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="映射覆盖率" value={displayStats.mappingCoverage * 100} precision={1} suffix="%" />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="平均置信度" value={displayStats.mappedConfidence * 100} precision={1} suffix="%" />
          </Card>
        </Col>
      </Row>

      <Card style={{ marginBottom: 16 }}>
        <Descriptions bordered column={3} size="small">
          <Descriptions.Item label="文件名">{importResult.fileName || selectedFileName || 'n/a'}</Descriptions.Item>
          <Descriptions.Item label="平台">{importResult.platform}</Descriptions.Item>
          <Descriptions.Item label="表头行">第 {importResult.headerRow} 行</Descriptions.Item>
          <Descriptions.Item label="传输状态">{renderGateTag(importResult.transportStatus)}</Descriptions.Item>
          <Descriptions.Item label="语义状态">{renderGateTag(importResult.semanticStatus)}</Descriptions.Item>
          <Descriptions.Item label="最终状态">{renderGateTag(importResult.finalStatus)}</Descriptions.Item>
          <Descriptions.Item label="总行数">{importResult.totalRows}</Descriptions.Item>
          <Descriptions.Item label="原始列数">{displayStats.rawColumns}</Descriptions.Item>
          <Descriptions.Item label="当前列数">{importResult.totalColumns}</Descriptions.Item>
        </Descriptions>
      </Card>

      {canUseSuggestion && (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          message="检测到疑似 SKU 主标识列"
          description={
            <div>
              <div>建议字段：{entityKeySuggestion?.field}</div>
              <div>建议列：{entityKeySuggestion?.sourceColumn}</div>
              <div>样本值：{entityKeySuggestion?.sampleToken || 'n/a'}</div>
              <div>置信度：{((entityKeySuggestion?.confidence || 0) * 100).toFixed(1)}%</div>
              <Space style={{ marginTop: 12 }}>
                <Button
                  type={acceptedEntityKeySuggestion ? 'primary' : 'default'}
                  onClick={() => onToggleAcceptedEntityKeySuggestion(!acceptedEntityKeySuggestion)}
                >
                  {acceptedEntityKeySuggestion ? '已接受建议' : '接受建议'}
                </Button>
                <Button
                  onClick={() => onToggleAcceptedEntityKeySuggestion(false)}
                  disabled={!acceptedEntityKeySuggestion}
                >
                  忽略建议
                </Button>
              </Space>
            </div>
          }
        />
      )}

      <Card
        title="字段映射"
        extra={
          <Space>
            <Button onClick={onSaveTemplate}>保存模板</Button>
            {savedTemplates.length > 0 && (
              <Select
                style={{ width: 220 }}
                placeholder="应用模板"
                onChange={(index) => onApplyTemplate(savedTemplates[index])}
                options={savedTemplates.map((template, index) => ({
                  value: index,
                  label: `${template.name} (${template.platform})`,
                }))}
              />
            )}
          </Space>
        }
      >
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          message="可手动调整字段映射；如接受系统建议，确认导入时将只提交你确认过的 override。"
        />

        <Table
          rowKey={(record: FieldMapping) => record.originalField}
          columns={columns}
          dataSource={mappings}
          pagination={{ pageSize: 20 }}
          scroll={{ x: 980 }}
          size="small"
        />

        <Space style={{ marginTop: 16 }}>
          <Button onClick={onBackToUpload}>返回重新上传</Button>
          <Button
            type="primary"
            onClick={onConfirmImport}
            loading={importing}
            disabled={displayStats.mappedCount === 0 && !acceptedEntityKeySuggestion}
          >
            {semanticRisk ? '存在语义风险，继续导入（需确认）' : '确认导入'}
          </Button>
        </Space>
      </Card>
    </div>
  )
}
