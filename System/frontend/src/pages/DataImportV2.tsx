import { Upload, Button, Card, Steps, Table, Tag, Alert, Progress, Descriptions, Divider, message, Select, Space, Tabs, Tooltip, Badge, Row, Col, Statistic } from 'antd'
import {
  UploadOutlined, FileExcelOutlined, CheckCircleOutlined, WarningOutlined,
  LoadingOutlined, SaveOutlined, EyeOutlined, DatabaseOutlined
} from '@ant-design/icons'
import { useState } from 'react'
import type { UploadFile } from 'antd/es/upload/interface'
import { importApi } from '../services/api'
import type { ImportResult, FieldMapping, ConfirmImportResponse } from '../types'

// 标准字段定义（参考 C:\strategy-system）
const STANDARD_FIELDS = {
  // 基础信息
  sku: { name: 'SKU', category: '基础', required: true, description: '商品唯一标识' },
  product_name: { name: '商品名称', category: '基础', required: false },
  category: { name: '类目', category: '基础', required: false },

  // 销售数据
  orders: { name: '订单数', category: '销售', required: false },
  revenue: { name: '销售额', category: '销售', required: false },
  units: { name: '销量', category: '销售', required: false },

  // 流量数据
  impressions: { name: '展示量', category: '流量', required: false },
  clicks: { name: '点击量', category: '流量', required: false },
  ctr: { name: '点击率', category: '流量', required: false },
  card_visits: { name: '商品页访问', category: '流量', required: false },

  // 转化数据
  add_to_cart: { name: '加购数', category: '转化', required: false },
  add_to_cart_rate: { name: '加购率', category: '转化', required: false },
  conversion_rate: { name: '转化率', category: '转化', required: false },

  // 价格数据
  sale_price: { name: '售价', category: '价格', required: false },
  list_price: { name: '原价', category: '价格', required: false },
  market_price: { name: '市场价', category: '价格', required: false },
  discount: { name: '折扣', category: '价格', required: false },

  // 库存数据
  stock_total: { name: '总库存', category: '库存', required: false },
  stock_fbo: { name: 'FBO库存', category: '库存', required: false },
  stock_fbs: { name: 'FBS库存', category: '库存', required: false },
  days_of_supply: { name: '库存天数', category: '库存', required: false },

  // 评价数据
  rating: { name: '评分', category: '评价', required: false },
  reviews_count: { name: '评价数', category: '评价', required: false },
  return_rate: { name: '退货率', category: '评价', required: false },
  cancel_rate: { name: '取消率', category: '评价', required: false },

  // 广告数据
  ad_spend: { name: '广告花费', category: '广告', required: false },
  ad_revenue: { name: '广告收入', category: '广告', required: false },
  roas: { name: 'ROAS', category: '广告', required: false },
  cpc: { name: 'CPC', category: '广告', required: false },

  // 成本数据
  cost_price: { name: '成本价', category: '成本', required: false },
  commission_rate: { name: '佣金率', category: '成本', required: false },
  logistics_cost: { name: '物流成本', category: '成本', required: false },
}


