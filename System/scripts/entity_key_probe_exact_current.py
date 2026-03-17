from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(r"C:\Operation-system\System")
IMPORT_SERVICE = REPO_ROOT / "src" / "ecom_v51" / "services" / "import_service.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"[{label}] expected 1 match, got {count}")
    return text.replace(old, new, 1)


OLD_HELPER_BLOCK = """    ENTITY_KEY_TOKEN_PATTERNS = [
        re.compile(r"(?i)\\b[A-Z0-9]{2,}[-_][A-Z0-9][A-Z0-9_-]{2,}\\b"),
        re.compile(r"\\b\\d{8,14}\\b"),
    ]


    ENTITY_KEY_HEADER_HINTS = [
        "sku",
        "seller_sku",
        "offer_id",
        "offer id",
        "product_id",
        "item_id",
        "asin",
        "ean",
        "barcode",
        "货号",
        "商品编码",
        "商品id",
        "产品编号",
        "产品id",
        "商家编码",
        "条码",
        "артикул",
        "артикул продавца",
        "код товара",
    ]


    def _extract_entity_key_token(self, value: Any) -> Optional[str]:
        text = str(value or "").strip()
        if not text:
            return None

        for pattern in self.ENTITY_KEY_TOKEN_PATTERNS:
            match = pattern.search(text)
            if match:
                return match.group(0)

        return None


    def _score_entity_key_candidate(self, text: str) -> float:
        raw = str(text or "").strip()
        if not raw:
            return 0.0

        score = 0.0
        lower = raw.lower()

        if any(hint in lower for hint in self.ENTITY_KEY_HEADER_HINTS):
            score += 0.35

        token = self._extract_entity_key_token(raw)
        if token:
            score += 0.45
            if "-" in token or "_" in token:
                score += 0.1
            elif token.isdigit() and 8 <= len(token) <= 14:
                score += 0.05

        if raw.startswith("Unnamed:") or raw.startswith("col_"):
            score -= 0.15

        return round(max(score, 0.0), 4)


    def _build_entity_key_suggestion(
        self,
        top_unmapped_headers: List[str],
        recovery_candidate_preview: List[dict],
        mapped_canonical_fields: List[str],
    ) -> Optional[dict]:
        # 如果当前已经映射出 sku，就不需要 suggestion
        if "sku" in {str(x) for x in (mapped_canonical_fields or [])}:
            return None

        candidate_pool: List[tuple[str, str]] = []

        for item in top_unmapped_headers or []:
            candidate_pool.append(("topUnmappedHeaders", str(item)))

        for candidate in recovery_candidate_preview or []:
            for example in candidate.get("flattenedHeaderExamples") or []:
                candidate_pool.append(("recoveryCandidatePreview", str(example)))

        best = None
        best_score = 0.0
        best_token = None
        best_source = None
        best_text = None

        for source, raw in candidate_pool:
            score = self._score_entity_key_candidate(raw)
            token = self._extract_entity_key_token(raw)

            # 优先使用真正提取到 token 的候选
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

NEW_HELPER_BLOCK = """    ENTITY_KEY_TOKEN_PATTERNS = [
        re.compile(r"(?i)(?<![A-Z0-9])[A-Z0-9]{2,}(?:[-_][A-Z0-9]+){1,}(?![A-Z0-9])"),
        re.compile(r"(?<!\\d)\\d{8,14}(?!\\d)"),
    ]


    ENTITY_KEY_HEADER_HINTS = [
        "sku",
        "seller_sku",
        "offer_id",
        "offer id",
        "product_id",
        "item_id",
        "asin",
        "ean",
        "barcode",
        "货号",
        "商品编码",
        "商品id",
        "产品编号",
        "产品id",
        "商家编码",
        "条码",
        "артикул",
        "артикул продавца",
        "код товара",
    ]


    def _extract_entity_key_token(self, value: Any) -> Optional[str]:
        text = str(value or "").strip()
        if not text:
            return None

        for pattern in self.ENTITY_KEY_TOKEN_PATTERNS:
            match = pattern.search(text)
            if match:
                return match.group(0)

        return None


    def _score_entity_key_candidate(self, text: str) -> float:
        raw = str(text or "").strip()
        if not raw:
            return 0.0

        score = 0.0
        lower = raw.lower()

        if any(hint in lower for hint in self.ENTITY_KEY_HEADER_HINTS):
            score += 0.35

        token = self._extract_entity_key_token(raw)
        if token:
            score += 0.45
            if "-" in token or "_" in token:
                score += 0.1
            elif token.isdigit() and 8 <= len(token) <= 14:
                score += 0.05

        if raw.startswith("Unnamed:") or raw.startswith("col_"):
            score -= 0.15

        return round(max(score, 0.0), 4)


    def _collect_entity_key_probe_values(
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


    def _build_entity_key_suggestion(
        self,
        top_unmapped_headers: List[str],
        recovery_candidate_preview: List[dict],
        mapped_canonical_fields: List[str],
        field_mappings: Optional[List[dict]] = None,
        df: Optional[pd.DataFrame] = None,
    ) -> Optional[dict]:
        # 如果当前已经映射出 sku，就不需要 suggestion
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

            # 优先使用真正提取到 token 的候选
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

OLD_CALL = """        entity_key_suggestion = self._build_entity_key_suggestion(
            top_unmapped_headers=top_unmapped_headers,
            recovery_candidate_preview=recovery_candidate_preview,
            mapped_canonical_fields=mapped_canonical_fields,
        )
"""

NEW_CALL = """        entity_key_suggestion = self._build_entity_key_suggestion(
            top_unmapped_headers=top_unmapped_headers,
            recovery_candidate_preview=recovery_candidate_preview,
            mapped_canonical_fields=mapped_canonical_fields,
            field_mappings=active_bundle.get("fieldMappings") or [],
            df=active_bundle["df"],
        )
"""


def main() -> None:
    if not IMPORT_SERVICE.exists():
        raise FileNotFoundError(f"missing file: {IMPORT_SERVICE}")

    text = IMPORT_SERVICE.read_text(encoding="utf-8")
    backup = IMPORT_SERVICE.with_suffix(".py.bak_entity_key_probe_exact_current")
    if not backup.exists():
        backup.write_text(text, encoding="utf-8")

    text = replace_once(text, OLD_HELPER_BLOCK, NEW_HELPER_BLOCK, "replace exact helper block")
    text = replace_once(text, OLD_CALL, NEW_CALL, "replace exact helper call")

    IMPORT_SERVICE.write_text(text, encoding="utf-8")
    print("Applied entity key probe exact-current patch")
    print(f"Patched: {IMPORT_SERVICE}")
    print(f"Backup:  {backup}")


if __name__ == "__main__":
    main()
