from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(r"C:\Operation-system\System")
IMPORT_SERVICE = REPO_ROOT / "src" / "ecom_v51" / "services" / "import_service.py"

NEW_PROBE_HELPER = '''    def _collect_entity_key_probe_values(
        self,
        df: pd.DataFrame,
        field_mappings: List[dict],
        limit: int = 12,
    ) -> List[tuple[str, str]]:
        values: List[tuple[str, str]] = []

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
                values.append((header, text))
                if len(values) >= limit:
                    return values

        return values
'''

NEW_BUILD_FUNC = '''    def _build_entity_key_suggestion(
        self,
        top_unmapped_headers: List[str],
        recovery_candidate_preview: List[dict],
        mapped_canonical_fields: List[str],
        field_mappings: Optional[List[dict]] = None,
        df: Optional[pd.DataFrame] = None,
    ) -> Optional[dict]:
        if "sku" in {str(x) for x in (mapped_canonical_fields or [])}:
            return None

        candidate_pool: List[tuple[str, Optional[str], str]] = []

        for item in top_unmapped_headers or []:
            candidate_pool.append(("topUnmappedHeaders", None, str(item)))

        for candidate in recovery_candidate_preview or []:
            for example in candidate.get("flattenedHeaderExamples") or []:
                candidate_pool.append(("recoveryCandidatePreview", None, str(example)))

        for item in field_mappings or []:
            if item.get("standardField") or item.get("dynamicCompanion"):
                continue
            original_field = str(item.get("originalField") or "")
            if original_field:
                candidate_pool.append(("fieldMappings.originalField", original_field, original_field))
            for value in item.get("sampleValues") or []:
                candidate_pool.append(("fieldMappings.sampleValues", original_field or None, str(value)))

        if df is not None:
            for column_name, value in self._collect_entity_key_probe_values(df, field_mappings or []):
                candidate_pool.append(("dataProbeValues", column_name, value))

        best = None
        best_score = 0.0
        best_token = None
        best_source = None
        best_column = None
        best_text = None

        for source, column_name, raw in candidate_pool:
            score = self._score_entity_key_candidate(raw)
            token = self._extract_entity_key_token(raw)

            if token and score >= best_score:
                best = raw
                best_score = score
                best_token = token
                best_source = source
                best_column = column_name
                best_text = raw
            elif best is None and score > best_score:
                best = raw
                best_score = score
                best_token = token
                best_source = source
                best_column = column_name
                best_text = raw

        if best_score < 0.45:
            return None

        return {
            "field": "sku",
            "confidence": best_score,
            "sourceHeader": best_source,
            "sourceColumn": best_column,
            "sampleToken": best_token,
            "detectedBy": "value_pattern" if best_token else "header_hint",
            "rawCandidate": best_text,
        }
'''

def replace_function(text: str, func_name: str, replacement: str, next_anchor: str) -> str:
    start = text.find(f"    def {func_name}(")
    if start == -1:
        raise RuntimeError(f"[{func_name}] start not found")
    end = text.find(next_anchor, start)
    if end == -1:
        raise RuntimeError(f"[{func_name}] end anchor not found")
    return text[:start] + replacement + "\n\n" + text[end:]


def main() -> None:
    if not IMPORT_SERVICE.exists():
        raise FileNotFoundError(f"missing file: {IMPORT_SERVICE}")

    text = IMPORT_SERVICE.read_text(encoding="utf-8")
    backup = IMPORT_SERVICE.with_suffix(".py.bak_entity_key_source_column_v1")
    if not backup.exists():
        backup.write_text(text, encoding="utf-8")

    text = replace_function(
        text,
        "_collect_entity_key_probe_values",
        NEW_PROBE_HELPER,
        "    def _build_entity_key_suggestion(\n",
    )
    text = replace_function(
        text,
        "_build_entity_key_suggestion",
        NEW_BUILD_FUNC,
        "    # ---------- 读取 / 表头恢复 ----------\n",
    )

    IMPORT_SERVICE.write_text(text, encoding="utf-8")
    print("Applied entity key source-column patch v1")
    print(f"Patched: {IMPORT_SERVICE}")
    print(f"Backup:  {backup}")


if __name__ == "__main__":
    main()
