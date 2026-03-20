import React, { useEffect, useMemo, useState } from 'react'
import { ExclamationCircleOutlined, SaveOutlined } from '@ant-design/icons'
import { Modal, Steps, Space, Typography, message } from 'antd'
import type { UploadFile } from 'antd/es/upload/interface'
import { importApi } from '../services/api'
import type {
  ConfirmImportResponse,
  EntityKeySuggestion,
  FieldMapping,
  FieldRegistryField,
  ImportResult,
} from '../types'
import ImportCompleteStep from './data-import-v2/ImportCompleteStep'
import ImportMappingStep from './data-import-v2/ImportMappingStep'
import ImportParsingStep from './data-import-v2/ImportParsingStep'
import ImportUploadStep from './data-import-v2/ImportUploadStep'
import {
  SHOP_ID,
  STANDARD_FIELDS,
  type SavedTemplate,
  type StandardFieldConfig,
  buildDisplayStats,
  findProtectedTargetConflicts,
  getSuggestionOverride,
  isMappedField,
  normalizeConfirmResult,
  normalizeImportResult,
  normalizeRawFile,
} from './data-import-v2/shared'

const { Title, Paragraph } = Typography

export default function DataImportV2() {
  const [currentStep, setCurrentStep] = useState(0)
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [importResult, setImportResult] = useState<ImportResult | null>(null)
  const [confirmResult, setConfirmResult] = useState<ConfirmImportResponse | null>(null)
  const [acceptedEntityKeySuggestion, setAcceptedEntityKeySuggestion] = useState(false)
  const [importing, setImporting] = useState(false)
  const [savedTemplates, setSavedTemplates] = useState<SavedTemplate[]>([])
  const [standardFieldRegistry, setStandardFieldRegistry] =
    useState<Record<string, StandardFieldConfig>>(STANDARD_FIELDS)

  useEffect(() => {
    importApi
      .getFieldRegistry()
      .then((registry) => {
        const next: Record<string, StandardFieldConfig> = {}
        ;(registry?.fields || []).forEach((f: FieldRegistryField) => {
          next[f.canonical] = {
            name: f.displayLabel || f.canonical,
            category: f.type || '通用',
            required: f.canonical === 'sku',
            description: f.factTarget || '',
          }
        })
        if (Object.keys(next).length > 0) setStandardFieldRegistry(next)
      })
      .catch(() => {})
  }, [])

  const semanticRisk = importResult?.finalStatus === 'risk'
  const entityKeySuggestion = importResult?.entityKeySuggestion || null
  const displayStats = useMemo(() => buildDisplayStats(importResult), [importResult])
  const datasetKind = ((importResult as any)?.datasetKind || 'orders') as string
  const batchStatus = ((confirmResult as any)?.batchStatus ||
    (importResult as any)?.batchStatus ||
    'uploaded') as string

  const syncSelectedFile = (nextList: UploadFile[]) => {
    setFileList(nextList)
    setSelectedFile(normalizeRawFile(nextList[0] ?? undefined))
  }

  const handleUpload = async () => {
    if (!selectedFile) {
      message.warning('请先选择文件')
      return
    }

    setImporting(true)
    setCurrentStep(1)

    try {
      const raw = await importApi.uploadFile(selectedFile, SHOP_ID)
      const result = normalizeImportResult(raw)
      if (!result.fileName && selectedFile?.name) {
        result.fileName = selectedFile.name
      }
      setImportResult(result)
      setConfirmResult(null)
      setAcceptedEntityKeySuggestion(false)
      setCurrentStep(2)

      if (result?.finalStatus === 'risk') {
        message.warning('文件解析完成，但存在语义风险，请先检查后再确认导入。')
      } else {
        message.success('文件解析成功')
      }
    } catch (error: any) {
      message.error(`解析失败: ${error?.message || '未知错误'}`)
      setCurrentStep(0)
    } finally {
      setImporting(false)
    }
  }

  const handleManualMapping = (index: number, nextValue: string) => {
    if (!importResult || !Array.isArray(importResult.fieldMappings)) return
    const newStandardField = nextValue === '__UNMAPPED__' ? null : nextValue
    const nextMappings = [...importResult.fieldMappings]
    const prev = nextMappings[index]
    if (!prev) return

    nextMappings[index] = {
      ...prev,
      standardField: newStandardField,
      isManual: true,
      confidence: 1.0,
      reasons: Array.from(new Set([...(prev.reasons || []), 'manual_mapping'])),
    }

    setImportResult({
      ...importResult,
      fieldMappings: nextMappings,
    })
    message.success('映射已更新')
  }

  const saveTemplate = () => {
    if (!importResult) return
    const template: SavedTemplate = {
      name: `模板_${new Date().toLocaleString()}`,
      platform: importResult.platform,
      mappings: importResult.fieldMappings,
      createdAt: new Date().toISOString(),
    }
    setSavedTemplates((prev) => [...prev, template])
    message.success(`模板“${template.name}”已保存`)
  }

  const applyTemplate = (template: SavedTemplate) => {
    if (!importResult || !Array.isArray(template?.mappings)) return
    setImportResult({
      ...importResult,
      fieldMappings: template.mappings,
    })
    message.success(`模板“${template.name}”已应用`)
  }

  const buildConfirmedOverrides = (): FieldMapping[] => {
    if (!importResult || !Array.isArray(importResult.fieldMappings)) return []

    const manualMappings = importResult.fieldMappings
      .filter((m) => m.isManual && isMappedField(m))
      .map((m) => ({ ...m }))

    const suggestionOverride = acceptedEntityKeySuggestion
      ? getSuggestionOverride(entityKeySuggestion)
      : null

    if (!suggestionOverride) return manualMappings

    const alreadyExists = manualMappings.some(
      (m) =>
        m.originalField === suggestionOverride.originalField &&
        m.standardField === suggestionOverride.standardField,
    )

    if (alreadyExists) return manualMappings
    return [...manualMappings, suggestionOverride]
  }

  const confirmImport = async () => {
    if (!importResult) return

    const confirmedOverrides = buildConfirmedOverrides()
    const effectiveByOriginal = new Map<string, FieldMapping>()
    for (const item of importResult.fieldMappings || []) {
      effectiveByOriginal.set(item.originalField, { ...item })
    }
    for (const item of confirmedOverrides) {
      effectiveByOriginal.set(item.originalField, {
        ...(effectiveByOriginal.get(item.originalField) || item),
        ...item,
        isManual: true,
      })
    }

    const protectedConflicts = findProtectedTargetConflicts([...effectiveByOriginal.values()])
    if (protectedConflicts.length > 0) {
      Modal.error({
        title: '存在重复目标字段映射',
        content: (
          <div>
            {protectedConflicts.map(([target, items]) => (
              <div key={target}>
                {target}: {items.map((x) => x.originalField).join('、')}
              </div>
            ))}
          </div>
        ),
      })
      return
    }

    if (importResult.finalStatus === 'risk') {
      const reasons =
        (importResult.semanticGateReasons || importResult.semanticAcceptanceReason || []).join('、') ||
        'semantic_gate_not_met'

      const proceed = await new Promise<boolean>((resolve) => {
        Modal.confirm({
          title: '存在语义风险，确认继续导入？',
          icon: <ExclamationCircleOutlined />,
          content: `finalStatus=risk，原因：${reasons}`,
          okText: '继续导入',
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
      const raw = await importApi.confirmImport({
        sessionId: importResult.sessionId,
        shopId: SHOP_ID,
        operator: 'ui_manual_confirmation',
        manualOverrides: confirmedOverrides,
      })

      const result = normalizeConfirmResult(raw)
      if (result?.status !== 'success') {
        throw new Error(result?.errors?.[0] || '导入失败')
      }

      setConfirmResult(result)

      if (result.importabilityStatus === 'risk') {
        message.warning(
          `导入完成，但仍存在可提交性风险：${(result.importabilityReasons || []).join('、') || 'importability_risk'}`,
        )
      } else {
        message.success(`成功导入 ${result.importedRows || 0} 条数据`)
      }

      setCurrentStep(3)
    } catch (error: any) {
      message.error(`导入失败: ${error?.message || '未知错误'}`)
    } finally {
      setImporting(false)
    }
  }

  const resetFlow = () => {
    setCurrentStep(0)
    setFileList([])
    setSelectedFile(null)
    setImportResult(null)
    setConfirmResult(null)
    setAcceptedEntityKeySuggestion(false)
  }

  const renderStepContent = () => {
    switch (currentStep) {
      case 0:
        return (
          <ImportUploadStep
            fileList={fileList}
            selectedFile={selectedFile}
            importing={importing}
            onSyncFileList={syncSelectedFile}
            onHandleUpload={handleUpload}
          />
        )
      case 1:
        return <ImportParsingStep />
      case 2:
        return importResult ? (
          <ImportMappingStep
            importResult={importResult}
            selectedFileName={selectedFile?.name}
            standardFieldRegistry={standardFieldRegistry}
            savedTemplates={savedTemplates}
            acceptedEntityKeySuggestion={acceptedEntityKeySuggestion}
            entityKeySuggestion={entityKeySuggestion}
            semanticRisk={semanticRisk}
            displayStats={displayStats}
            importing={importing}
            onManualMapping={handleManualMapping}
            onSaveTemplate={saveTemplate}
            onApplyTemplate={applyTemplate}
            onToggleAcceptedEntityKeySuggestion={setAcceptedEntityKeySuggestion}
            onConfirmImport={confirmImport}
            onBackToUpload={() => setCurrentStep(0)}
          />
        ) : null
      case 3:
        return (
          <ImportCompleteStep
            confirmResult={confirmResult}
            importResult={importResult}
            onGoDashboard={() => {
              window.location.href = '/dashboard'
            }}
            onContinueImport={resetFlow}
          />
        )
      default:
        return null
    }
  }

  return (
    <div style={{ padding: 24 }}>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <div>
          <Title level={3} style={{ marginBottom: 8 }}>
            数据导入 V2
          </Title>
          <Paragraph type="secondary" style={{ marginBottom: 0 }}>
            当前页面已正式接入：entityKeySuggestion → manualOverrides → confirm → missingRatingCount。
          </Paragraph>
          <Paragraph type="secondary" style={{ marginBottom: 0 }}>
            当前数据集：{datasetKind}；当前批次状态：{batchStatus}。
          </Paragraph>
        </div>

        <Steps
          current={currentStep}
          items={[
            { title: '上传文件' },
            { title: '解析中' },
            { title: '字段映射' },
            { title: '导入完成' },
          ]}
        />

        {renderStepContent()}
      </Space>
    </div>
  )
}
