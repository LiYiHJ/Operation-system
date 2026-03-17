from __future__ import annotations

from pathlib import Path
import re

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

NEW_CALL = """        entity_key_suggestion = self._build_entity_key_suggestion(
            top_unmapped_headers=top_unmapped_headers,
            recovery_candidate_preview=recovery_candidate_preview,
            mapped_canonical_fields=mapped_canonical_fields,
            field_mappings=active_bundle.get("fieldMappings") or [],
            df=df,
        )
"""

TOKEN_BLOCK_PATTERN = re.compile(
    r'(?ms)^    ENTITY_KEY_TOKEN_PATTERNS = \[\n.*?^    \]\n'
)

BUILD_FUNC_PATTERN = re.compile(
    r'(?ms)^    def _build_entity_key_suggestion\(\n.*?^        return \{\n.*?^        \}\n'
)

CALL_PATTERN = re.compile(
    r'(?ms)^        entity_key_suggestion = self\._build_entity_key_suggestion\(\n.*?^        \)\n'
)


def sub_once(text: str, pattern: re.Pattern[str], replacement: str, label: str) -> str:
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise RuntimeError(f"[{label}] expected 1 match, got {len(matches)}")
    return pattern.sub(lambda _m: replacement, text, count=1)


def main() -> None:
    if not IMPORT_SERVICE.exists():
        raise FileNotFoundError(f"missing file: {IMPORT_SERVICE}")

    text = IMPORT_SERVICE.read_text(encoding="utf-8")
    backup = IMPORT_SERVICE.with_suffix(".py.bak_entity_key_probe_fix_v4")
    if not backup.exists():
        backup.write_text(text, encoding="utf-8")

    text = sub_once(text, TOKEN_BLOCK_PATTERN, NEW_TOKEN_BLOCK, "token block")

    if "def _collect_entity_key_probe_values(" not in text:
        anchor = "    def _build_entity_key_suggestion(\n"
        idx = text.find(anchor)
        if idx == -1:
            raise RuntimeError("[insert probe helper] anchor not found")
        text = text[:idx] + PROBE_HELPER + text[idx:]

    text = sub_once(text, BUILD_FUNC_PATTERN, NEW_BUILD_FUNC, "build_entity_key_suggestion")
    text = sub_once(text, CALL_PATTERN, NEW_CALL, "entity key helper call")

    IMPORT_SERVICE.write_text(text, encoding="utf-8")
    print("Applied entity key probe fix v4")
    print(f"Patched: {IMPORT_SERVICE}")
    print(f"Backup:  {backup}")


if __name__ == "__main__":
    main()
