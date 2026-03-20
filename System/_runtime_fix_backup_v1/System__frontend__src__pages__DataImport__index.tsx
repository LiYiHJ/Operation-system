import { useState } from 'react'
import { Upload, Button, Table, Tag, Progress, Card, Steps, Alert, Select, message, Modal, Space, Divider, Collapse } from 'antd'
import { UploadOutlined, CheckCircleOutlined, WarningOutlined, FileExcelOutlined, ReloadOutlined, QuestionCircleOutlined } from '@ant-design/icons'
import type { UploadFile } from 'antd/es/upload/interface'
import ReactECharts from 'echarts-for-react'

const { Dragger } = Upload
const { Panel } = Collapse

// ==================== 类型定义 ====================
interface FieldMapping {
  original: string
  standard: string | null
  confidence: number
  reasons: string[]
  status: 'success' | 'warning' | 'error'
}

interface DiagnosisResult {
  status: 'success' | 'partial' | 'failed'
  platform: string
  detected_header_row: number
  key_field: string | null
  mapped_fields: number
  unmapped_fields: number
  row_error_count: number
  suggestions: string[]
}

interface UploadResponse {
  upload_id: string
  file_name: string
  total_rows: number
  columns: string[]
  preview_rows: Record<string, any>[]
  auto_mapping: Record<string, {
    standard_name: string
    confidence: number
    reasons: string[]
  }>
  mapping_summary: {
    total_fields: number
    mapped_fields: number
    low_confidence_fields: number
  }
}

