
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(r"C:\Operation-system\System")
PAGE = REPO_ROOT / "frontend" / "src" / "pages" / "DataImportV2.tsx"

PATCH_1_OLD = "    isManual: Boolean(item?.isManual ?? item?.is_manual ?? False),\n"
PATCH_1_NEW = "    isManual: Boolean(item?.isManual ?? item?.is_manual ?? false),\n"

PATCH_2_OLD = """const buildDisplayStats = (result: ImportResult | null) => {
  const mappings = Array.isArray(result?.fieldMappings) ? result!.fieldMappings : []
  const ignoredFields = new Set(result?.stats?.ignoredFields || [])
  const candidateMappings = mappings.filter(
    (m) => !(isIgnoredField(m) || ignoredFields.has(m.originalField)),
  )
  const mappedCount = candidateMappings.filter(isMappedField).length
  const unmappedCount = candidateMappings.length - mappedCount
  const coverage = mappedCount / Math.max(candidateMappings.length, 1)
  const mappedConfidence =
    mappedCount > 0
      ? candidateMappings
          .filter(isMappedField)
          .reduce((acc, cur) => acc + (cur.confidence || 0), 0) / mappedCount
      : 0

  return {
    mappedCount,
    unmappedCount,
    mappingCoverage: Number(coverage.toFixed(3)),
    mappedConfidence: Number(mappedConfidence.toFixed(3)),
    rawColumns: result?.rawColumns ?? result?.totalColumns ?? 0,
  }
}
"""
PATCH_2_NEW = """const buildDisplayStats = (result: ImportResult | null) => {
  const mappings = Array.isArray(result?.fieldMappings) ? result!.fieldMappings : []
  const ignoredFields = new Set(result?.stats?.ignoredFields || [])
  const candidateMappings = mappings.filter(
    (m) => !(isIgnoredField(m) || ignoredFields.has(m.originalField)),
  )
  const mappedCountFromMappings = candidateMappings.filter(isMappedField).length
  const unmappedCountFromMappings = candidateMappings.length - mappedCountFromMappings
  const coverageFromMappings =
    mappedCountFromMappings / Math.max(candidateMappings.length, 1)
  const mappedConfidence =
    mappedCountFromMappings > 0
      ? candidateMappings
          .filter(isMappedField)
          .reduce((acc, cur) => acc + (cur.confidence || 0), 0) / mappedCountFromMappings
      : 0

  const mappedCount =
    candidateMappings.length > 0
      ? mappedCountFromMappings
      : Number((result as any)?.mappedCount ?? (result as any)?.mapped_count ?? 0)

  const unmappedCount =
    candidateMappings.length > 0
      ? unmappedCountFromMappings
      : Number((result as any)?.unmappedCount ?? (result as any)?.unmapped_count ?? 0)

  const mappingCoverage =
    candidateMappings.length > 0
      ? Number(coverageFromMappings.toFixed(3))
      : Number(
          Number(
            (result as any)?.mappingCoverage ?? (result as any)?.mapping_coverage ?? 0,
          ).toFixed(3),
        )

  return {
    mappedCount,
    unmappedCount,
    mappingCoverage,
    mappedConfidence: Number(mappedConfidence.toFixed(3)),
    rawColumns: Number(result?.rawColumns ?? result?.totalColumns ?? 0),
  }
}
"""

PATCH_3_OLD = """      const result = normalizeImportResult(raw)
      console.log('upload raw ->', raw)
      console.log('upload normalized ->', result)
      setImportResult(result)
"""
PATCH_3_NEW = """      const result = normalizeImportResult(raw)
      if (!result.fileName && selectedFile?.name) {
        result.fileName = selectedFile.name
      }
      console.log('upload raw ->', raw)
      console.log('upload normalized ->', result)
      console.log('upload fieldMappings length ->', Array.isArray(result.fieldMappings) ? result.fieldMappings.length : 'n/a')
      setImportResult(result)
"""

PATCH_4_OLD = """    return (
      <div>
"""
PATCH_4_NEW = """    return (
      <div>
        {mappings.length === 0 && (
          <Alert
            type="warning"
            showIcon
            style={{ marginBottom: 16 }}
            message="后端未返回 fieldMappings，当前按回退模式展示统计与建议"
            description={
              <div>
                <div>已映射字段：{displayStats.mappedCount}</div>
                <div>待处理字段：{displayStats.unmappedCount}</div>
                <div>映射覆盖率：{(displayStats.mappingCoverage * 100).toFixed(1)}%</div>
                <div>若下方出现 SKU 建议，可直接接受建议后确认导入。</div>
              </div>
            }
          />
        )}
"""

PATCH_5_OLD = """            <Descriptions.Item label="文件名">{importResult.fileName}</Descriptions.Item>
"""
PATCH_5_NEW = """            <Descriptions.Item label="文件名">{importResult.fileName || selectedFile?.name || 'n/a'}</Descriptions.Item>
"""


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"[{label}] expected 1 match, got {count}")
    return text.replace(old, new, 1)


def main() -> None:
    if not PAGE.exists():
        raise FileNotFoundError(f"missing file: {PAGE}")

    text = PAGE.read_text(encoding="utf-8")
    backup = PAGE.with_suffix(".tsx.bak_mapping_zeros_fix_v1")
    if not backup.exists():
        backup.write_text(text, encoding="utf-8")

    text = replace_once(text, PATCH_1_OLD, PATCH_1_NEW, "fix False to false")
    text = replace_once(text, PATCH_2_OLD, PATCH_2_NEW, "fallback stats")
    text = replace_once(text, PATCH_3_OLD, PATCH_3_NEW, "upload filename fallback")
    text = replace_once(text, PATCH_4_OLD, PATCH_4_NEW, "mapping fallback alert")
    text = replace_once(text, PATCH_5_OLD, PATCH_5_NEW, "fileName fallback display")

    PAGE.write_text(text, encoding="utf-8")
    print("Applied DataImportV2 mapping-zeros fix v1")
    print(f"Patched: {PAGE}")
    print(f"Backup:  {backup}")


if __name__ == "__main__":
    main()
