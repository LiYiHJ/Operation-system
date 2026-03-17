
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(r"C:\Operation-system\System")
IMPORT_SERVICE = REPO_ROOT / "src" / "ecom_v51" / "services" / "import_service.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"[{label}] expected 1 match, got {count}")
    return text.replace(old, new, 1)


def main() -> None:
    if not IMPORT_SERVICE.exists():
        raise FileNotFoundError(f"missing file: {IMPORT_SERVICE}")

    text = IMPORT_SERVICE.read_text(encoding="utf-8")
    backup = IMPORT_SERVICE.with_suffix(".py.bak_entity_key_probe_fix_v2")
    if not backup.exists():
        backup.write_text(text, encoding="utf-8")

    # 1) safer token regex
    old_patterns = """    ENTITY_KEY_TOKEN_PATTERNS = [
        re.compile(r"(?i)\\b[A-Z0-9]{2,}[-_][A-Z0-9][A-Z0-9_-]{2,}\\b"),
        re.compile(r"\\b\\d{8,14}\\b"),
    ]
"""
    new_patterns = """    ENTITY_KEY_TOKEN_PATTERNS = [
        re.compile(r"(?i)(?<![A-Z0-9])[A-Z0-9]{2,}(?:[-_][A-Z0-9]+){1,}(?![A-Z0-9])"),
        re.compile(r"(?<!\\d)\\d{8,14}(?!\\d)"),
    ]
"""
    text = replace_once(text, old_patterns, new_patterns, "replace token patterns")

    # 2) add deeper probe helper before _build_entity_key_suggestion if not present
    if "def _collect_entity_key_probe_values(" not in text:
        anchor = """    def _build_entity_key_suggestion(
"""
        helper = """    def _collect_entity_key_probe_values(
        self,
        df: pd.DataFrame,
        field_mappings: List[dict],
        limit: int = 12,
    ) -> List[str]:
        values: List[str] = []

        unmapped_headers = []
        for item in field_mappings or []:
            if item.get("standardField") or item.get("dynamicCompanion"):
                continue
            original_field = str(item.get("originalField") or "")
            if original_field:
                unmapped_headers.append(original_field)

        preferred_headers = []
        fallback_headers = []

        for header in unmapped_headers:
            lower = header.lower()
            if (
                header.startswith("Unnamed:")
                or header.startswith("col_")
                or "sku" in lower
                or "货号" in header
                or "编码" in header
                or "id" in lower
                or "артикул" in lower
            ):
                preferred_headers.append(header)
            else:
                fallback_headers.append(header)

        scan_headers = preferred_headers + fallback_headers

        for header in scan_headers:
            if header not in df.columns:
                continue
            series = df[header]
            for raw in series.tolist():
                if raw is None:
                    continue
                text = str(raw).strip()
                if not text or text.lower() == "nan":
                    continue
                values.append(text)
                if len(values) >= limit:
                    return values

        return values


"""
        text = replace_once(text, anchor, helper + anchor, "insert probe helper")

    # 3) extend suggestion signature with df
    old_sig = """    def _build_entity_key_suggestion(
        self,
        top_unmapped_headers: List[str],
        recovery_candidate_preview: List[dict],
        mapped_canonical_fields: List[str],
        field_mappings: Optional[List[dict]] = None,
    ) -> Optional[dict]:
"""
    new_sig = """    def _build_entity_key_suggestion(
        self,
        top_unmapped_headers: List[str],
        recovery_candidate_preview: List[dict],
        mapped_canonical_fields: List[str],
        field_mappings: Optional[List[dict]] = None,
        df: Optional[pd.DataFrame] = None,
    ) -> Optional[dict]:
"""
    text = replace_once(text, old_sig, new_sig, "extend suggestion signature")

    # 4) add dataProbeValues after fieldMappings.sampleValues loop
    old_pool_tail = """        for item in field_mappings or []:
            if item.get("standardField") or item.get("dynamicCompanion"):
                continue
            original_field = str(item.get("originalField") or "")
            if original_field:
                candidate_pool.append(("fieldMappings.originalField", original_field))
            for value in item.get("sampleValues") or []:
                candidate_pool.append(("fieldMappings.sampleValues", str(value)))

        best = None
"""
    new_pool_tail = """        for item in field_mappings or []:
            if item.get("standardField") or item.get("dynamicCompanion"):
                continue
            original_field = str(item.get("originalField") or "")
            if original_field:
                candidate_pool.append(("fieldMappings.originalField", original_field))
            for value in item.get("sampleValues") or []:
                candidate_pool.append(("fieldMappings.sampleValues", str(value)))

        if df is not None:
            for value in self._collect_entity_key_probe_values(df, field_mappings or []):
                candidate_pool.append(("dataProbeValues", value))

        best = None
"""
    text = replace_once(text, old_pool_tail, new_pool_tail, "add data probe values")

    # 5) pass df into helper call
    old_call = """        entity_key_suggestion = self._build_entity_key_suggestion(
            top_unmapped_headers=top_unmapped_headers,
            recovery_candidate_preview=recovery_candidate_preview,
            mapped_canonical_fields=mapped_canonical_fields,
            field_mappings=active_bundle.get("fieldMappings") or [],
        )
"""
    new_call = """        entity_key_suggestion = self._build_entity_key_suggestion(
            top_unmapped_headers=top_unmapped_headers,
            recovery_candidate_preview=recovery_candidate_preview,
            mapped_canonical_fields=mapped_canonical_fields,
            field_mappings=active_bundle.get("fieldMappings") or [],
            df=df,
        )
"""
    text = replace_once(text, old_call, new_call, "pass df into suggestion helper")

    IMPORT_SERVICE.write_text(text, encoding="utf-8")
    print("Applied entity key probe fix v2")
    print(f"Patched: {IMPORT_SERVICE}")
    print(f"Backup:  {backup}")


if __name__ == "__main__":
    main()