// ==================== 文件上传组件 ====================
function FileUploadStep({ 
  onUploadSuccess, 
  onUploadError 
}: { 
  onUploadSuccess: (data: UploadResponse) => void
  onUploadError: (error: string) => void
}) {
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [uploading, setUploading] = useState(false)
  const [fileInfo, setFileInfo] = useState<any>(null)

  const uploadProps = {
    name: 'file',
    multiple: false,
    accept: '.xlsx,.csv,.json',
    fileList,
    beforeUpload: (file: UploadFile) => {
      // 文件大小检查（10MB）
      const isLt10M = (file.size as number) / 1024 / 1024 < 10
      if (!isLt10M) {
        message.error('文件大小不能超过 10MB!')
        return false
      }

      // 文件类型检查
      const isValidType = file.name.endsWith('.xlsx') || 
                          file.name.endsWith('.csv') || 
                          file.name.endsWith('.json')
      if (!isValidType) {
        message.error('仅支持 .xlsx / .csv / .json 格式!')
        return false
      }

      setFileList([file])
      
      // 显示文件信息
      setFileInfo({
        name: file.name,
        size: ((file.size as number) / 1024).toFixed(2) + ' KB',
        type: file.name.split('.').pop()?.toUpperCase()
      })

      return false // 阻止自动上传
    },
    onRemove: () => {
      setFileList([])
      setFileInfo(null)
    }
  }

  const handleUpload = async () => {
    if (fileList.length === 0) {
      message.warning('请先选择文件')
      return
    }

    setUploading(true)
    const formData = new FormData()
    formData.append('file', fileList[0] as any)

    try {
      const response = await fetch('http://localhost:5000/api/import/upload', {
        method: 'POST',
        body: formData
      })

      if (!response.ok) {
        throw new Error('上传失败')
      }

      const result = await response.json()
      
      if (result.success) {
        message.success('文件上传成功！')
        onUploadSuccess(result.data)
      } else {
        throw new Error(result.message || '上传失败')
      }
    } catch (error: any) {
      message.error(`上传失败: ${error.message}`)
      onUploadError(error.message)
    } finally {
      setUploading(false)
    }
  }

  return (
    <div>
      <Alert
        message="支持的文件格式"
        description={
          <div>
            <p>✅ Excel 文件: .xlsx（当前已完成实证）</p>
            <p>✅ CSV 文件: .csv（当前已完成实证）</p>
            <p>⚠️ JSON 文件: .json（能力存在，待真实样本验证）</p>
            <p>📏 最大文件大小: 10MB</p>
            <p>📊 最大行数: 1,000 行（演示限制）</p>
          </div>
        }
        type="info"
        showIcon
        style={{ marginBottom: '24px' }}
      />

      <Dragger {...uploadProps} style={{ marginBottom: '24px' }}>
        <p className="ant-upload-drag-icon">
          <FileExcelOutlined style={{ fontSize: '48px', color: '#52c41a' }} />
        </p>
        <p className="ant-upload-text" style={{ fontSize: '16px', marginBottom: '8px' }}>
          点击或拖拽文件到此区域上传
        </p>
        <p className="ant-upload-hint" style={{ fontSize: '14px', color: '#8c8c8c' }}>
          支持 .xlsx / .csv / .json 格式，最大 10MB
        </p>
      </Dragger>

      {fileInfo && (
        <Card 
          size="small" 
          style={{ marginBottom: '24px', background: '#fafafa' }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <Space>
                <FileExcelOutlined style={{ fontSize: '20px', color: '#52c41a' }} />
                <span style={{ fontWeight: 500 }}>{fileInfo.name}</span>
                <Tag color="blue">{fileInfo.type}</Tag>
              </Space>
            </div>
            <div style={{ color: '#8c8c8c' }}>
              文件大小: {fileInfo.size}
            </div>
          </div>
        </Card>
      )}

      <div style={{ textAlign: 'center' }}>
        <Button
          type="primary"
          size="large"
          onClick={handleUpload}
          loading={uploading}
          disabled={fileList.length === 0}
          icon={<UploadOutlined />}
          style={{ minWidth: '200px' }}
        >
          {uploading ? '上传中...' : '开始导入'}
        </Button>
      </div>

      {/* 常见问题 */}
      <Divider>常见问题</Divider>
      <Collapse accordion>
        <Panel header="❓ 文件应该包含哪些字段？" key="1">
          <p>建议包含以下字段（俄语/中文/英文均可）：</p>
          <ul>
            <li><strong>SKU/Артикул</strong> - 产品编号（必需）</li>
            <li><strong>展示量/Показы</strong> - 产品浏览量</li>
            <li><strong>订单数/Кол-во заказов</strong> - 订单数量</li>
            <li><strong>销售额/Заказано на сумму</strong> - 销售金额</li>
            <li><strong>评分/Рейтинг</strong> - 产品评分</li>
            <li><strong>库存/Остаток</strong> - 库存数量</li>
          </ul>
        </Panel>
        <Panel header="❓ 为什么上传失败？" key="2">
          <p>常见失败原因：</p>
          <ul>
            <li>文件格式不正确（仅支持 .xlsx/.csv/.json）</li>
            <li>文件大小超过 10MB</li>
            <li>文件编码不是 UTF-8（CSV 文件）</li>
            <li>文件损坏或无法读取</li>
            <li>缺少必需字段（SKU/Артикул）</li>
          </ul>
        </Panel>
        <Panel header="❓ 数据会被保存吗？" key="3">
          <p>数据安全说明：</p>
          <ul>
            <li>✅ 数据仅用于分析，不会被永久保存</li>
            <li>✅ 数据不会传输到第三方服务器</li>
            <li>✅ 上传的数据仅在当前会话中使用</li>
            <li>✅ 关闭浏览器后数据将自动清除</li>
          </ul>
        </Panel>
      </Collapse>
    </div>
  )
}

// ==================== 字段映射组件 ====================
function FieldMappingStep({ 
  uploadData,
  onConfirm,
  onBack
}: { 
  uploadData: UploadResponse
  onConfirm: (mapping: Record<string, string>) => void
  onBack: () => void
}) {
  const [fieldMappings, setFieldMappings] = useState<Record<string, string>>({})
  const [mappingDetails, setMappingDetails] = useState<FieldMapping[]>([])

  // 初始化映射
  useState(() => {
    const mappings: FieldMapping[] = []
    const mappingObj: Record<string, string> = {}

    Object.entries(uploadData.auto_mapping).forEach(([original, info]) => {
      const confidence = info.confidence
      let status: 'success' | 'warning' | 'error' = 'error'
      
      if (confidence >= 0.7) status = 'success'
      else if (confidence >= 0.5) status = 'warning'

      mappings.push({
        original,
        standard: info.standard_name,
        confidence,
        reasons: info.reasons,
        status
      })

      if (info.standard_name) {
        mappingObj[original] = info.standard_name
      }
    })

    setMappingDetails(mappings)
    setFieldMappings(mappingObj)
  })

  // 标准字段选项
  const standardFieldOptions = [
    { value: 'sku', label: 'SKU' },
    { value: 'name', label: '产品名称' },
    { value: 'impressions', label: '展示量' },
    { value: 'orders', label: '订单数' },
    { value: 'revenue', label: '销售额' },
    { value: 'rating', label: '评分' },
    { value: 'stock', label: '库存' },
    { value: 'add_to_cart', label: '加购数' },
    { value: 'ad_spend', label: '广告花费' },
    { value: 'conversion_rate', label: '转化率' }
  ]

  const handleFieldChange = (original: string, standard: string) => {
    setFieldMappings(prev => ({
      ...prev,
      [original]: standard
    }))
  }

  const columns = [
    {
      title: '原始字段名',
      dataIndex: 'original',
      key: 'original',
      width: '25%',
      render: (text: string) => (
        <span style={{ fontWeight: 500, fontFamily: 'monospace' }}>{text}</span>
      )
    },
    {
      title: '标准字段名',
      dataIndex: 'standard',
      key: 'standard',
      width: '30%',
      render: (standard: string | null, record: FieldMapping) => (
        <Select
          value={fieldMappings[record.original] || standard}
          onChange={(value) => handleFieldChange(record.original, value)}
          style={{ width: '100%' }}
          placeholder="请选择字段"
          allowClear
          showSearch
          options={standardFieldOptions}
        />
      )
    },
    {
      title: '置信度',
      dataIndex: 'confidence',
      key: 'confidence',
      width: '20%',
      render: (confidence: number, record: FieldMapping) => (
        <div>
          <Progress 
            percent={Math.round(confidence * 100)}
            size="small"
            status={confidence >= 0.7 ? 'success' : confidence >= 0.5 ? 'normal' : 'exception'}
            format={(percent) => `${percent}%`}
          />
        </div>
      )
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: '15%',
      render: (status: string) => {
        const statusConfig = {
          success: { color: 'green', icon: <CheckCircleOutlined />, text: '✅ 高置信' },
          warning: { color: 'orange', icon: <WarningOutlined />, text: '⚠️ 需确认' },
          error: { color: 'red', icon: <WarningOutlined />, text: '❌ 低置信' }
        }
        const config = statusConfig[status]
        return (
          <Tag color={config.color} icon={config.icon}>
            {config.text}
          </Tag>
        )
      }
    },
    {
      title: '匹配原因',
      dataIndex: 'reasons',
      key: 'reasons',
      width: '10%',
      render: (reasons: string[]) => (
        <Button 
          type="link" 
          size="small"
          onClick={() => {
            Modal.info({
              title: '匹配详情',
              content: (
                <div>
                  {reasons.map((reason, index) => (
                    <p key={index}>• {reason}</p>
                  ))}
                </div>
              )
            })
          }}
        >
          查看
        </Button>
      )
    }
  ]

  // 统计信息
  const highConfidence = mappingDetails.filter(m => m.confidence >= 0.7).length
  const lowConfidence = mappingDetails.filter(m => m.confidence < 0.5).length

  return (
    <div>
      {/* 统计信息 */}
      <Card style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-around', textAlign: 'center' }}>
          <div>
            <div style={{ fontSize: '32px', fontWeight: 700, color: '#52c41a' }}>
              {highConfidence}
            </div>
            <div style={{ color: '#8c8c8c' }}>高置信度</div>
          </div>
          <Divider type="vertical" style={{ height: '60px' }} />
          <div>
            <div style={{ fontSize: '32px', fontWeight: 700, color: '#faad14' }}>
              {mappingDetails.length - highConfidence - lowConfidence}
            </div>
            <div style={{ color: '#8c8c8c' }}>需确认</div>
          </div>
          <Divider type="vertical" style={{ height: '60px' }} />
          <div>
            <div style={{ fontSize: '32px', fontWeight: 700, color: '#ff4d4f' }}>
              {lowConfidence}
            </div>
            <div style={{ color: '#8c8c8c' }}>低置信度</div>
          </div>
        </div>
      </Card>

      {/* 置信度分布图 */}
      <Card style={{ marginBottom: '24px' }}>
        <ReactECharts
          option={{
            title: { text: '字段映射置信度分布', left: 'center' },
            tooltip: { trigger: 'item' },
            series: [{
              type: 'pie',
              radius: ['40%', '70%'],
              data: [
                { value: highConfidence, name: '高置信度 (≥70%)', itemStyle: { color: '#52c41a' } },
                { value: mappingDetails.length - highConfidence - lowConfidence, name: '中等置信度 (50-70%)', itemStyle: { color: '#faad14' } },
                { value: lowConfidence, name: '低置信度 (<50%)', itemStyle: { color: '#ff4d4f' } }
              ]
            }]
          }}
          style={{ height: '250px' }}
        />
      </Card>

      {/* 映射表格 */}
      <Card title="字段映射详情" style={{ marginBottom: '24px' }}>
        <Table
          dataSource={mappingDetails}
          columns={columns}
          pagination={false}
          rowKey="original"
          scroll={{ y: 400 }}
        />
      </Card>

      {/* 操作按钮 */}
      <div style={{ textAlign: 'center', marginTop: '24px' }}>
        <Space size="large">
          <Button size="large" onClick={onBack}>
            返回上一步
          </Button>
          <Button 
            type="primary" 
            size="large"
            onClick={() => onConfirm(fieldMappings)}
            icon={<CheckCircleOutlined />}
          >
            确认映射
          </Button>
        </Space>
      </div>
    </div>
  )
}

// ==================== 主组件 ====================
export default function DataImport() {
  const [currentStep, setCurrentStep] = useState(0)
  const [uploadData, setUploadData] = useState<UploadResponse | null>(null)
  const [diagnosisResult, setDiagnosisResult] = useState<DiagnosisResult | null>(null)

  const steps = [
    { title: '文件上传', description: '上传数据文件' },
    { title: '字段映射', description: '确认字段映射' },
    { title: '诊断报告', description: '查看导入结果' },
    { title: '完成', description: '导入成功' }
  ]

  const handleUploadSuccess = (data: UploadResponse) => {
    setUploadData(data)
    setCurrentStep(1)
  }

  const handleUploadError = (error: string) => {
    console.error('Upload error:', error)
  }

  const handleMappingConfirm = async (mapping: Record<string, string>) => {
    if (!uploadData) return

    try {
      const response = await fetch('http://localhost:5000/api/import/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          upload_id: uploadData.upload_id,
          field_mapping: mapping
        })
      })

      const result = await response.json()
      
      if (result.success) {
        setDiagnosisResult(result.data.diagnosis)
        setCurrentStep(2)
        message.success('字段映射确认成功！')
      } else {
        throw new Error(result.message)
      }
    } catch (error: any) {
      message.error(`确认失败: ${error.message}`)
    }
  }

  const handleComplete = () => {
    setCurrentStep(3)
  }

  const renderStepContent = () => {
    switch (currentStep) {
      case 0:
        return (
          <FileUploadStep 
            onUploadSuccess={handleUploadSuccess}
            onUploadError={handleUploadError}
          />
        )
      case 1:
        return uploadData ? (
          <FieldMappingStep 
            uploadData={uploadData}
            onConfirm={handleMappingConfirm}
            onBack={() => setCurrentStep(0)}
          />
        ) : null
      case 2:
        return diagnosisResult ? (
          <DiagnosisStep 
            diagnosis={diagnosisResult}
            onComplete={handleComplete}
            onBack={() => setCurrentStep(1)}
          />
        ) : null
      case 3:
        return <SuccessStep />
      default:
        return null
    }
  }

  return (
    <div style={{ padding: '24px', background: '#f0f2f5', minHeight: '100vh' }}>
      <Card>
        {/* 步骤指示器 */}
        <Steps 
          current={currentStep} 
          items={steps}
          style={{ marginBottom: '32px' }}
        />

        {/* 步骤内容 */}
        <div style={{ minHeight: '500px' }}>
          {renderStepContent()}
        </div>
      </Card>
    </div>
  )
}

