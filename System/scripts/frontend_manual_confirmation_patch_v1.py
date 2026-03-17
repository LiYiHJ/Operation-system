
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(r"C:\Operation-system\System")
PAGE = REPO_ROOT / "frontend" / "src" / "pages" / "DataImportV2.tsx"
TYPES = REPO_ROOT / "frontend" / "src" / "types" / "index.ts"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"[{label}] expected 1 match, got {count}")
    return text.replace(old, new, 1)


def replace_between(text: str, start_anchor: str, end_anchor: str, replacement: str, label: str) -> str:
    start = text.find(start_anchor)
    if start == -1:
        raise RuntimeError(f"[{label}] start anchor not found")
    end = text.find(end_anchor, start)
    if end == -1:
        raise RuntimeError(f"[{label}] end anchor not found")
    return text[:start] + replacement + text[end:]


def patch_types() -> None:
    text = TYPES.read_text(encoding="utf-8")
    backup = TYPES.with_suffix(".ts.bak_frontend_manual_confirmation_v1")
    if not backup.exists():
        backup.write_text(text, encoding="utf-8")

    text = replace_once(
        text,
        "export interface ImportDiagnosis { suggestions: string[] keyField: string | null unmappedFields: string[] status: 'success' | 'partial' | 'failed' } export interface ImportResult {",
        "export interface ImportDiagnosis { suggestions: string[] keyField: string | null unmappedFields: string[] status: 'success' | 'partial' | 'failed' } export interface EntityKeySuggestion { field: string confidence: number sourceHeader?: string | null sourceColumn?: string | null sampleToken?: string | null detectedBy?: string | null rawCandidate?: string | null } export interface ImportResult {",
        "insert EntityKeySuggestion interface",
    )

    text = replace_once(
        text,
        "semanticGateReasons?: string[] riskOverrideReasons?: string[] semanticAcceptanceReason?: string[] semanticMetrics?: {",
        "semanticGateReasons?: string[] riskOverrideReasons?: string[] semanticAcceptanceReason?: string[] entityKeySuggestion?: EntityKeySuggestion semanticMetrics?: {",
        "add entityKeySuggestion to ImportResult",
    )

    text = replace_once(
        text,
        "quarantineCount?: number stagingRows?: number factLoadErrors?: number transportStatus?: 'passed' | 'failed' semanticStatus?: 'passed' | 'risk' | 'failed' finalStatus?: 'passed' | 'risk' | 'failed'",
        "quarantineCount?: number stagingRows?: number factLoadErrors?: number missingRatingCount?: number importabilityStatus?: 'passed' | 'risk' | 'failed' importabilityReasons?: string[] ratingIssueSamples?: Array<{ row?: number ratingValue?: any ratingSourceColumn?: string | null ratingSourceRawValue?: any error?: string }> transportStatus?: 'passed' | 'failed' semanticStatus?: 'passed' | 'risk' | 'failed' finalStatus?: 'passed' | 'risk' | 'failed'",
        "add confirm result fields",
    )

    text = replace_once(
        text,
        "export interface FieldMapping { originalField: string normalizedField?: string standardField: string | null mappingSource?: string confidence: number sampleValues: any[] isManual: boolean reasons?: string[] }",
        "export interface FieldMapping { originalField: string normalizedField?: string standardField: string | null mappingSource?: string confidence: number sampleValues: any[] isManual: boolean reasons?: string[] reason?: string sampleToken?: string }",
        "extend FieldMapping manual fields",
    )

    TYPES.write_text(text, encoding="utf-8")


