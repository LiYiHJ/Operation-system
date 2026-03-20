import React from 'react'
import { Card, Space, Spin, Typography } from 'antd'

const { Title, Paragraph } = Typography

export default function ImportParsingStep() {
  return (
    <Card>
      <Space direction="vertical" style={{ width: '100%', alignItems: 'center' }}>
        <Spin size="large" />
        <Title level={4} style={{ marginBottom: 0 }}>
          正在智能解析文件...
        </Title>
        <Paragraph type="secondary" style={{ marginBottom: 0 }}>
          正在执行：文件识别 → 表头分析 → 字段映射 → suggestion 生成
        </Paragraph>
      </Space>
    </Card>
  )
}
