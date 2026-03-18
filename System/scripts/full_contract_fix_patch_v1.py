
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(r"C:\Operation-system\System")
IMPORT_ROUTE = REPO_ROOT / "src" / "ecom_v51" / "api" / "routes" / "import_route.py"
DATAIMPORT_PAGE = REPO_ROOT / "frontend" / "src" / "pages" / "DataImportV2.tsx"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"[{label}] expected 1 match, got {count}")
    return text.replace(old, new, 1)


def patch_import_route() -> None:
    text = IMPORT_ROUTE.read_text(encoding="utf-8")
    backup = IMPORT_ROUTE.with_suffix(".py.bak_contract_fix_v1")
    if not backup.exists():
        backup.write_text(text, encoding="utf-8")

    if "def _ensure_json_object(" not in text:
        text = replace_once(
            text,
            "from flask import Blueprint, jsonify, request, send_file\n",
            "from flask import Blueprint, jsonify, request, send_file\nimport ast\nimport json\n",
            "add ast/json imports",
        )

        insert_anchor = "import_service = ImportService()\n\n\n"
        helper = """import_service = ImportService()\n\n\ndef _ensure_json_object(value, *, label: str):\n    if isinstance(value, str):\n        try:\n            value = json.loads(value)\n        except Exception:\n            try:\n                value = ast.literal_eval(value)\n            except Exception:\n                return None, (jsonify({'error': f'{label} is string and cannot be parsed'}), 500)\n\n    if not isinstance(value, dict):\n        return None, (jsonify({'error': f'{label} must be dict, got {type(value).__name__}'}), 500)\n\n    return value, None\n\n\n"""
        text = replace_once(
            text,
            insert_anchor,
            helper,
            "insert _ensure_json_object helper",
        )

    old_upload = """        result = import_service.parse_import_file(
            str(filepath),
            shop_id=shop_id,
            operator=operator,
        )
        return jsonify(result)
"""
    new_upload = """        result = import_service.parse_import_file(
            str(filepath),
            shop_id=shop_id,
            operator=operator,
        )
        result, error_response = _ensure_json_object(result, label='upload result')
        if error_response is not None:
            return error_response
        return jsonify(result)
"""
    if old_upload in text:
        text = replace_once(text, old_upload, new_upload, "patch upload_file response")

    old_server = """        result = import_service.parse_import_file(
            file_path,
            shop_id=shop_id,
            operator=operator,
        )
        result["sourceMode"] = "server_file"
        return jsonify(result)
"""
    new_server = """        result = import_service.parse_import_file(
            file_path,
            shop_id=shop_id,
            operator=operator,
        )
        result, error_response = _ensure_json_object(result, label='upload-server-file result')
        if error_response is not None:
            return error_response
        result["sourceMode"] = "server_file"
        return jsonify(result)
"""
    if old_server in text:
        text = replace_once(text, old_server, new_server, "patch upload_server_file response")

    IMPORT_ROUTE.write_text(text, encoding="utf-8")


def patch_dataimport_page() -> None:
    if not DATAIMPORT_PAGE.exists():
        return

    text = DATAIMPORT_PAGE.read_text(encoding="utf-8")
    backup = DATAIMPORT_PAGE.with_suffix(".tsx.bak_contract_fix_v1")
    if not backup.exists():
        backup.write_text(text, encoding="utf-8")

    old_normalize_block = """const normalizeFieldMappings = (value: any): FieldMapping[] => {
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
    isManual: Boolean(item?.isManual ?? item?.is_manual ?? false),
    reasons: Array.isArray(item?.reasons) ? item.reasons : [],
    reason: item?.reason ?? undefined,
    sampleToken: item?.sampleToken ?? item?.sample_token ?? undefined,
  }))
}

const normalizeImportResult = (raw: any): ImportResult => {
  const payload = unwrapPayload(raw)
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
    mappedCount: Number(payload?.mappedCount ?? payload?.mapped_count ?? 0),
    unmappedCount: Number(payload?.unmappedCount ?? payload?.unmapped_count ?? 0),
    mappingCoverage: Number(payload?.mappingCoverage ?? payload?.mapping_coverage ?? 0),
    ...payload,
  } as ImportResult
}
"""
    new_normalize_block = """const normalizeFieldMappings = (value: any): FieldMapping[] => {
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
    isManual: Boolean(item?.isManual ?? item?.is_manual ?? false),
    reasons: Array.isArray(item?.reasons) ? item.reasons : [],
    reason: item?.reason ?? undefined,
    sampleToken: item?.sampleToken ?? item?.sample_token ?? undefined,
  }))
}

const normalizeImportResult = (raw: any): ImportResult => {
  const payload = unwrapPayload(raw)
  return {
    status: payload?.status ?? 'success',
    sessionId: Number(payload?.sessionId ?? payload?.session_id ?? 0),
    fileName: payload?.fileName ?? payload?.file_name ?? payload?.filename ?? '',
    platform: payload?.platform ?? '',
    headerRow: Number(payload?.headerRow ?? payload?.header_row ?? 0),
    totalRows: Number(payload?.totalRows ?? payload?.total_rows ?? 0),
    totalColumns: Number(payload?.totalColumns ?? payload?.total_columns ?? 0),
    rawColumns: Number(
      payload?.rawColumns ??
        payload?.raw_columns ??
        payload?.totalColumns ??
        payload?.total_columns ??
        0,
    ),
    fieldMappings: normalizeFieldMappings(payload?.fieldMappings ?? payload?.field_mappings),
    stats: payload?.stats ?? {},
    transportStatus: payload?.transportStatus ?? payload?.transport_status,
    semanticStatus: payload?.semanticStatus ?? payload?.semantic_status,
    finalStatus: payload?.finalStatus ?? payload?.final_status,
    semanticGateReasons:
      payload?.semanticGateReasons ?? payload?.semantic_gate_reasons ?? [],
    semanticAcceptanceReason:
      payload?.semanticAcceptanceReason ??
      payload?.semantic_acceptance_reason ??
      [],
    entityKeySuggestion:
      payload?.entityKeySuggestion ?? payload?.entity_key_suggestion ?? null,
    mappedCount: Number(payload?.mappedCount ?? payload?.mapped_count ?? 0),
    unmappedCount: Number(payload?.unmappedCount ?? payload?.unmapped_count ?? 0),
    mappingCoverage: Number(
      payload?.mappingCoverage ?? payload?.mapping_coverage ?? 0,
    ),
    ...payload,
  } as ImportResult
}
"""
    if old_normalize_block in text:
        text = replace_once(
            text,
            old_normalize_block,
            new_normalize_block,
            "refresh normalizeImportResult block",
        )

    DATAIMPORT_PAGE.write_text(text, encoding="utf-8")


def main() -> None:
    if not IMPORT_ROUTE.exists():
        raise FileNotFoundError(f"missing file: {IMPORT_ROUTE}")

    patch_import_route()
    patch_dataimport_page()

    print("Applied full contract fix patch v1")
    print(f"Patched: {IMPORT_ROUTE}")
    if DATAIMPORT_PAGE.exists():
        print(f"Patched: {DATAIMPORT_PAGE}")


if __name__ == "__main__":
    main()
