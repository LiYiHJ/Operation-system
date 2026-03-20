import React from 'react'
import { Alert, Button, Card, Descriptions, Space, Typography } from 'antd'
import { CheckCircleOutlined } from '@ant-design/icons'
import type { ConfirmImportResponse, ImportResult } from '../../types'
import { renderGateTag } from './shared'

const { Title, Paragraph, Text } = Typography

type Props = {
  confirmResult: ConfirmImportResponse | null
  importResult: ImportResult | null
  onGoDashboard: () => void
  onContinueImport: () => void
}

export default function ImportCompleteStep({
  confirmResult,
  importResult,
  onGoDashboard,
  onContinueImport,
}: Props) {
  const result = confirmResult

  return (
    <Card>
      <Space direction="vertical" style={{ width: '100%' }}>
        <Space direction="vertical" style={{ width: '100%', alignItems: 'center' }}>
          <CheckCircleOutlined style={{ fontSize: 56, color: '#52c41a' }} />
          <Title level={3} style={{ marginBottom: 0 }}>
            {result?.importabilityStatus === 'risk' ? '导入完成，但需复核' : '导入完成'}
          </Title>
          <Paragraph type="secondary" style={{ marginBottom: 0 }}>
            成功导入 {result?.importedRows ?? 0} 条，隔离 {result?.quarantineCount ?? 0} 条
          </Paragraph>
        </Space>

        <Descriptions bordered column={3}>
          <Descriptions.Item label="语义状态">
            {renderGateTag(result?.semanticStatus || importResult?.semanticStatus)}
          </Descriptions.Item>
          <Descriptions.Item label="导入可用性">
            {renderGateTag(result?.importabilityStatus)}
          </Descriptions.Item>
          <Descriptions.Item label="最终状态">
            {renderGateTag(result?.finalStatus || importResult?.finalStatus)}
          </Descriptions.Item>
          <Descriptions.Item label="导入行数">{result?.importedRows ?? 0}</Descriptions.Item>
          <Descriptions.Item label="隔离行数">{result?.quarantineCount ?? 0}</Descriptions.Item>
          <Descriptions.Item label="缺失评分">{result?.missingRatingCount ?? 0}</Descriptions.Item>
        </Descriptions>

        {(result?.missingRatingCount || 0) > 0 && (
          <Alert
            type="info"
            showIcon
            message="评分缺失已按缺失事实导入"
            description={`当前有 ${result?.missingRatingCount ?? 0} 条商品无评分，系统未伪造评分值，而是按缺失事实保留。`}
          />
        )}

        {!!result?.ratingIssueSamples?.length && (
          <Card size="small" title="评分问题样本（截取）">
            {result.ratingIssueSamples.map((item, index) => (
              <Paragraph key={`${item.row}-${index}`} style={{ marginBottom: 8 }}>
                <Text strong>行 {item.row}</Text>：
                <Text code>{String(item.ratingSourceColumn || 'n/a')}</Text>
                {' → '}
                原始值 <Text code>{String(item.ratingSourceRawValue ?? 'null')}</Text>
                {' / '}
                当前值 <Text code>{String(item.ratingValue ?? 'null')}</Text>
              </Paragraph>
            ))}
          </Card>
        )}

        <Space>
          <Button type="primary" onClick={onGoDashboard}>
            查看仪表盘
          </Button>
          <Button onClick={onContinueImport}>
            继续导入
          </Button>
        </Space>
      </Space>
    </Card>
  )
}
