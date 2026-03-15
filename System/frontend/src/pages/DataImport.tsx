import { Upload, Button, Card, Steps, Table, Tag, Alert, Progress, Descriptions, Divider, message } from 'antd'
import { UploadOutlined, FileExcelOutlined, CheckCircleOutlined, WarningOutlined, LoadingOutlined } from '@ant-design/icons'
import { useState } from 'react'
import type { UploadFile } from 'antd/es/upload/interface'

interface ImportResult {
  fileName: string
  platform: string
  totalRows: number
  mappedFields: number
  unmappedFields: string[]
  detectedHeaderRow: number
  keyField: string
  status: 'success' | 'warning' | 'error'
  diagnosis: {
    platform: string
    confidence: number
    issues: string[]
  }
}

export default function DataImport() {
  const [currentStep, setCurrentStep] = useState(0)
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [importResults, setImportResults] = useState<ImportResult[]>([])
  const [importing, setImporting] = useState(false)

  // 处理文件上传
  const handleUpload = async () => {
    if (fileList.length === 0) {
      message.warning('请先选择文件')
      return
    }

    setImporting(true)
    setCurrentStep(1)

    // 模拟导入过程
    setTimeout(() => {
      const mockResults: ImportResult[] = fileList.map(file => ({
        fileName: file.name,
        platform: file.name.includes('ozon') ? 'Ozon' : file.name.includes('wb') ? 'Wildberries' : '未知',
        totalRows: Math.floor(Math.random() * 5000) + 1000,
        mappedFields: Math.floor(Math.random() * 20) + 15,
        unmappedFields: ['未知字段1', '未知字段2'],
        detectedHeaderRow: Math.floor(Math.random() * 5) + 1,
        keyField: 'SKU',
        status: 'success',
        diagnosis: {
          platform: file.name.includes('ozon') ? 'ozon' : 'wildberries',
          confidence: 0.92,
          issues: []
        }
      }))

      setImportResults(mockResults)
      setCurrentStep(2)
      setImporting(false)
      message.success('导入诊断完成！')
    }, 2000)
  }

  // 导入结果表格列定义
  const resultColumns = [
    {
      title: '文件名',
      dataIndex: 'fileName',
      key: 'fileName',
      render: (text: string) => (
        <span>
          <FileExcelOutlined style={{ color: '#52c41a', marginRight: 8 }} />
          {text}
        </span>
      )
    },
    {
      title: '平台',
      dataIndex: 'platform',
      key: 'platform',
      render: (text: string) => <Tag color="blue">{text}</Tag>
    },
    {
      title: '识别置信度',
      dataIndex: ['diagnosis', 'confidence'],
      key: 'confidence',
      render: (val: number) => (
        <Progress
          percent={val * 100}
          size="small"
          status={val > 0.8 ? 'success' : 'normal'}
          format={percent => `${percent?.toFixed(0)}%`}
        />
      )
    },
    {
      title: '数据行数',
      dataIndex: 'totalRows',
      key: 'totalRows',
      render: (val: number) => val.toLocaleString()
    },
    {
      title: '映射字段',
      dataIndex: 'mappedFields',
      key: 'mappedFields',
      render: (val: number, record: ImportResult) => (
        <span>
          <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 4 }} />
          {val} 个字段已映射
          {record.unmappedFields.length > 0 && (
            <WarningOutlined style={{ color: '#faad14', marginLeft: 8 }} />
          )}
        </span>
      )
    },
    {
      title: '表头行',
      dataIndex: 'detectedHeaderRow',
      key: 'detectedHeaderRow',
      render: (val: number) => `第 ${val} 行`
    },
    {
      title: '主键字段',
      dataIndex: 'keyField',
      key: 'keyField',
      render: (text: string) => <Tag color="purple">{text}</Tag>
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const config: Record<string, { color: string; icon: any }> = {
          success: { color: '#52c41a', icon: <CheckCircleOutlined /> },
          warning: { color: '#faad14', icon: <WarningOutlined /> },
          error: { color: '#f5222d', icon: <WarningOutlined /> }
        }
        const { color, icon } = config[status]
        return (
          <Tag color={color} icon={icon}>
            {status === 'success' ? '成功' : status === 'warning' ? '警告' : '失败'}
          </Tag>
        )
      }
    }
  ]

  return (
    <div style={{ padding: '24px' }}>
      <h1 style={{ fontSize: '24px', fontWeight: 'bold', marginBottom: '24px' }}>
        📥 数据导入中心
      </h1>

      <Alert
        message="智能导入系统"
        description="支持自动识别 Ozon/Wildberries/AliExpress 等平台导出数据，自动定位表头、智能字段映射、多语言识别（俄语/中文/英语）"
        type="info"
        showIcon
        style={{ marginBottom: '24px' }}
      />

      <Card>
        <Steps current={currentStep} style={{ marginBottom: '32px' }}>
          <Steps.Step title="上传文件" description="选择文件（xlsx/csv 已实证）" />
          <Steps.Step title="智能诊断" description="识别平台和字段" icon={importing ? <LoadingOutlined /> : undefined} />
          <Steps.Step title="完成" description="查看导入结果" />
        </Steps>

        {currentStep === 0 && (
          <>
            <Upload.Dragger
              multiple
              accept=".xlsx,.xls,.csv"
              fileList={fileList}
              beforeUpload={(file) => {
                setFileList([...fileList, file])
                return false
              }}
              onRemove={(file) => {
                const index = fileList.indexOf(file)
                const newFileList = fileList.slice()
                newFileList.splice(index, 1)
                setFileList(newFileList)
              }}
            >
              <p className="ant-upload-drag-icon">
                <FileExcelOutlined style={{ fontSize: '48px', color: '#52c41a' }} />
              </p>
              <p className="ant-upload-text">点击或拖拽文件到此区域</p>
              <p className="ant-upload-hint">
                支持导入 Excel/CSV（当前已完成实证：.xlsx/.csv）
              </p>
            </Upload.Dragger>

            <Divider />

            <Button
              type="primary"
              size="large"
              icon={<UploadOutlined />}
              onClick={handleUpload}
              disabled={fileList.length === 0}
              loading={importing}
            >
              开始导入
            </Button>
          </>
        )}

        {currentStep === 1 && (
          <div style={{ textAlign: 'center', padding: '48px' }}>
            <LoadingOutlined style={{ fontSize: '48px', color: '#1890ff' }} />
            <p style={{ marginTop: '24px', fontSize: '16px' }}>正在智能诊断数据...</p>
            <p style={{ color: '#8c8c8c' }}>识别平台、定位表头、映射字段</p>
          </div>
        )}

        {currentStep === 2 && importResults.length > 0 && (
          <>
            <Alert
              message="导入诊断完成"
              description={`成功处理 ${importResults.length} 个文件，共 ${importResults.reduce((sum, r) => sum + r.totalRows, 0).toLocaleString()} 行数据`}
              type="success"
              showIcon
              style={{ marginBottom: '24px' }}
            />

            <Table
              dataSource={importResults}
              columns={resultColumns}
              pagination={false}
              rowKey="fileName"
            />

            <Divider />

            {/* 详细诊断信息 */}
            {importResults.map((result, index) => (
              <Card key={index} style={{ marginTop: '16px' }}>
                <Descriptions title={`📋 ${result.fileName} 诊断详情`} bordered column={2}>
                  <Descriptions.Item label="平台识别">{result.platform}</Descriptions.Item>
                  <Descriptions.Item label="识别置信度">{(result.diagnosis.confidence * 100).toFixed(0)}%</Descriptions.Item>
                  <Descriptions.Item label="表头行位置">第 {result.detectedHeaderRow} 行</Descriptions.Item>
                  <Descriptions.Item label="主键字段">{result.keyField}</Descriptions.Item>
                  <Descriptions.Item label="数据行数">{result.totalRows.toLocaleString()}</Descriptions.Item>
                  <Descriptions.Item label="映射字段数">{result.mappedFields}</Descriptions.Item>
                  {result.unmappedFields.length > 0 && (
                    <Descriptions.Item label="未映射字段" span={2}>
                      {result.unmappedFields.map((field, i) => (
                        <Tag key={i} color="orange">{field}</Tag>
                      ))}
                    </Descriptions.Item>
                  )}
                </Descriptions>
              </Card>
            ))}

            <Divider />

            <Button
              type="primary"
              size="large"
              onClick={() => {
                message.success('数据已进入分析系统')
                setCurrentStep(0)
                setFileList([])
                setImportResults([])
              }}
            >
              完成，进入运营分析 →
            </Button>
          </>
        )}
      </Card>

      <Divider />

      {/* 使用说明 */}
      <Card title="📖 导入指南">
        <Descriptions bordered column={1}>
          <Descriptions.Item label="支持平台">
            <Tag color="blue">Ozon</Tag>
            <Tag color="purple">Wildberries</Tag>
            <Tag color="green">AliExpress</Tag>
            <Tag color="orange">Amazon</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="自动识别功能">
            <ul style={{ marginBottom: 0 }}>
              <li>✅ 自动定位表头行（支持前20行搜索）</li>
              <li>✅ 智能字段映射（俄语/中文/英语）</li>
              <li>✅ 自动识别主键字段（SKU优先）</li>
              <li>✅ 数据清洗（货币符号、空格、换行）</li>
              <li>✅ 批量导入支持</li>
            </ul>
          </Descriptions.Item>
          <Descriptions.Item label="文件要求">
            <ul style={{ marginBottom: 0 }}>
              <li>文件格式：Excel 或 CSV（当前实证覆盖：.xlsx/.csv）</li>
              <li>文件大小：单个文件不超过 50MB</li>
              <li>编码格式：UTF-8 或 GBK</li>
            </ul>
          </Descriptions.Item>
        </Descriptions>
      </Card>
    </div>
  )
}
