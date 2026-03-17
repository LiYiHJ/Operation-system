
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(r"C:\Operation-system\System")
IMPORT_SERVICE = REPO_ROOT / "src" / "ecom_v51" / "services" / "import_service.py"


NEW_TOKEN_BLOCK = """    ENTITY_KEY_TOKEN_PATTERNS = [
        re.compile(r"(?i)(?<![A-Z0-9])[A-Z0-9]{2,}(?:[-_][A-Z0-9]+){1,}(?![A-Z0-9])"),
        re.compile(r"(?<!\\d)\\d{8,14}(?!\\d)"),
    ]
"""

PROBE_HELPER = """    def _collect_entity_key_probe_values(
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

NEW_BUILD_FUNC = """    def _build_entity_key_suggestion(
        self,
        top_unmapped_headers: List[str],
        recovery_candidate_preview: List[dict],
        mapped_canonical_fields: List[str],
        field_mappings: Optional[List[dict]] = None,
        df: Optional[pd.DataFrame] = None,
    ) -> Optional[dict]:
        if "sku" in {str(x) for x in (mapped_canonical_fields or [])}:
            return None

        candidate_pool: List[tuple[str, str]] = []

        for item in top_unmapped_headers or []:
            candidate_pool.append(("topUnmappedHeaders", str(item)))

        for candidate in recovery_candidate_preview or []:
            for example in candidate.get("flattenedHeaderExamples") or []:
                candidate_pool.append(("recoveryCandidatePreview", str(example)))

        for item in field_mappings or []:
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
        best_score = 0.0
        best_token = None
        best_source = None
        best_text = None

        for source, raw in candidate_pool:
            score = self._score_entity_key_candidate(raw)
            token = self._extract_entity_key_token(raw)

            if token and score >= best_score:
                best = raw
                best_score = score
                best_token = token
                best_source = source
                best_text = raw
            elif best is None and score > best_score:
                best = raw
                best_score = score
                best_token = token
                best_source = source
                best_text = raw

        if best_score < 0.45:
            return None

        return {
            "field": "sku",
            "confidence": best_score,
            "sourceHeader": best_source,
            "sampleToken": best_token,
            "detectedBy": "value_pattern" if best_token else "header_hint",
            "rawCandidate": best_text,
        }
"""

NEW_CALL_BLOCK = """        entity_key_suggestion = self._build_entity_key_suggestion(
            top_unmapped_headers=top_unmapped_headers,
            recovery_candidate_preview=recovery_candidate_preview,
            mapped_canonical_fields=mapped_canonical_fields,
            field_mappings=active_bundle.get("fieldMappings") or [],
            df=active_bundle["df"],
        )

"""

OLD_RESULT_SLICE = """            "fieldMappings": active_bundle["fieldMappings"],
            "mappedCanonicalFields": list(
                dict.fromkeys(
                    [
                        str(item.get("standardField"))
                        for item in (active_bundle.get("fieldMappings") or [])
                        if item.get("standardField")
                    ]
                )
            )[:20],
            "topUnmappedHeaders": [
                str(item.get("originalField"))
                for item in (active_bundle.get("fieldMappings") or [])
                if not item.get("standardField") and not item.get("dynamicCompanion")
            ][:20],
"""

NEW_RESULT_SLICE = """            "fieldMappings": active_bundle["fieldMappings"],
            "mappedCanonicalFields": mapped_canonical_fields,
            "topUnmappedHeaders": top_unmapped_headers,
            "entityKeySuggestion": entity_key_suggestion,
"""

OLD_RECOVERY_PREVIEW_SLICE = """            "recoveryDiff": recovery_diff,
            "recoveryCandidatePreview": list(
                recovery_result.get("candidatePreview") or []
            ),
"""

NEW_RECOVERY_PREVIEW_SLICE = """            "recoveryDiff": recovery_diff,
            "recoveryCandidatePreview": recovery_candidate_preview,
"""

def replace_token_block(text: str) -> str:
    start = text.find("    ENTITY_KEY_TOKEN_PATTERNS = [\n")
    if start == -1:
        raise RuntimeError("[token block] start not found")
    end = text.find("    ENTITY_KEY_HEADER_HINTS = [\n", start)
    if end == -1:
        raise RuntimeError("[token block] end anchor not found")
    return text[:start] + NEW_TOKEN_BLOCK + "\n" + text[end:]


def ensure_probe_helper(text: str) -> str:
    if "def _collect_entity_key_probe_values(" in text:
        return text
    anchor = "    def _build_entity_key_suggestion(\n"
    idx = text.find(anchor)
    if idx == -1:
        raise RuntimeError("[probe helper] _build_entity_key_suggestion anchor not found")
    return text[:idx] + PROBE_HELPER + text[idx:]


def replace_build_func(text: str) -> str:
    start = text.find("    def _build_entity_key_suggestion(\n")
    if start == -1:
        raise RuntimeError("[build func] start not found")
    end = text.find("    # ---------- 读取 / 表头恢复 ----------\n", start)
    if end == -1:
        raise RuntimeError("[build func] end anchor not found")
    return text[:start] + NEW_BUILD_FUNC + "\n\n" + text[end:]


def replace_call_block(text: str) -> str:
    start = text.find('        entity_key_suggestion = self._build_entity_key_suggestion(\n')
    if start == -1:
        raise RuntimeError("[helper call] start not found")
    end = text.find("\n        result = {\n", start)
    if end == -1:
        raise RuntimeError("[helper call] end anchor not found")
    return text[:start] + NEW_CALL_BLOCK + text[end + 1:]


def maybe_patch_result_slice(text: str) -> str:
    if '"entityKeySuggestion": entity_key_suggestion,' in text:
        return text
    if OLD_RESULT_SLICE not in text:
        raise RuntimeError("[result slice] expected old result slice not found")
    return text.replace(OLD_RESULT_SLICE, NEW_RESULT_SLICE, 1)


def maybe_patch_recovery_preview(text: str) -> str:
    if '"recoveryCandidatePreview": recovery_candidate_preview,' in text:
        return text
    if OLD_RECOVERY_PREVIEW_SLICE not in text:
        raise RuntimeError("[recovery preview slice] expected old preview slice not found")
    return text.replace(OLD_RECOVERY_PREVIEW_SLICE, NEW_RECOVERY_PREVIEW_SLICE, 1)


def main() -> None:
    if not IMPORT_SERVICE.exists():
        raise FileNotFoundError(f"missing file: {IMPORT_SERVICE}")

    text = IMPORT_SERVICE.read_text(encoding="utf-8")
    backup = IMPORT_SERVICE.with_suffix(".py.bak_entity_key_probe_stateful_v1")
    if not backup.exists():
        backup.write_text(text, encoding="utf-8")

    text = replace_token_block(text)
    text = ensure_probe_helper(text)
    text = replace_build_func(text)
    text = replace_call_block(text)
    text = maybe_patch_result_slice(text)
    text = maybe_patch_recovery_preview(text)

    IMPORT_SERVICE.write_text(text, encoding="utf-8")
    print("Applied entity key probe stateful patch v1")
    print(f"Patched: {IMPORT_SERVICE}")
    print(f"Backup:  {backup}")


if __name__ == "__main__":
    main()
