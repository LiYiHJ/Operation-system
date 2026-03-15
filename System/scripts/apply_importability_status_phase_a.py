from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(r"C:\Operation-system\System")
IMPORT_SERVICE = REPO_ROOT / "src" / "ecom_v51" / "services" / "import_service.py"
TYPES_FILE = REPO_ROOT / "frontend" / "src" / "types" / "index.ts"
PAGE_FILE = REPO_ROOT / "frontend" / "src" / "pages" / "DataImportV2.tsx"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"[{label}] expected 1 match, got {count}")
    return text.replace(old, new, 1)


def patch_import_service() -> None:
    text = IMPORT_SERVICE.read_text(encoding="utf-8")
    backup = IMPORT_SERVICE.with_suffix(".py.bak_importability_phase_a")
    if not backup.exists():
        backup.write_text(text, encoding="utf-8")

    old_session_not_found = """                "transportStatus": "failed",
                "semanticStatus": "failed",
                "finalStatus": "failed",
                "semanticGateReasons": ["session_not_found"],
                "riskOverrideReasons": [],
                "semanticAcceptanceReason": [],
                "recoverySummary": {},
"""
    new_session_not_found = """                "transportStatus": "failed",
                "semanticStatus": "failed",
                "finalStatus": "failed",
                "importabilityStatus": "failed",
                "importabilityReasons": ["session_not_found"],
                "semanticGateReasons": ["session_not_found"],
                "riskOverrideReasons": [],
                "semanticAcceptanceReason": [],
                "recoverySummary": {},
"""
    text = replace_once(text, old_session_not_found, new_session_not_found, "session_not_found response")

    anchor = """        if result.get("finalStatus") == "risk":
            warnings.append("当前样本处于 risk 状态，请结合语义门禁原因复核")

        response = {
"""
    inject = """        if result.get("finalStatus") == "risk":
            warnings.append("当前样本处于 risk 状态，请结合语义门禁原因复核")

        imported_rows = int(len(valid_df))
        quarantine_count = int(len(row_errors))
        fact_load_errors = 0
        importability_reasons: List[str] = []
        if imported_rows == 0 and quarantine_count > 0 and fact_load_errors == 0:
            importability_status = "risk"
            importability_reasons.append("all_rows_quarantined")
        elif imported_rows > 0 and quarantine_count > 0:
            importability_status = "risk"
            importability_reasons.append("partial_quarantine")
        elif imported_rows > 0 and fact_load_errors == 0:
            importability_status = "passed"
        else:
            importability_status = "failed"

        response = {
"""
    text = replace_once(text, anchor, inject, "inject importability block")

    text = replace_once(text, '"importedRows": int(len(valid_df)),', '"importedRows": imported_rows,', "use imported_rows")
    text = replace_once(text, '"errorRows": int(len(row_errors)),', '"errorRows": quarantine_count,', "use quarantine_count as errorRows")
    text = replace_once(text, '"quarantineCount": int(len(row_errors)),', '"quarantineCount": quarantine_count,', "use quarantine_count")
    text = replace_once(text, '"stagingRows": int(len(valid_df)),', '"stagingRows": imported_rows,', "use imported_rows as stagingRows")
    text = replace_once(text, '"factLoadErrors": 0,', '"factLoadErrors": fact_load_errors,', "use fact_load_errors")

    old_status_block = """            "transportStatus": result.get("transportStatus"),
            "semanticStatus": result.get("semanticStatus"),
            "finalStatus": result.get("finalStatus"),
            "semanticGateReasons": list(result.get("semanticGateReasons") or []),
"""
    new_status_block = """            "transportStatus": result.get("transportStatus"),
            "semanticStatus": result.get("semanticStatus"),
            "finalStatus": result.get("finalStatus"),
            "importabilityStatus": importability_status,
            "importabilityReasons": importability_reasons,
            "semanticGateReasons": list(result.get("semanticGateReasons") or []),
"""
    text = replace_once(text, old_status_block, new_status_block, "confirm response statuses")

    old_runtime = """                "sourceFile": session.get("fileName"),
                "finalStatus": result.get("finalStatus"),
                "transportStatus": result.get("transportStatus"),
                "semanticStatus": result.get("semanticStatus"),
"""
    new_runtime = """                "sourceFile": session.get("fileName"),
                "finalStatus": result.get("finalStatus"),
                "transportStatus": result.get("transportStatus"),
                "semanticStatus": result.get("semanticStatus"),
                "importabilityStatus": importability_status,
                "importabilityReasons": importability_reasons,
"""
    text = replace_once(text, old_runtime, new_runtime, "runtime audit importability")

    IMPORT_SERVICE.write_text(text, encoding="utf-8")


