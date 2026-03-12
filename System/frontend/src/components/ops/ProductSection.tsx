import { Alert, Button, Card, Empty, Space, Tag, Typography } from 'antd'
import type { ReactNode } from 'react'

const { Title, Text } = Typography

export function OpsPageHeader({ title, subtitle, extra }: { title: string; subtitle: string; extra?: ReactNode }) {
  return (
    <Card style={{ marginBottom: 16 }} bodyStyle={{ padding: 16 }}>
      <Space direction="vertical" size={4} style={{ width: '100%' }}>
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <Title level={3} style={{ margin: 0 }}>{title}</Title>
          {extra}
        </Space>
        <Text type="secondary">{subtitle}</Text>
      </Space>
    </Card>
  )
}

export function OpsConclusion({ title, desc, actionText, onAction, level = 'warning' }: { title: string; desc: string; actionText?: string; onAction?: () => void; level?: 'error'|'warning'|'info'|'success' }) {
  return (
    <Alert
      showIcon
      type={level}
      message={title}
      description={
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <span>{desc}</span>
          {actionText ? <Button type="primary" size="small" onClick={onAction}>{actionText}</Button> : null}
        </Space>
      }
    />
  )
}

export function OpsRiskTag({ level }: { level?: string }) {
  const map: Record<string, { color: string; text: string }> = {
    critical: { color: 'red', text: '紧急' },
    high: { color: 'red', text: '高风险' },
    warning: { color: 'orange', text: '警告' },
    medium: { color: 'orange', text: '中风险' },
    normal: { color: 'green', text: '正常' },
    low: { color: 'green', text: '低风险' },
  }
  const c = map[(level || '').toLowerCase()] || { color: 'default', text: level || '未知' }
  return <Tag color={c.color}>{c.text}</Tag>
}

export function OpsStatusTag({ status }: { status?: string }) {
  const map: Record<string, { color: string; text: string }> = {
    pending: { color: 'orange', text: '待处理' },
    in_progress: { color: 'blue', text: '执行中' },
    completed: { color: 'green', text: '已完成' },
    cancelled: { color: 'default', text: '已取消' },
    '已回写': { color: 'green', text: '已回写' },
    '未回写': { color: 'default', text: '未回写' },
  }
  const c = map[status || ''] || { color: 'default', text: status || '未知' }
  return <Tag color={c.color}>{c.text}</Tag>
}

export function OpsEmpty({ text = '暂无数据' }: { text?: string }) {
  return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={text} />
}
