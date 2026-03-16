
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(r"C:\Operation-system\System")
TYPES_FILE = REPO_ROOT / "frontend" / "src" / "types" / "index.ts"
PAGE_FILE = REPO_ROOT / "frontend" / "src" / "pages" / "DataImportV2.tsx"

OLD_FIELDS = """  transportStatus?: 'passed' | 'failed'
  semanticStatus?: 'passed' | 'risk' | 'failed'
  finalStatus?: 'passed' | 'risk' | 'failed'
  semanticGateReasons?: string[]
"""

NEW_FIELDS = """  transportStatus?: 'passed' | 'failed'
  semanticStatus?: 'passed' | 'risk' | 'failed'
  finalStatus?: 'passed' | 'risk' | 'failed'
  importabilityStatus?: 'passed' | 'risk' | 'failed'
  importabilityReasons?: string[]
  semanticGateReasons?: string[]
"""


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"[{label}] expected 1 match, got {count}")
    return text.replace(old, new, 1)


def patch_types() -> None:
    text = TYPES_FILE.read_text(encoding="utf-8")
    backup = TYPES_FILE.with_suffix(".ts.bak_phase1_frontend_sync_v4")
    if not backup.exists():
        backup.write_text(text, encoding="utf-8")

    if "importabilityStatus?" in text and "importabilityReasons?" in text:
        # If already present in both interfaces, skip.
        # Require at least 2 occurrences to count as done.
        if text.count("importabilityStatus?") >= 2 and text.count("importabilityReasons?") >= 2:
            print("types already patched; skipping types patch")
            return

    count = text.count(OLD_FIELDS)
    if count < 2:
        raise RuntimeError(f"[types] expected at least 2 OLD_FIELDS occurrences before patch, got {count}")

    text = replace_once(text, OLD_FIELDS, NEW_FIELDS, "ImportResult fields")
    text = replace_once(text, OLD_FIELDS, NEW_FIELDS, "ConfirmImportResponse fields")
    TYPES_FILE.write_text(text, encoding="utf-8")


def patch_page() -> None:
    text = PAGE_FILE.read_text(encoding="utf-8")
    backup = PAGE_FILE.with_suffix(".tsx.bak_phase1_frontend_sync_v4")
    if not backup.exists():
        backup.write_text(text, encoding="utf-8")

    if "const [confirmResult, setConfirmResult]" in text and "导入可用性" in text:
        print("page appears already patched; skipping page patch")
        return

    old_state = "const [currentStep, setCurrentStep] = useState(0) const [fileList, setFileList] = useState([]) const [selectedFile, setSelectedFile] = useState(null) const [importResult, setImportResult] = useState(null) const [importing, setImporting] = useState(false)"
    new_state = "const [currentStep, setCurrentStep] = useState(0) const [fileList, setFileList] = useState([]) const [selectedFile, setSelectedFile] = useState(null) const [importResult, setImportResult] = useState(null) const [confirmResult, setConfirmResult] = useState<ConfirmImportResponse | null>(null) const [importing, setImporting] = useState(false)"
    text = replace_once(text, old_state, new_state, "add confirmResult state")

    text = replace_once(
        text,
        "setImportResult(result) setCurrentStep(2)",
        "setImportResult(result) setConfirmResult(null) setCurrentStep(2)",
        "reset confirmResult on upload",
    )

    old_confirm_success = "if (result.status === 'success') { message.success(`成功导入 ${result.importedRows} 条数据！`) setCurrentStep(3) } else {"
    new_confirm_success = "if (result.status === 'success') { setConfirmResult(result) if (result.importabilityStatus === 'risk') { message.warning(`文件识别通过，但导入可用性存在风险：${(result.importabilityReasons || []).join('、') || 'importability_risk'}`) } else { message.success(`成功导入 ${result.importedRows} 条数据！`) } setCurrentStep(3) } else {"
    text = replace_once(text, old_confirm_success, new_confirm_success, "confirm success message")

    old_complete = "const renderCompleteStep = () => ( <div style={{ textAlign: 'center', padding: '48px' }}> <CheckCircleOutlined style={{ fontSize: '64px', color: '#52c41a' }} /> <h2 style={{ marginTop: '24px' }}>导入成功！</h2> <p style={{ color: '#8c8c8c', fontSize: '16px' }}> 已成功导入 {importResult?.totalRows.toLocaleString()} 条数据 </p> <Divider /> <Space> <Button type=\"primary\" onClick={() => window.location.href = '/dashboard'}> 查看仪表盘 </Button> <Button onClick={() => { setCurrentStep(0) setFileList([]) setImportResult(null) }}> 继续导入 </Button> </Space> </div> )"
    new_complete = "const renderCompleteStep = () => ( <div style={{ textAlign: 'center', padding: '48px' }}> <CheckCircleOutlined style={{ fontSize: '64px', color: '#52c41a' }} /> <h2 style={{ marginTop: '24px' }}>{confirmResult?.importabilityStatus === 'risk' ? '导入完成，但需复核' : '导入成功！'}</h2> <p style={{ color: '#8c8c8c', fontSize: '16px' }}> 已处理 {(confirmResult?.stagingRows ?? importResult?.totalRows ?? 0).toLocaleString()} 条数据；成功导入 {confirmResult?.importedRows ?? 0} 条 </p> {confirmResult?.importabilityStatus === 'risk' && ( <Alert style={{ marginTop: '16px', textAlign: 'left' }} type=\"warning\" showIcon message=\"导入可用性风险\" description={`当前语义识别已通过，但提交阶段存在风险：${(confirmResult.importabilityReasons || []).join('、') || 'importability_risk'}`} /> )} <Divider /> <Descriptions bordered column={3} style={{ marginBottom: '24px', textAlign: 'left' }}> <Descriptions.Item label=\"语义状态\">{renderGateTag(confirmResult?.semanticStatus || importResult?.semanticStatus)}</Descriptions.Item> <Descriptions.Item label=\"导入可用性\">{renderGateTag(confirmResult?.importabilityStatus)}</Descriptions.Item> <Descriptions.Item label=\"最终状态\">{renderGateTag(confirmResult?.finalStatus || importResult?.finalStatus)}</Descriptions.Item> <Descriptions.Item label=\"导入行数\">{confirmResult?.importedRows ?? 0}</Descriptions.Item> <Descriptions.Item label=\"隔离行数\">{confirmResult?.quarantineCount ?? 0}</Descriptions.Item> <Descriptions.Item label=\"事实写入错误\">{confirmResult?.factLoadErrors ?? 0}</Descriptions.Item> </Descriptions> <Space> <Button type=\"primary\" onClick={() => window.location.href = '/dashboard'}> 查看仪表盘 </Button> <Button onClick={() => { setCurrentStep(0) setFileList([]) setImportResult(null) setConfirmResult(null) }}> 继续导入 </Button> </Space> </div> )"
    text = replace_once(text, old_complete, new_complete, "replace complete step")

    PAGE_FILE.write_text(text, encoding="utf-8")


def main() -> None:
    if not TYPES_FILE.exists():
        raise FileNotFoundError(f"missing file: {TYPES_FILE}")
    if not PAGE_FILE.exists():
        raise FileNotFoundError(f"missing file: {PAGE_FILE}")

    patch_types()
    patch_page()
    print("Applied Phase 1 frontend sync patch v4")
    print(f"- patched {TYPES_FILE}")
    print(f"- patched {PAGE_FILE}")


if __name__ == "__main__":
    main()