def patch_page() -> None:
    text = PAGE.read_text(encoding="utf-8")
    backup = PAGE.with_suffix(".tsx.bak_frontend_manual_confirmation_v1")
    if not backup.exists():
        backup.write_text(text, encoding="utf-8")

    text = replace_once(
        text,
        "const [currentStep, setCurrentStep] = useState(0) const [fileList, setFileList] = useState([]) const [selectedFile, setSelectedFile] = useState(null) const [importResult, setImportResult] = useState(null) const [importing, setImporting] = useState(false) const [savedTemplates, setSavedTemplates] = useState([]) const [standardFieldRegistry, setStandardFieldRegistry] = useState(STANDARD_FIELDS) const semanticRisk = importResult?.finalStatus === 'risk'",
        "const [currentStep, setCurrentStep] = useState(0) const [fileList, setFileList] = useState<UploadFile[]>([]) const [selectedFile, setSelectedFile] = useState<File | null>(null) const [importResult, setImportResult] = useState<ImportResult | null>(null) const [confirmResult, setConfirmResult] = useState<ConfirmImportResponse | null>(null) const [acceptedEntityKeySuggestion, setAcceptedEntityKeySuggestion] = useState(false) const [importing, setImporting] = useState(false) const [savedTemplates, setSavedTemplates] = useState<any[]>([]) const [standardFieldRegistry, setStandardFieldRegistry] = useState(STANDARD_FIELDS) const semanticRisk = importResult?.finalStatus === 'risk' const entityKeySuggestion = importResult?.entityKeySuggestion || null",
        "patch state block",
    )

    text = replace_once(
        text,
        "const syncSelectedFile = (nextList: UploadFile[]) => { setFileList(nextList) setSelectedFile(normalizeRawFile(nextList[0])) }",
        """const syncSelectedFile = (nextList: UploadFile[]) => { setFileList(nextList) setSelectedFile(normalizeRawFile(nextList[0])) } const buildConfirmedOverrides = (): FieldMapping[] => { if (!importResult) return [] const manualMappings = importResult.fieldMappings.filter((m) => m.isManual && !!m.standardField && m.standardField !== 'unmapped').map((m) => ({ ...m })) const canUseSuggestion = acceptedEntityKeySuggestion && !!entityKeySuggestion?.sourceColumn && !!entityKeySuggestion?.field if (!canUseSuggestion) return manualMappings const alreadyExists = manualMappings.some((m) => m.originalField === entityKeySuggestion!.sourceColumn && m.standardField === entityKeySuggestion!.field) if (alreadyExists) return manualMappings return [ ...manualMappings, { originalField: entityKeySuggestion!.sourceColumn!, normalizedField: String(entityKeySuggestion!.sourceColumn || '').toLowerCase(), standardField: entityKeySuggestion!.field, mappingSource: 'manual_override', confidence: 1.0, sampleValues: entityKeySuggestion?.sampleToken ? [entityKeySuggestion.sampleToken] : [], isManual: true, reasons: ['entity_key_suggestion_confirmed'], reason: 'entity_key_suggestion_confirmed', sampleToken: entityKeySuggestion?.sampleToken || undefined, }, ] }""",
        "insert buildConfirmedOverrides helper",
    )

    text = replace_once(
        text,
        "setImportResult(result) setCurrentStep(2)",
        "setImportResult(result) setConfirmResult(null) setAcceptedEntityKeySuggestion(false) setCurrentStep(2)",
        "reset confirm state after upload",
    )

    confirm_replacement = """// 确认导入
const confirmImport = async () => {
  if (!importResult) return
  if (importResult.finalStatus === 'risk') {
    const reasons = (importResult.semanticGateReasons || importResult.semanticAcceptanceReason || []).join('、') || 'semantic_gate_not_met'
    const proceed = await new Promise((resolve) => {
      Modal.confirm({
        title: '存在语义风险，确认继续导入？',
        icon: <ExclamationCircleOutlined />,
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
    const confirmedOverrides = buildConfirmedOverrides()
    const result: ConfirmImportResponse = await importApi.confirmImport({
      sessionId: importResult.sessionId,
      shopId: 1,
      manualOverrides: confirmedOverrides,
    })
    if (result.status === 'success') {
      setConfirmResult(result)
      if (result.importabilityStatus === 'risk') {
        message.warning(`导入完成，但仍存在可提交性风险：${(result.importabilityReasons || []).join('、') || 'importability_risk'}`)
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
"""
    text = replace_between(
        text,
        "// 确认导入 const confirmImport = async () => {",
        "// 渲染步骤 const renderStepContent = () => {",
        confirm_replacement,
        "replace confirmImport block",
    )

    mapping_replacement = """// 步骤2: 字段映射
const renderMappingStep = () => {
  if (!importResult) return null
  const stats = buildDisplayStats(importResult)
  const canUseEntityKeySuggestion = !!entityKeySuggestion?.field && !!entityKeySuggestion?.sourceColumn && !importResult.fieldMappings.some((m) => m.standardField === 'sku')
  const columns = [
    {
      title: '原始字段',
      dataIndex: 'originalField',
      key: 'originalField',
      width: 200,
      render: (text: string) => <strong>{text}</strong>,
    },
    {
      title: '样本值',
      dataIndex: 'sampleValues',
      key: 'sampleValues',
      width: 250,
      render: (values: any[]) => <span>{values.slice(0, 3).join(', ')}{values.length > 3 ? '...' : ''}</span>,
    },
    {
      title: '映射到',
      dataIndex: 'standardField',
      key: 'standardField',
      width: 220,
      render: (field: string, _: any, index: number) => {
        const standardField = standardFieldRegistry[field as keyof typeof standardFieldRegistry]
        return (
          <Select
            value={field || undefined}
            placeholder="选择标准字段"
            onChange={(value) => handleManualMapping(index, value)}
            style={{ width: '100%' }}
            showSearch
            filterOption={(input, option) => String(option?.label).toLowerCase().includes(input.toLowerCase())}
            options={[
              { value: null, label: '不映射' },
              ...Object.entries(standardFieldRegistry).map(([key, config]) => ({
                value: key,
                label: `${config.required ? '[必填] ' : ''}${config.category} · ${config.name}`,
              })),
            ]}
          />
        )
      },
    },
    {
      title: '置信度',
      dataIndex: 'confidence',
      key: 'confidence',
      width: 120,
      render: (val: number) => (
        <Progress percent={(val || 0) * 100} size="small" status={val > 0.7 ? 'success' : val > 0.5 ? 'normal' : 'exception'} format={(percent) => `${percent?.toFixed(0)}%`} />
      ),
    },
    {
      title: '状态',
      key: 'status',
      width: 80,
      render: (_: any, record: FieldMapping) => (
        record.isManual ? <Tag color="blue">手动</Tag> :
        record.reasons?.includes('dynamic_column_ignored') ? <Tag>动态列</Tag> :
        isMappedField(record) ? <Tag color="green">自动</Tag> :
        <Tag color="default">未映射</Tag>
      ),
    },
  ]

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}><Card><Statistic title="已映射字段" value={stats.mappedCount} /></Card></Col>
        <Col span={6}><Card><Statistic title="待处理字段" value={stats.unmappedCount} /></Card></Col>
        <Col span={6}><Card><Statistic title="映射覆盖率" value={Number((stats.mappingCoverage * 100).toFixed(1))} suffix="%" /></Card></Col>
        <Col span={6}><Card><Statistic title="平均置信度" value={Number((stats.mappedConfidence * 100).toFixed(1))} suffix="%" /></Card></Col>
      </Row>

      <Card style={{ marginBottom: 16 }}>
        <Descriptions bordered column={3} size="small">
          <Descriptions.Item label="文件名">{importResult.fileName}</Descriptions.Item>
          <Descriptions.Item label="平台">{importResult.platform}</Descriptions.Item>
          <Descriptions.Item label="表头行">第 {importResult.headerRow} 行</Descriptions.Item>
          <Descriptions.Item label="传输状态">{renderGateTag(importResult.transportStatus)}</Descriptions.Item>
          <Descriptions.Item label="语义状态">{renderGateTag(importResult.semanticStatus)}</Descriptions.Item>
          <Descriptions.Item label="最终状态">{renderGateTag(importResult.finalStatus)}</Descriptions.Item>
          <Descriptions.Item label="总行数">{importResult.totalRows.toLocaleString()}</Descriptions.Item>
          <Descriptions.Item label="原始列数">{stats.rawColumns}</Descriptions.Item>
          <Descriptions.Item label="当前列数">{importResult.totalColumns}</Descriptions.Item>
        </Descriptions>
      </Card>

      {canUseEntityKeySuggestion && (
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
                <Button type={acceptedEntityKeySuggestion ? 'primary' : 'default'} onClick={() => setAcceptedEntityKeySuggestion(!acceptedEntityKeySuggestion)}>
                  {acceptedEntityKeySuggestion ? '已接受该建议' : '接受建议'}
                </Button>
                <Button onClick={() => setAcceptedEntityKeySuggestion(false)} disabled={!acceptedEntityKeySuggestion}>
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
            <Button icon={<SaveOutlined />} onClick={saveTemplate}>保存映射模板</Button>
            {savedTemplates.length > 0 && (
              <Select
                placeholder="应用模板"
                style={{ width: 220 }}
                onChange={(index) => applyTemplate(savedTemplates[index])}
                options={savedTemplates.map((template, index) => ({
                  value: index,
                  label: `${template.name} (${template.platform})`,
                }))}
              />
            )}
          </Space>
        }
      >
        <Alert message='点击"映射到"列可手动调整' type="info" showIcon style={{ marginBottom: 16 }} />
        <Table
          rowKey={(record: FieldMapping) => record.originalField}
          columns={columns}
          dataSource={importResult.fieldMappings}
          pagination={{ pageSize: 20 }}
          scroll={{ x: 900 }}
          size="small"
        />

        <Space style={{ marginTop: 16 }}>
          <Button onClick={() => setCurrentStep(0)}>重新上传</Button>
          <Button
            type="primary"
            onClick={confirmImport}
            loading={importing}
            disabled={stats.mappedCount === 0 && !acceptedEntityKeySuggestion}
          >
            {semanticRisk ? '存在语义风险，继续导入（需确认）' : `确认导入 ${stats.mappedCount} 个字段`}
          </Button>
        </Space>
      </Card>
    </div>
  )
}
// 步骤3: 完成
"""
    text = replace_between(
        text,
        "// 步骤2: 字段映射 const renderMappingStep = () => {",
        "// 步骤3: 完成 const renderCompleteStep = () => (",
        mapping_replacement,
        "replace renderMappingStep block",
    )

    complete_replacement = """// 步骤3: 完成
const renderCompleteStep = () => {
  const result = confirmResult
  return (
    <div style={{ textAlign: 'center', padding: '48px' }}>
      <CheckCircleOutlined style={{ fontSize: '64px', color: '#52c41a' }} />
      <h2 style={{ marginTop: '24px' }}>
        {result?.importabilityStatus === 'risk' ? '导入完成，但需复核' : '导入完成'}
      </h2>
      <p style={{ color: '#8c8c8c', fontSize: '16px' }}>
        已成功导入 {result?.importedRows ?? 0} 条数据，隔离 {result?.quarantineCount ?? 0} 条
      </p>

      <Descriptions bordered column={3} style={{ marginBottom: '24px', textAlign: 'left' }}>
        <Descriptions.Item label="语义状态">{renderGateTag(result?.semanticStatus || importResult?.semanticStatus)}</Descriptions.Item>
        <Descriptions.Item label="导入可用性">{renderGateTag(result?.importabilityStatus)}</Descriptions.Item>
        <Descriptions.Item label="最终状态">{renderGateTag(result?.finalStatus || importResult?.finalStatus)}</Descriptions.Item>
        <Descriptions.Item label="导入行数">{result?.importedRows ?? 0}</Descriptions.Item>
        <Descriptions.Item label="隔离行数">{result?.quarantineCount ?? 0}</Descriptions.Item>
        <Descriptions.Item label="缺失评分">{result?.missingRatingCount ?? 0}</Descriptions.Item>
      </Descriptions>

      {(result?.missingRatingCount || 0) > 0 && (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: '24px', textAlign: 'left' }}
          message="评分缺失已按缺失事实导入"
          description={`当前有 ${result?.missingRatingCount ?? 0} 条商品无评分，系统未伪造评分值，而是按缺失事实保留。`}
        />
      )}

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
            setAcceptedEntityKeySuggestion(false)
          }}
        >
          继续导入
        </Button>
      </Space>
    </div>
  )
}
"""
    text = replace_between(
        text,
        "// 步骤3: 完成 const renderCompleteStep = () => (",
        ") return (",
        complete_replacement + "\nreturn (",
        "replace renderCompleteStep block",
    )

    PAGE.write_text(text, encoding="utf-8")


def main() -> None:
    if not PAGE.exists():
        raise FileNotFoundError(f"missing file: {PAGE}")
    if not TYPES.exists():
        raise FileNotFoundError(f"missing file: {TYPES}")

    patch_types()
    patch_page()

    print("Applied frontend manual confirmation patch v1")
    print(f"Patched: {PAGE}")
    print(f"Patched: {TYPES}")


if __name__ == "__main__":
    main()