def patch_types() -> None:
    text = TYPES_FILE.read_text(encoding="utf-8")
    backup = TYPES_FILE.with_suffix(".ts.bak_importability_phase_a")
    if not backup.exists():
        backup.write_text(text, encoding="utf-8")

    old_fields = """  transportStatus?: 'passed' | 'failed'
  semanticStatus?: 'passed' | 'risk' | 'failed'
  finalStatus?: 'passed' | 'risk' | 'failed'
  semanticGateReasons?: string[]
"""
    new_fields = """  transportStatus?: 'passed' | 'failed'
  semanticStatus?: 'passed' | 'risk' | 'failed'
  finalStatus?: 'passed' | 'risk' | 'failed'
  importabilityStatus?: 'passed' | 'risk' | 'failed'
  importabilityReasons?: string[]
  semanticGateReasons?: string[]
"""
    # ImportResult occurrence
    text = replace_once(text, old_fields, new_fields, "ImportResult importability fields")
    # ConfirmImportResponse occurrence
    text = replace_once(text, old_fields, new_fields, "ConfirmImportResponse importability fields")

    TYPES_FILE.write_text(text, encoding="utf-8")


def patch_page() -> None:
    text = PAGE_FILE.read_text(encoding="utf-8")
    backup = PAGE_FILE.with_suffix(".tsx.bak_importability_phase_a")
    if not backup.exists():
        backup.write_text(text, encoding="utf-8")

    text = replace_once(
        text,
        "  const [importResult, setImportResult] = useState<ImportResult | null>(null)\n  const [importing, setImporting] = useState(false)\n",
        "  const [importResult, setImportResult] = useState<ImportResult | null>(null)\n  const [confirmResult, setConfirmResult] = useState<ConfirmImportResponse | null>(null)\n  const [importing, setImporting] = useState(false)\n",
        "add confirmResult state",
    )

    text = replace_once(
        text,
        "          setImportResult(result)\n",
        "          setImportResult(result)\n          setConfirmResult(null)\n",
        "reset confirmResult on upload",
    )

    text = replace_once(
        text,
        "      if (result.status === 'success') {\n        message.success(`成功导入 ${result.importedRows} 条数据！`)\n        setCurrentStep(3)\n",
        "      if (result.status === 'success') {\n        setConfirmResult(result)\n        if (result.importabilityStatus === 'risk') {\n          message.warning(`文件识别通过，但导入可用性存在风险：${(result.importabilityReasons || []).join('、') || 'importability_risk'}`)\n        } else {\n          message.success(`成功导入 ${result.importedRows} 条数据！`)\n        }\n        setCurrentStep(3)\n",
        "store confirmResult and warn on importability risk",
    )

    old_complete = """  const renderCompleteStep = () => (
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
"""
    new_complete = """  const renderCompleteStep = () => (
    <div style={{ textAlign: 'center', padding: '48px' }}>
      <CheckCircleOutlined style={{ fontSize: '64px', color: '#52c41a' }} />
      <h2 style={{ marginTop: '24px' }}>{confirmResult?.importabilityStatus === 'risk' ? '导入完成，但需复核' : '导入成功！'}</h2>
      <p style={{ color: '#8c8c8c', fontSize: '16px' }}>
        已处理 {confirmResult?.stagingRows?.toLocaleString?.() ?? importResult?.totalRows?.toLocaleString?.() ?? 0} 条数据；成功导入 {confirmResult?.importedRows ?? 0} 条
      </p>

      {confirmResult?.importabilityStatus === 'risk' && (
        <Alert
          style={{ marginTop: '16px', textAlign: 'left' }}
          type="warning"
          showIcon
          message="导入可用性风险"
          description={`当前语义识别已通过，但提交阶段存在风险：${(confirmResult.importabilityReasons || []).join('、') || 'importability_risk'}`}
        />
      )}

      <Divider />

      <Descriptions bordered column={3} style={{ marginBottom: '24px', textAlign: 'left' }}>
        <Descriptions.Item label="语义状态">{renderGateTag(confirmResult?.semanticStatus || importResult?.semanticStatus)}</Descriptions.Item>
        <Descriptions.Item label="导入可用性">{renderGateTag(confirmResult?.importabilityStatus)}</Descriptions.Item>
        <Descriptions.Item label="最终状态">{renderGateTag(confirmResult?.finalStatus || importResult?.finalStatus)}</Descriptions.Item>
        <Descriptions.Item label="导入行数">{confirmResult?.importedRows ?? 0}</Descriptions.Item>
        <Descriptions.Item label="隔离行数">{confirmResult?.quarantineCount ?? 0}</Descriptions.Item>
        <Descriptions.Item label="事实写入错误">{confirmResult?.factLoadErrors ?? 0}</Descriptions.Item>
      </Descriptions>

      <Space>
        <Button type="primary" onClick={() => window.location.href = '/dashboard'}>
          查看仪表盘
        </Button>
        <Button onClick={() => {
          setCurrentStep(0)
          setFileList([])
          setImportResult(null)
          setConfirmResult(null)
        }}>
          继续导入
        </Button>
      </Space>
    </div>
  )
"""
    text = replace_once(text, old_complete, new_complete, "replace renderCompleteStep")

    PAGE_FILE.write_text(text, encoding="utf-8")


def main() -> None:
    for p in [IMPORT_SERVICE, TYPES_FILE, PAGE_FILE]:
        if not p.exists():
            raise FileNotFoundError(f"missing file: {p}")

    patch_import_service()
    patch_types()
    patch_page()
    print("Applied importability status Phase A patch")
    print(f"- patched {IMPORT_SERVICE}")
    print(f"- patched {TYPES_FILE}")
    print(f"- patched {PAGE_FILE}")


if __name__ == "__main__":
    main()
