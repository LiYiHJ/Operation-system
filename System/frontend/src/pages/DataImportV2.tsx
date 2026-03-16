import { Upload, Button, Card, Steps, Table, Tag, Alert, Progress, Descriptions, Divider, message, Select, Space, Tabs, Tooltip, Badge, Row, Col, Statistic, Modal } from 'antd'
import {
  UploadOutlined, FileExcelOutlined, CheckCircleOutlined, WarningOutlined,
  LoadingOutlined, SaveOutlined, EyeOutlined, DatabaseOutlined, ExclamationCircleOutlined
} from '@ant-design/icons'
import { useEffect, useState } from 'react'
import type { UploadFile } from 'antd/es/upload/interface'
import { importApi } from '../services/api'
import type { ImportResult, FieldMapping, ConfirmImportResponse, FieldRegistryField } from '../types'

const isMappedField = (m: Pick<FieldMapping, 'standardField'>) => !!m.standardField && m.standardField !== 'unmapped'
const isIgnoredField = (m: FieldMapping) => !!m.reasons?.includes('dynamic_column_ignored')

// 标准字段定义（参考 C:\strategy-system）
const STANDARD_FIELDS = {
  // 基础信息
  sku: { name: 'SKU', category: '基础', required: true, description: '商品唯一标识' },
  product_name: { name: '商品名称', category: '基础', required: false },
  category: { name: '类目', category: '基础', required: false },

  // 销售数据
  orders: { name: '订单数', category: '销售', required: false },
  revenue: { name: '销售额', category: '销售', required: false },
  order_amount: { name: '订单金额', category: '销售', required: false },
  items_ordered: { name: '下单件数', category: '销售', required: false },
  items_delivered: { name: '履约件数', category: '销售', required: false },
  items_purchased: { name: '购买件数', category: '销售', required: false },
  items_canceled: { name: '取消件数', category: '销售', required: false },
  items_returned: { name: '退货件数', category: '销售', required: false },
  units: { name: '销量', category: '销售', required: false },

  // 流量数据
  impressions: { name: '展示量', category: '流量', required: false },
  impressions_total: { name: '总曝光', category: '流量', required: false },
  impressions_search_catalog: { name: '搜索/目录曝光', category: '流量', required: false },
  clicks: { name: '点击量', category: '流量', required: false },
  ctr: { name: '点击率', category: '流量', required: false },
  card_visits: { name: '商品页访问', category: '流量', required: false },
  product_card_visits: { name: '商品卡访问', category: '流量', required: false },

  // 转化数据
  add_to_cart: { name: '加购数', category: '转化', required: false },
  add_to_cart_total: { name: '总加购', category: '转化', required: false },
  add_to_cart_cvr_total: { name: '总加购转化率', category: '转化', required: false },
  add_to_cart_rate: { name: '加购率', category: '转化', required: false },
  conversion_rate: { name: '转化率', category: '转化', required: false },

  // 价格数据
  sale_price: { name: '售价', category: '价格', required: false },
  list_price: { name: '原价', category: '价格', required: false },
  avg_sale_price: { name: '平均销售价', category: '价格', required: false },
  market_price: { name: '市场价', category: '价格', required: false },
  discount: { name: '折扣', category: '价格', required: false },
  discount_pct: { name: '折扣率', category: '价格', required: false },
  price_index_status: { name: '价格指数状态', category: '价格', required: false },
  promo_days_count: { name: '活动天数', category: '价格', required: false },

  // 库存数据
  stock: { name: '库存', category: '库存', required: false },
  stock_total: { name: '总库存', category: '库存', required: false },
  stock_fbo: { name: 'FBO库存', category: '库存', required: false },
  stock_fbs: { name: 'FBS库存', category: '库存', required: false },
  days_of_supply: { name: '库存天数', category: '库存', required: false },

  // 评价数据
  rating: { name: '评分', category: '评价', required: false },
  rating_value: { name: '评分值', category: '评价', required: false },
  reviews_count: { name: '评价数', category: '评价', required: false },
  review_count: { name: '评论数', category: '评价', required: false },
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
  const [confirmResult, setConfirmResult] = useState<ConfirmImportResponse | null>(null)
  const [importing, setImporting] = useState(false)
  const [savedTemplates, setSavedTemplates] = useState<any[]>([])
  const [standardFieldRegistry, setStandardFieldRegistry] = useState(STANDARD_FIELDS)

  const semanticRisk = importResult?.finalStatus === 'risk'

  const renderGateTag = (status?: 'passed' | 'risk' | 'failed') => {
    if (status === 'passed') return <Tag color="green">passed</Tag>
    if (status === 'risk') return <Tag color="orange">risk</Tag>
    if (status === 'failed') return <Tag color="red">failed</Tag>
    return <Tag color="default">n/a</Tag>
  }

  useEffect(() => {
    importApi.getFieldRegistry()
      .then((registry) => {
        const next: Record<string, { name: string; category: string; required: boolean; description?: string }> = {}
          ; (registry.fields || []).forEach((f: FieldRegistryField) => {
            next[f.canonical] = {
              name: f.displayLabel || f.canonical,
              category: f.type || '通用',
              required: f.canonical === 'sku',
              description: f.factTarget,
            }
          })
        if (Object.keys(next).length > 0) {
          setStandardFieldRegistry(next as typeof STANDARD_FIELDS)
        }
      })
      .catch(() => {
        // keep local fallback
      })
  }, [])

  const buildDisplayStats = (result: ImportResult) => {
    const ignoredFields = new Set(result.stats?.ignoredFields || [])
    const ignoredMappings = result.fieldMappings.filter((m) => isIgnoredField(m) || ignoredFields.has(m.originalField))
    const candidateMappings = result.fieldMappings.filter((m) => !(isIgnoredField(m) || ignoredFields.has(m.originalField)))
    const mappedCount = candidateMappings.filter(isMappedField).length
    const unmappedCount = candidateMappings.length - mappedCount
    const coverage = mappedCount / Math.max(candidateMappings.length, 1)
    const mappedConfidence = mappedCount > 0
      ? candidateMappings.filter(isMappedField).reduce((acc, cur) => acc + (cur.confidence || 0), 0) / mappedCount
      : 0

    return {
      mappedCount,
      unmappedCount,
      candidateColumns: candidateMappings.length,
      ignoredColumns: ignoredMappings.length,
      mappingCoverage: Number(coverage.toFixed(3)),
      mappedConfidence: Number(mappedConfidence.toFixed(3)),
      rawColumns: result.rawColumns ?? result.totalColumns,
      droppedPlaceholderColumns: result.stats?.droppedPlaceholderColumns ?? [],
      removedSummaryRows: result.stats?.removedSummaryRows ?? 0,
      removedDescriptionRows: result.stats?.removedDescriptionRows ?? 0,
    }
  }

  const normalizeRawFile = (uploadFile?: UploadFile): File | null => {
    if (!uploadFile) return null
    const raw = uploadFile.originFileObj
    if (raw instanceof File) return raw
    return null
  }

  const syncSelectedFile = (nextList: UploadFile[]) => {
    setFileList(nextList)
    setSelectedFile(normalizeRawFile(nextList[0] ?? undefined))
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
      setConfirmResult(null)
      setCurrentStep(2)
      if (result.finalStatus === 'risk') {
        message.warning('文件解析完成，但存在语义风险，请先检查门禁状态再确认导入。')
      } else {
        message.success('文件解析成功！')
      }
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

    const ignoredFields = new Set(importResult.stats?.ignoredFields || [])
    const candidateMappings = newMappings.filter((m) => !(isIgnoredField(m) || ignoredFields.has(m.originalField)))
    const mappedCount = candidateMappings.filter(isMappedField).length
    const unmappedCount = candidateMappings.length - mappedCount
    const mappedConfidence = mappedCount > 0
      ? Number((candidateMappings.filter(isMappedField).reduce((acc, cur) => acc + (cur.confidence || 0), 0) / mappedCount).toFixed(3))
      : 0
    const mappingCoverage = Number((mappedCount / Math.max(candidateMappings.length, 1)).toFixed(3))

    setImportResult({
      ...importResult,
      fieldMappings: newMappings,
      mappedCount,
      unmappedCount,
      confidence: mappedConfidence,
      stats: {
        ...(importResult.stats || {
          candidateColumns: candidateMappings.length,
          ignoredColumns: newMappings.length - candidateMappings.length,
          ignoredFields: Array.from(ignoredFields),
          mappedConfidence: 0,
          mappingCoverage: 0,
          droppedPlaceholderColumns: [],
          removedSummaryRows: 0,
          removedDescriptionRows: 0,
        }),
        candidateColumns: candidateMappings.length,
        ignoredColumns: newMappings.length - candidateMappings.length,
        mappedConfidence,
        mappingCoverage,
      }
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

    // Soft gate 策略：finalStatus=risk 时允许继续，但必须二次确认并显示风险原因。
    // 后续建议：在生产环境可按租户/开关升级为 hard gate（risk 直接禁止 confirm）。
    if (importResult.finalStatus === 'risk') {
      const reasons = (importResult.semanticGateReasons || importResult.semanticAcceptanceReason || []).join('、') || 'semantic_gate_not_met'
      const proceed = await new Promise<boolean>((resolve) => {
        Modal.confirm({
          title: '存在语义风险，确认继续导入？',
          icon: <ExclamationCircleOutlined style={{ color: '#faad14' }} />,
          content: `finalStatus=risk，原因：${reasons}`,
          okText: '仍要继续导入',
          cancelText: '返回检查',
          okButtonProps: { danger: true },
          onOk: () => resolve(true),
          onCancel: () => resolve(false),
        })
      })
      if (!proceed) return
    }

    setImporting(true)

    try {
      const result: ConfirmImportResponse = await importApi.confirmImport({
        sessionId: importResult.sessionId,
        shopId: 1,
        manualOverrides: importResult.fieldMappings,
      })

      if (result.status === 'success') {
        setConfirmResult(result)

        if (result.importabilityStatus === 'risk') {
          message.warning(
            `文件识别通过，但导入可用性存在风险：${(result.importabilityReasons || []).join('、') || 'importability_risk'
            }`
          )
        } else {
          message.success(`成功导入 ${result.importedRows} 条数据！`)
        }

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
            <p>✅ 支持导入多格式；当前已完成实证：xlsx / csv</p>
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
          支持导入多格式（已完成实证：xlsx/csv），单个文件不超过 50MB
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
    const stats = buildDisplayStats(importResult)

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
          const standardField = standardFieldRegistry[field as keyof typeof standardFieldRegistry]

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

              {Object.entries(standardFieldRegistry).map(([key, config]) => (
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
          ) : record.reasons?.includes('dynamic_column_ignored') ? (
            <Tag color="default">动态列</Tag>
          ) : isMappedField(record) ? (
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
                title="候选字段数"
                value={stats.candidateColumns}
                prefix={<DatabaseOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="已映射"
                value={stats.mappedCount}
                valueStyle={{ color: '#52c41a' }}
                prefix={<CheckCircleOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="未映射"
                value={stats.unmappedCount}
                valueStyle={{ color: stats.unmappedCount > 0 ? '#faad14' : '#52c41a' }}
                prefix={<WarningOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="映射覆盖率"
                value={stats.mappingCoverage * 100}
                precision={1}
                suffix="%"
                valueStyle={{
                  color: stats.mappingCoverage > 0.7 ? '#52c41a' : stats.mappingCoverage > 0.5 ? '#faad14' : '#f5222d'
                }}
              />
            </Card>
          </Col>
        </Row>

        <Alert
          type="info"
          showIcon
          style={{ marginBottom: '16px' }}
          message="统计口径说明"
          description={`文件字段 ${stats.rawColumns}；候选字段 ${stats.candidateColumns}（用于映射统计）；已映射 ${stats.mappedCount}；未映射 ${stats.unmappedCount}；忽略动态列 ${stats.ignoredColumns}；映射置信度 ${(stats.mappedConfidence * 100).toFixed(1)}%。`}
        />

        <Card style={{ marginBottom: '16px' }}>
          <Descriptions bordered column={3} size="small">
            <Descriptions.Item label="传输状态">{renderGateTag(importResult.transportStatus)}</Descriptions.Item>
            <Descriptions.Item label="语义状态">{renderGateTag(importResult.semanticStatus)}</Descriptions.Item>
            <Descriptions.Item label="最终状态">{renderGateTag(importResult.finalStatus)}</Descriptions.Item>
          </Descriptions>
          {semanticRisk && (
            <Alert
              type="warning"
              showIcon
              style={{ marginTop: '12px' }}
              message="存在语义风险"
              description={`该样本链路可达，但语义门禁未全部通过：${(importResult.semanticGateReasons || []).join('、') || 'semantic_gate_not_met'}`}
            />
          )}
          {importResult.recoveryAttempted && (
            <Alert
              type={importResult.recoveryImproved ? 'success' : 'warning'}
              showIcon
              style={{ marginTop: '12px' }}
              message={importResult.recoveryImproved ? '已执行表头恢复，指标已改善' : '已执行表头恢复，但仍存在风险'}
              description={
                importResult.recoveryDiff
                  ? `mapped ${importResult.recoveryDiff.mappedCount_before}→${importResult.recoveryDiff.mappedCount_after}；unmapped ${importResult.recoveryDiff.unmappedCount_before}→${importResult.recoveryDiff.unmappedCount_after}；coverage ${(importResult.recoveryDiff.mappingCoverage_before * 100).toFixed(1)}%→${(importResult.recoveryDiff.mappingCoverage_after * 100).toFixed(1)}%。`
                  : '本次恢复未生成可比较指标。'
              }
            />
          )}
        </Card>

        {(importResult.headerBlock || importResult.headerStructureScore !== undefined) && (
          <Card style={{ marginBottom: '16px' }} title="表头结构与恢复信息">
            <Descriptions bordered column={3} size="small">
              <Descriptions.Item label="headerBlock">
                {importResult.headerBlock ? `${importResult.headerBlock.startRow + 1} - ${importResult.headerBlock.endRow + 1}` : 'n/a'}
              </Descriptions.Item>
              <Descriptions.Item label="headerBlock置信度">
                {importResult.headerBlock ? `${((importResult.headerBlock.confidence || 0) * 100).toFixed(1)}%` : 'n/a'}
              </Descriptions.Item>
              <Descriptions.Item label="结构评分">
                {importResult.headerStructureScore !== undefined ? `${(importResult.headerStructureScore * 100).toFixed(1)}%` : 'n/a'}
              </Descriptions.Item>
              <Descriptions.Item label="是否执行恢复">
                {importResult.recoveryAttempted ? <Tag color="blue">是</Tag> : <Tag>否</Tag>}
              </Descriptions.Item>
              <Descriptions.Item label="是否采用恢复结果">
                {importResult.headerRecoveryApplied ? <Tag color="green">是</Tag> : <Tag color="default">否</Tag>}
              </Descriptions.Item>
              <Descriptions.Item label="恢复后状态">
                {renderGateTag(importResult.postRecoveryStatus || importResult.semanticStatus)}
              </Descriptions.Item>
              <Descriptions.Item label="是否改善">
                {importResult.recoveryImproved ? <Tag color="green">improved</Tag> : <Tag color="orange">not_improved</Tag>}
              </Descriptions.Item>
            </Descriptions>
            {!!importResult.headerStructureRiskSignals?.length && (
              <Alert
                style={{ marginTop: 12 }}
                type="info"
                showIcon
                message="结构风险信号"
                description={(importResult.headerStructureRiskSignals || []).join('、')}
              />
            )}
            {!!importResult.semanticGateReasons?.length && (
              <Alert
                style={{ marginTop: 12 }}
                type="info"
                showIcon
                message="语义门禁原因"
                description={importResult.semanticGateReasons.join('、')}
              />
            )}
            {!!importResult.riskOverrideReasons?.length && (
              <Alert
                style={{ marginTop: 12 }}
                type="warning"
                showIcon
                message="风险保留原因"
                description={importResult.riskOverrideReasons.join('、')}
              />
            )}
          </Card>
        )}

        {/* 文件信息 */}
        <Card style={{ marginBottom: '24px' }}>
          <Descriptions bordered column={4}>
            <Descriptions.Item label="文件名">{importResult.fileName}</Descriptions.Item>
            <Descriptions.Item label="平台">
              <Tag color="blue">{importResult.platform}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="数据行数">{importResult.totalRows.toLocaleString()}</Descriptions.Item>
            <Descriptions.Item label="规范化后字段数">{importResult.totalColumns}</Descriptions.Item>
            <Descriptions.Item label="原始字段数">{stats.rawColumns}</Descriptions.Item>
            <Descriptions.Item label="剔除说明/汇总行">{stats.removedDescriptionRows + stats.removedSummaryRows}</Descriptions.Item>
            <Descriptions.Item label="剔除占位列">{stats.droppedPlaceholderColumns.length}</Descriptions.Item>
            <Descriptions.Item label="表头行">第 {importResult.headerRow} 行</Descriptions.Item>
            <Descriptions.Item label="Sheet" span={2}>
              {importResult.sheetNames.map(name => (
                <Tag key={name} color={name === importResult.selectedSheet ? 'blue' : 'default'}>
                  {name}
                </Tag>
              ))}
            </Descriptions.Item>
            <Descriptions.Item label="映射置信度（已映射字段）">
              {(stats.mappedConfidence * 100).toFixed(1)}%
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
            type={semanticRisk ? 'default' : 'primary'}
            danger={semanticRisk}
            size="large"
            icon={<CheckCircleOutlined />}
            onClick={confirmImport}
            loading={importing}
            disabled={stats.mappedCount === 0}
          >
            {semanticRisk ? '存在语义风险，继续导入（需确认）' : `确认导入 ${stats.mappedCount} 个字段`}
          </Button>
        </Space>
      </div>
    )
  }

  // 步骤3: 完成
  const renderCompleteStep = () => (
    <div style={{ textAlign: 'center', padding: '48px' }}>
      <CheckCircleOutlined style={{ fontSize: '64px', color: '#52c41a' }} />

      <h2 style={{ marginTop: '24px' }}>
        {confirmResult?.importabilityStatus === 'risk' ? '导入完成，但需复核' : '导入成功！'}
      </h2>

      <p style={{ color: '#8c8c8c', fontSize: '16px' }}>
        已处理 {(confirmResult?.stagingRows ?? importResult?.totalRows ?? 0).toLocaleString()} 条数据；
        成功导入 {confirmResult?.importedRows ?? 0} 条
      </p>

      {confirmResult?.importabilityStatus === 'risk' && (
        <Alert
          style={{ marginTop: '16px', textAlign: 'left' }}
          type="warning"
          showIcon
          message="导入可用性风险"
          description={`当前语义识别已通过，但提交阶段存在风险：${(confirmResult.importabilityReasons || []).join('、') || 'importability_risk'
            }`}
        />
      )}

      <Divider />

      <Descriptions bordered column={3} style={{ marginBottom: '24px', textAlign: 'left' }}>
        <Descriptions.Item label="语义状态">
          {renderGateTag(confirmResult?.semanticStatus || importResult?.semanticStatus)}
        </Descriptions.Item>
        <Descriptions.Item label="导入可用性">
          {renderGateTag(confirmResult?.importabilityStatus)}
        </Descriptions.Item>
        <Descriptions.Item label="最终状态">
          {renderGateTag(confirmResult?.finalStatus || importResult?.finalStatus)}
        </Descriptions.Item>
        <Descriptions.Item label="导入行数">
          {confirmResult?.importedRows ?? 0}
        </Descriptions.Item>
        <Descriptions.Item label="隔离行数">
          {confirmResult?.quarantineCount ?? 0}
        </Descriptions.Item>
        <Descriptions.Item label="事实写入错误">
          {confirmResult?.factLoadErrors ?? 0}
        </Descriptions.Item>
      </Descriptions>

      <Space>
        <Button type="primary" onClick={() => (window.location.href = '/dashboard')}>
          查看仪表盘
        </Button>
        <Button
          onClick={() => {
            setCurrentStep(0)
            setFileList([])
            setSelectedFile(null)
            setImportResult(null)
            setConfirmResult(null)
          }}
        >
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
          <Steps.Step title="上传文件" description="选择文件（xlsx/csv 已实证）" />
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
              <li>✅ <strong>Excel</strong>: 支持导入 .xlsx/.xls（当前已完成实证：.xlsx）</li>
              <li>✅ <strong>CSV</strong>: UTF-8, GBK 编码（当前已完成实证）</li>
              <li>⚠️ <strong>JSON</strong>: 能力存在，待真实样本实证</li>
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
              <li><strong>Q: 文件表头不在第一行怎么办？</strong><br />
                A: 系统会自动扫描前 20 行并尝试定位真实表头；若仍未识别，可先整理后再导入。
              </li>
              <li><strong>Q: 为什么会出现语义风险提示？</strong><br />
                A: 这表示链路可达，但关键字段组合、结构风险或映射覆盖度尚未完全满足门禁条件，可查看 semantic gate reasons。
              </li>
              <li><strong>Q: recoveryAttempted / headerRecoveryApplied / recoveryImproved 分别是什么意思？</strong><br />
                A: recoveryAttempted 表示是否执行过表头恢复；headerRecoveryApplied 表示是否采用恢复后的 bundle；recoveryImproved 表示恢复后指标是否量化改善。
              </li>
              <li><strong>Q: JSON 是否已经完全验证？</strong><br />
                A: 当前能力存在，但真实样本验证仍待补齐；现阶段 xlsx / csv 有实证，json 不应对外宣称已全部验证。
              </li>
            </ul>
          </Tabs.TabPane>
        </Tabs>
      </Card>
    </div>
  )
}