export default function DataImportV2() {
  const [currentStep, setCurrentStep] = useState(0)
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [importResult, setImportResult] = useState<ImportResult | null>(null)
  const [importing, setImporting] = useState(false)
  const [savedTemplates, setSavedTemplates] = useState<any[]>([])

  const normalizeRawFile = (uploadFile?: UploadFile): File | null => {
    if (!uploadFile) return null
    const raw = uploadFile.originFileObj
    if (raw instanceof File) return raw
    return null
  }

  const syncSelectedFile = (nextList: UploadFile[]) => {
    setFileList(nextList)
    setSelectedFile(normalizeRawFile(nextList[0]))
  }

  // 处理文件上传
  const handleUpload = async () => {
    if (!selectedFile) {
      message.warning('请先选择文件')
      return
    }

    setImporting(true)
    setCurrentStep(1)

    try {
      const result = await importApi.uploadFile(selectedFile, 1)
      setImportResult(result)
      setCurrentStep(2)
      message.success('文件解析成功！')
    } catch (error: any) {
      message.error(`解析失败: ${error.message}`)
      setCurrentStep(0)
    } finally {
      setImporting(false)
    }
  }

  // 手动调整映射
  const handleManualMapping = (index: number, newStandardField: string | null) => {
    if (!importResult) return

    const newMappings = [...importResult.fieldMappings]
    newMappings[index] = {
      ...newMappings[index],
      standardField: newStandardField,
      isManual: true,
      confidence: 1.0
    }

    setImportResult({
      ...importResult,
      fieldMappings: newMappings,
      mappedCount: newMappings.filter(m => !!m.standardField && m.standardField !== 'unmapped').length,
      unmappedCount: newMappings.filter(m => !m.standardField || m.standardField === 'unmapped').length
    })

    message.success('映射已更新')
  }

  // 保存映射模板
  const saveTemplate = () => {
    if (!importResult) return

    const templateName = `模板_${new Date().toLocaleString()}`
    const template = {
      name: templateName,
      platform: importResult.platform,
      mappings: importResult.fieldMappings,
      createdAt: new Date().toISOString()
    }

    setSavedTemplates([...savedTemplates, template])
    message.success(`模板 "${templateName}" 已保存`)
  }

  // 应用模板
  const applyTemplate = (template: any) => {
    if (!importResult) return

    setImportResult({
      ...importResult,
      fieldMappings: template.mappings,
      mappedCount: template.mappings.filter((m: FieldMapping) => !!m.standardField && m.standardField !== 'unmapped').length,
      unmappedCount: template.mappings.filter((m: FieldMapping) => !m.standardField || m.standardField === 'unmapped').length
    })

    message.success(`模板 "${template.name}" 已应用`)
  }

  // 确认导入
  const confirmImport = async () => {
    if (!importResult) return

    setImporting(true)

    try {
      const result: ConfirmImportResponse = await importApi.confirmImport({
        sessionId: importResult.sessionId,
        shopId: 1,
        manualOverrides: importResult.fieldMappings,
      })

      if (result.status === 'success') {
        message.success(`成功导入 ${result.importedRows} 条数据！`)
        setCurrentStep(3)
      } else {
        throw new Error(result.errors?.[0] || '导入失败')
      }
    } catch (error: any) {
      message.error(`导入失败: ${error.message}`)
    } finally {
      setImporting(false)
    }
  }

  // 渲染步骤
  const renderStepContent = () => {
    switch (currentStep) {
      case 0:
        return renderUploadStep()
      case 1:
        return renderParsingStep()
      case 2:
        return renderMappingStep()
      case 3:
        return renderCompleteStep()
      default:
        return null
    }
  }

  // 步骤0: 上传文件
  const renderUploadStep = () => (
    <div>
      <Alert
        message="智能数据导入系统"
        description={
          <div>
            <p>✅ 支持 Excel (.xlsx, .xls)、CSV、JSON 格式</p>
            <p>✅ 自动识别 Ozon/Wildberries/AliExpress/Amazon 等平台</p>
            <p>✅ 智能字段映射（支持俄语/中文/英语）</p>
            <p>✅ 手动调整映射（针对特殊格式）</p>
            <p>✅ 保存映射模板（下次导入直接使用）</p>
          </div>
        }
        type="info"
        showIcon
        style={{ marginBottom: '24px' }}
      />

      <Upload.Dragger
        multiple={false}
        accept=".xlsx,.xls,.csv,.json"
        fileList={fileList}
        beforeUpload={(file) => {
          // 检查文件大小
          const isLt50M = file.size / 1024 / 1024 < 50
          if (!isLt50M) {
            message.error('文件大小不能超过 50MB！')
            return false
          }

          syncSelectedFile([file as UploadFile])
          return false
        }}
        onChange={({ fileList: nextList }) => {
          syncSelectedFile(nextList)
        }}
        onRemove={() => {
          syncSelectedFile([])
          return true
        }}
      >
        <p className="ant-upload-drag-icon">
          <FileExcelOutlined style={{ fontSize: '48px', color: '#52c41a' }} />
        </p>
        <p className="ant-upload-text">点击或拖拽文件到此区域</p>
        <p className="ant-upload-hint">
          支持 Excel (.xlsx, .xls)、CSV、JSON，单个文件不超过 50MB
        </p>
      </Upload.Dragger>

      <Divider />

      <Button
        type="primary"
        size="large"
        icon={<UploadOutlined />}
        onClick={handleUpload}
        disabled={!selectedFile}
        loading={importing}
      >
        开始解析文件
      </Button>
    </div>
  )

  // 步骤1: 解析中
  const renderParsingStep = () => (
    <div style={{ textAlign: 'center', padding: '48px' }}>
      <LoadingOutlined style={{ fontSize: '48px', color: '#1890ff' }} />
      <p style={{ marginTop: '24px', fontSize: '16px' }}>正在智能解析文件...</p>
      <p style={{ color: '#8c8c8c' }}>识别格式 → 检测表头 → 智能字段映射</p>
    </div>
  )

  // 步骤2: 字段映射
  const renderMappingStep = () => {
    if (!importResult) return null

    const columns = [
      {
        title: '原始字段',
        dataIndex: 'originalField',
        key: 'originalField',
        width: 200,
        render: (text: string) => (
          <Space>
            <DatabaseOutlined />
            <strong>{text}</strong>
          </Space>
        )
      },
      {
        title: '样本值',
        dataIndex: 'sampleValues',
        key: 'sampleValues',
        width: 250,
        render: (values: any[]) => (
          <Tooltip title={values.slice(0, 5).join(', ')}>
            <span style={{ color: '#8c8c8c', fontSize: '12px' }}>
              {values.slice(0, 3).join(', ')}{values.length > 3 ? '...' : ''}
            </span>
          </Tooltip>
        )
      },
      {
        title: '映射到',
        dataIndex: 'standardField',
        key: 'standardField',
        width: 200,
        render: (field: string, _: any, index: number) => {
          const standardField = STANDARD_FIELDS[field as keyof typeof STANDARD_FIELDS]

          return (
            <Select
              value={field}
              onChange={(value) => handleManualMapping(index, value)}
              style={{ width: '100%' }}
              showSearch
              filterOption={(input, option) =>
                String(option?.label).toLowerCase().includes(input.toLowerCase())
              }
            >
              <Select.Option key="unmapped" value="unmapped">
                <WarningOutlined style={{ color: '#faad14' }} /> 不映射
              </Select.Option>

              {Object.entries(STANDARD_FIELDS).map(([key, config]) => (
                <Select.Option
                  key={key}
                  value={key}
                  label={`${config.name} (${config.category})`}
                >
                  <Space>
                    {config.required && <Badge color="red" />}
                    <Tag color="blue">{config.category}</Tag>
                    {config.name}
                  </Space>
                </Select.Option>
              ))}
            </Select>
          )
        }
      },
      {
        title: '置信度',
        dataIndex: 'confidence',
        key: 'confidence',
        width: 120,
        render: (val: number, record: FieldMapping) => (
          <Progress
            percent={val * 100}
            size="small"
            status={record.isManual ? 'success' : val > 0.7 ? 'success' : val > 0.5 ? 'normal' : 'exception'}
            format={percent => `${percent?.toFixed(0)}%`}
          />
        )
      },
      {
        title: '状态',
        key: 'status',
        width: 80,
        render: (_: any, record: FieldMapping) => (
          record.isManual ? (
            <Tag color="blue">手动</Tag>
          ) : record.standardField !== 'unmapped' ? (
            <Tag color="green">自动</Tag>
          ) : (
            <Tag color="orange">未映射</Tag>
          )
        )
      }
    ]

    return (
      <div>
        {/* 统计卡片 */}
        <Row gutter={16} style={{ marginBottom: '24px' }}>
          <Col span={6}>
            <Card>
              <Statistic
                title="总字段数"
                value={importResult.fieldMappings.length}
                prefix={<DatabaseOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="已映射"
                value={importResult.mappedCount}
                valueStyle={{ color: '#52c41a' }}
                prefix={<CheckCircleOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="未映射"
                value={importResult.unmappedCount}
                valueStyle={{ color: importResult.unmappedCount > 0 ? '#faad14' : '#52c41a' }}
                prefix={<WarningOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="整体置信度"
                value={importResult.confidence * 100}
                precision={1}
                suffix="%"
                valueStyle={{
                  color: importResult.confidence > 0.7 ? '#52c41a' : importResult.confidence > 0.5 ? '#faad14' : '#f5222d'
                }}
              />
            </Card>
          </Col>
        </Row>

        {/* 文件信息 */}
        <Card style={{ marginBottom: '24px' }}>
          <Descriptions bordered column={4}>
            <Descriptions.Item label="文件名">{importResult.fileName}</Descriptions.Item>
            <Descriptions.Item label="平台">
              <Tag color="blue">{importResult.platform}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="数据行数">{importResult.totalRows.toLocaleString()}</Descriptions.Item>
            <Descriptions.Item label="字段数">{importResult.totalColumns}</Descriptions.Item>
            <Descriptions.Item label="表头行">第 {importResult.headerRow} 行</Descriptions.Item>
            <Descriptions.Item label="Sheet" span={3}>
              {importResult.sheetNames.map(name => (
                <Tag key={name} color={name === importResult.selectedSheet ? 'blue' : 'default'}>
                  {name}
                </Tag>
              ))}
            </Descriptions.Item>
          </Descriptions>
        </Card>

        {/* 工具栏 */}
        <Space style={{ marginBottom: '16px' }}>
          <Button icon={<SaveOutlined />} onClick={saveTemplate}>
            保存映射模板
          </Button>

          {savedTemplates.length > 0 && (
            <Select
              placeholder="应用已保存的模板"
              style={{ width: 250 }}
              onSelect={(index) => applyTemplate(savedTemplates[index])}
            >
              {savedTemplates.map((template, index) => (
                <Select.Option key={index} value={index}>
                  {template.name} ({template.platform})
                </Select.Option>
              ))}
            </Select>
          )}

          <Button icon={<EyeOutlined />}>
            预览数据
          </Button>
        </Space>

        {/* 字段映射表格 */}
        <Card title="字段映射调整" extra={<Tag color="blue">点击"映射到"列可手动调整</Tag>}>
          <Table
            dataSource={importResult.fieldMappings}
            columns={columns}
            pagination={false}
            rowKey="originalField"
            scroll={{ x: 1000 }}
          />
        </Card>

        <Divider />

        {/* 操作按钮 */}
        <Space>
          <Button onClick={() => setCurrentStep(0)}>
            重新上传
          </Button>
          <Button
            type="primary"
            size="large"
            icon={<CheckCircleOutlined />}
            onClick={confirmImport}
            loading={importing}
            disabled={importResult.mappedCount === 0}
          >
            确认导入 {importResult.mappedCount} 个字段
          </Button>
        </Space>
      </div>
    )
  }

  // 步骤3: 完成
  const renderCompleteStep = () => (
    <div style={{ textAlign: 'center', padding: '48px' }}>
      <CheckCircleOutlined style={{ fontSize: '64px', color: '#52c41a' }} />
      <h2 style={{ marginTop: '24px' }}>导入成功！</h2>
      <p style={{ color: '#8c8c8c', fontSize: '16px' }}>
        已成功导入 {importResult?.totalRows.toLocaleString()} 条数据
      </p>

      <Divider />

      <Space>
        <Button type="primary" onClick={() => window.location.href = '/dashboard'}>
          查看仪表盘
        </Button>
        <Button onClick={() => {
          setCurrentStep(0)
          setFileList([])
          setImportResult(null)
        }}>
          继续导入
        </Button>
      </Space>
    </div>
  )

  return (
    <div style={{ padding: '24px' }}>
      <h1 style={{ fontSize: '24px', fontWeight: 'bold', marginBottom: '24px' }}>
        📥 智能数据导入
      </h1>

      <Card>
        <Steps current={currentStep} style={{ marginBottom: '32px' }}>
          <Steps.Step title="上传文件" description="选择 Excel/CSV/JSON" />
          <Steps.Step title="智能解析" description="识别格式和表头" icon={importing && currentStep === 1 ? <LoadingOutlined /> : undefined} />
          <Steps.Step title="字段映射" description="调整映射关系" />
          <Steps.Step title="完成" description="数据已导入" />
        </Steps>

        {renderStepContent()}
      </Card>

      <Divider />

      {/* 使用指南 */}
      <Card title="📖 使用指南">
        <Tabs>
          <Tabs.TabPane tab="支持的格式" key="formats">
            <ul>
              <li>✅ <strong>Excel</strong>: .xlsx, .xls（支持多个 Sheet）</li>
              <li>✅ <strong>CSV</strong>: UTF-8, GBK 编码（自动检测）</li>
              <li>✅ <strong>JSON</strong>: 数组格式或对象格式</li>
              <li>✅ <strong>特殊格式</strong>: 支持非顶格表头、合并单元格（自动识别）</li>
            </ul>
          </Tabs.TabPane>

          <Tabs.TabPane tab="智能识别" key="smart">
            <ul>
              <li>✅ <strong>平台识别</strong>: Ozon、Wildberries、AliExpress、Amazon</li>
              <li>✅ <strong>多语言</strong>: 俄语（Артикул）、中文（商品编码）、英语（SKU）</li>
              <li>✅ <strong>表头检测</strong>: 自动搜索前 20 行，识别真实表头</li>
              <li>✅ <strong>数据验证</strong>: 自动检测数据类型和异常值</li>
            </ul>
          </Tabs.TabPane>

          <Tabs.TabPane tab="手动映射" key="manual">
            <ul>
              <li>✅ <strong>点击调整</strong>: 点击"映射到"列，选择标准字段</li>
              <li>✅ <strong>保存模板</strong>: 调整后可保存为模板，下次直接使用</li>
              <li>✅ <strong>批量操作</strong>: 支持批量映射（开发中）</li>
              <li>✅ <strong>实时预览</strong>: 查看映射后的数据效果</li>
            </ul>
          </Tabs.TabPane>

          <Tabs.TabPane tab="常见问题" key="faq">
            <ul>
              <li><strong>Q: 文件表头不在第一行怎么办？</strong>
                <br />A: 系统会自动搜索前 20 行，识别包含关键词的行作为表头
              </li>
              <li><strong>Q: 字段名是中英混杂怎么办？</strong>
                <br />A: 系统支持多语言关键词匹配，会尝试识别所有可能的标准字段
              </li>
              <li><strong>Q: 字段映射不准确怎么办？</strong>
                <br />A: 点击"映射到"列手动调整，并保存为模板供下次使用
              </li>
              <li><strong>Q: 可以导入多个文件吗？</strong>
                <br />A: 目前单次只能导入一个文件，但可以连续导入多次
              </li>
            </ul>
          </Tabs.TabPane>
        </Tabs>
      </Card>
    </div>
  )
}