// ==================== 诊断报告组件 ====================
function DiagnosisStep({ 
  diagnosis,
  onComplete,
  onBack
}: {
  diagnosis: DiagnosisResult
  onComplete: () => void
  onBack: () => void
}) {
  const statusConfig = {
    success: { color: 'green', text: '✅ 成功' },
    partial: { color: 'orange', text: '⚠️ 部分成功' },
    failed: { color: 'red', text: '❌ 失败' }
  }

  const config = statusConfig[diagnosis.status]

  return (
    <div>
      <Alert
        message={`导入状态: ${config.text}`}
        description={
          <div>
            <p>✅ 平台: {diagnosis.platform}</p>
            <p>✅ 表头行: 第 {diagnosis.detected_header_row} 行</p>
            <p>✅ 主键字段: {diagnosis.key_field || '未识别'}</p>
            <p>⚠️ 映射字段: {diagnosis.mapped_fields}/{diagnosis.mapped_fields + diagnosis.unmapped_fields}</p>
            {diagnosis.row_error_count > 0 && (
              <p>⚠️ 数据错误: {diagnosis.row_error_count} 行</p>
            )}
          </div>
        }
        type={diagnosis.status === 'success' ? 'success' : diagnosis.status === 'partial' ? 'warning' : 'error'}
        showIcon
        style={{ marginBottom: '24px' }}
      />

      {/* 建议 */}
      {diagnosis.suggestions.length > 0 && (
        <Card title="💡 建议" style={{ marginBottom: '24px' }}>
          <ul>
            {diagnosis.suggestions.map((suggestion, index) => (
              <li key={index}>{suggestion}</li>
            ))}
          </ul>
        </Card>
      )}

      {/* 操作按钮 */}
      <div style={{ textAlign: 'center', marginTop: '24px' }}>
        <Space size="large">
          <Button size="large" onClick={onBack}>
            返回修改
          </Button>
          <Button 
            type="primary" 
            size="large"
            onClick={onComplete}
          >
            继续导入
          </Button>
        </Space>
      </div>
    </div>
  )
}

// ==================== 成功组件 ====================
function SuccessStep() {
  return (
    <div style={{ textAlign: 'center', padding: '60px 20px' }}>
      <CheckCircleOutlined 
        style={{ 
          fontSize: '80px', 
          color: '#52c41a', 
          marginBottom: '24px' 
        }} 
      />
      <h1 style={{ fontSize: '28px', marginBottom: '16px' }}>
        ✅ 数据导入成功！
      </h1>
      <p style={{ fontSize: '16px', color: '#8c8c8c', marginBottom: '32px' }}>
        数据已成功导入系统，现在您可以开始分析了
      </p>
      <Space size="large">
        <Button 
          type="primary" 
          size="large"
          onClick={() => window.location.href = '/dashboard'}
        >
          查看仪表盘
        </Button>
        <Button 
          size="large"
          onClick={() => window.location.reload()}
        >
          继续导入
        </Button>
      </Space>
    </div>
  )
}
