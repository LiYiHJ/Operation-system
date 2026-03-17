
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(r"C:\Operation-system\System")
PAGE = REPO_ROOT / "frontend" / "src" / "pages" / "DataImportV2.tsx"

HELPERS = """
const normalizeFieldMappings = (value: any): FieldMapping[] => {
  if (!Array.isArray(value)) return []
  return value.map((item: any) => ({
    originalField: item?.originalField ?? item?.original_field ?? '',
    normalizedField: item?.normalizedField ?? item?.normalized_field ?? undefined,
    standardField: item?.standardField ?? item?.standard_field ?? null,
    mappingSource: item?.mappingSource ?? item?.mapping_source ?? undefined,
    confidence: Number(item?.confidence ?? 0),
    sampleValues: Array.isArray(item?.sampleValues)
      ? item.sampleValues
      : Array.isArray(item?.sample_values)
      ? item.sample_values
      : [],
    isManual: Boolean(item?.isManual ?? item?.is_manual ?? False),
    reasons: Array.isArray(item?.reasons) ? item.reasons : [],
    reason: item?.reason ?? undefined,
    sampleToken: item?.sampleToken ?? item?.sample_token ?? undefined,
  }))
}

const normalizeImportResult = (raw: any): ImportResult => {
  const payload = raw?.data ?? raw?.result ?? raw ?? {}
  return {
    status: payload?.status ?? 'success',
    sessionId: Number(payload?.sessionId ?? payload?.session_id ?? 0),
    fileName: payload?.fileName ?? payload?.file_name ?? payload?.filename ?? '',
    platform: payload?.platform ?? '',
    headerRow: Number(payload?.headerRow ?? payload?.header_row ?? 0),
    totalRows: Number(payload?.totalRows ?? payload?.total_rows ?? 0),
    totalColumns: Number(payload?.totalColumns ?? payload?.total_columns ?? 0),
    rawColumns: Number(payload?.rawColumns ?? payload?.raw_columns ?? payload?.totalColumns ?? payload?.total_columns ?? 0),
    fieldMappings: normalizeFieldMappings(payload?.fieldMappings ?? payload?.field_mappings),
    stats: payload?.stats ?? {},
    transportStatus: payload?.transportStatus ?? payload?.transport_status,
    semanticStatus: payload?.semanticStatus ?? payload?.semantic_status,
    finalStatus: payload?.finalStatus ?? payload?.final_status,
    semanticGateReasons: payload?.semanticGateReasons ?? payload?.semantic_gate_reasons ?? [],
    semanticAcceptanceReason: payload?.semanticAcceptanceReason ?? payload?.semantic_acceptance_reason ?? [],
    entityKeySuggestion: payload?.entityKeySuggestion ?? payload?.entity_key_suggestion ?? null,
    ...payload,
  } as ImportResult
}

const normalizeConfirmResult = (raw: any): ConfirmImportResponse => {
  const payload = raw?.data ?? raw?.result ?? raw ?? {}
  return {
    status: payload?.status ?? 'success',
    importedRows: Number(payload?.importedRows ?? payload?.imported_rows ?? 0),
    quarantineCount: Number(payload?.quarantineCount ?? payload?.quarantine_count ?? 0),
    duplicateCount: Number(payload?.duplicateCount ?? payload?.duplicate_count ?? 0),
    missingRatingCount: Number(payload?.missingRatingCount ?? payload?.missing_rating_count ?? 0),
    importabilityStatus: payload?.importabilityStatus ?? payload?.importability_status,
    importabilityReasons: payload?.importabilityReasons ?? payload?.importability_reasons ?? [],
    semanticStatus: payload?.semanticStatus ?? payload?.semantic_status,
    finalStatus: payload?.finalStatus ?? payload?.final_status,
    ratingIssueSamples: Array.isArray(payload?.ratingIssueSamples)
      ? payload.ratingIssueSamples
      : Array.isArray(payload?.rating_issue_samples)
      ? payload.rating_issue_samples
      : [],
    errors: Array.isArray(payload?.errors) ? payload.errors : [],
    ...payload,
  } as ConfirmImportResponse
}

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
    backup = PAGE.with_suffix(".tsx.bak_response_normalize_fix_v1")
    if not backup.exists():
        backup.write_text(text, encoding="utf-8")

    text = replace_once(
        text,
        "const buildDisplayStats = (result: ImportResult | null) => {\n",
        HELPERS + "\nconst buildDisplayStats = (result: ImportResult | null) => {\n",
        "insert normalize helpers",
    )

    text = replace_once(
        text,
        "      const result = await importApi.uploadFile(selectedFile, SHOP_ID)\n      setImportResult(result)\n",
        "      const raw = await importApi.uploadFile(selectedFile, SHOP_ID)\n      const result = normalizeImportResult(raw)\n      console.log('upload raw ->', raw)\n      console.log('upload normalized ->', result)\n      setImportResult(result)\n",
        "normalize upload result",
    )

    text = replace_once(
        text,
        "      const result = await importApi.confirmImport({\n",
        "      const raw = await importApi.confirmImport({\n",
        "rename confirm result raw",
    )

    text = replace_once(
        text,
        "      if (result?.status !== 'success') {\n        throw new Error(result?.errors?.[0] || '导入失败')\n      }\n\n      setConfirmResult(result)\n",
        "      const result = normalizeConfirmResult(raw)\n      console.log('confirm raw ->', raw)\n      console.log('confirm normalized ->', result)\n      if (result?.status !== 'success') {\n        throw new Error(result?.errors?.[0] || '导入失败')\n      }\n\n      setConfirmResult(result)\n",
        "normalize confirm result",
    )

    PAGE.write_text(text, encoding="utf-8")
    print("Applied DataImportV2 response-normalize fix v1")
    print(f"Patched: {PAGE}")
    print(f"Backup:  {backup}")


if __name__ == "__main__":
    main()
