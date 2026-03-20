import React from 'react'
import { Alert, Button, Card, Space, Typography, Upload, message } from 'antd'
import { UploadOutlined } from '@ant-design/icons'
import type { UploadFile } from 'antd/es/upload/interface'

const { Dragger } = Upload
const { Title, Paragraph } = Typography

type Props = {
  fileList: UploadFile[]
  selectedFile: File | null
  importing: boolean
  onSyncFileList: (nextList: UploadFile[]) => void
  onHandleUpload: () => void
}

export default function ImportUploadStep({
  fileList,
  selectedFile,
  importing,
  onSyncFileList,
  onHandleUpload,
}: Props) {
  return (
    <Card>
      <Title level={4}>导入文件</Title>
      <Paragraph type="secondary">
        当前入口已接入：建议式 SKU 识别、人工确认导入，以及缺失评分审计。
      </Paragraph>

      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="当前导入能力"
        description={
          <div>
            <div>• 已完成实证：xlsx / csv</div>
            <div>• 支持字段智能映射与人工调整</div>
            <div>• 支持 entityKeySuggestion → manualOverrides → confirm 闭环</div>
            <div>• 评分缺失会计入 missingRatingCount，不会伪造评分值</div>
          </div>
        }
      />

      <Dragger
        fileList={fileList}
        maxCount={1}
        beforeUpload={(file) => {
          const isLt50M = file.size / 1024 / 1024 < 50
          if (!isLt50M) {
            message.error('文件大小不能超过 50MB')
            return Upload.LIST_IGNORE
          }
          onSyncFileList([file as UploadFile])
          return false
        }}
        onChange={({ fileList: nextList }) => onSyncFileList(nextList)}
        onRemove={() => {
          onSyncFileList([])
          return true
        }}
      >
        <p className="ant-upload-drag-icon">
          <UploadOutlined />
        </p>
        <p className="ant-upload-text">点击或拖拽文件到此区域</p>
        <p className="ant-upload-hint">支持 xlsx / csv，单文件不超过 50MB</p>
      </Dragger>

      <Space style={{ marginTop: 16 }}>
        <Button type="primary" onClick={onHandleUpload} disabled={!selectedFile} loading={importing}>
          开始解析
        </Button>
      </Space>
    </Card>
  )
}
