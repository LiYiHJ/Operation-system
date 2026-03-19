from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'src' / 'ecom_v51' / 'services' / 'import_service.py'
BACKUP = ROOT / 'docs' / 'mapping_accuracy_safe_patch_v3.import_service.backup.py'


def replace_method(text: str, name: str, new_src: str) -> tuple[str, int]:
    pattern = re.compile(rf"(?ms)^    def {re.escape(name)}\(.*?(?=^    def |\Z)")
    return pattern.subn(new_src.rstrip() + "\n\n", text, count=1)


def insert_before_method(text: str, method_name: str, block: str, marker: str) -> tuple[str, int]:
    if marker in text:
        return text, 0
    pattern = re.compile(rf"(?m)^    def {re.escape(method_name)}\(")
    match = pattern.search(text)
    if not match:
        raise RuntimeError(f"插入失败：未找到方法 {method_name}")
    new_text = text[:match.start()] + block.rstrip() + "\n\n" + text[match.start():]
    return new_text, 1


def replace_once_regex(text: str, pattern: str, repl: str, label: str, required: bool = True) -> tuple[str, int]:
    new_text, count = re.subn(pattern, repl, text, count=1, flags=re.M | re.S)
    if required and count != 1:
        raise RuntimeError(f"{label} 替换失败，命中次数={count}")
    return new_text, count


def main() -> None:
    if not TARGET.exists():
        raise FileNotFoundError(f"未找到目标文件: {TARGET}")

    text = TARGET.read_text(encoding='utf-8')
    original = text
    applied: list[str] = []

    constants_block = '''    PROTECTED_TARGETS = set(CORE_FIELDS)

    CORE_SAFE_NOISE_TOKENS = {
        "динамик": "dynamic",
        "изменени": "dynamic",
        "trend": "dynamic",
        "delta": "dynamic",
        "change": "dynamic",
        "рост": "dynamic",
        "снижение": "dynamic",
        "доля": "share",
        "share": "share",
        "процент": "share",
        "%": "share",
        "abc": "abc",
        "abc-анализ": "abc",
        "рекомендац": "recommendation",
        "recommend": "recommendation",
        "建议": "recommendation",
        "平均时效": "ops_extension",
        "补货": "ops_extension",
        "时效": "ops_extension",
        "оборач": "ops_extension",
        "доставка": "ops_extension",
    }

    MAX_SAMPLE_VALUE_LENGTH = 72
    MAX_SAMPLE_VALUE_TOKENS = 8
    ENTITY_KEY_MIN_CONFIDENCE = 0.58
'''

    helper_block = '''    @staticmethod
    def _normalize_preview_text(value: Any) -> str:
        if value is None:
            return ""
        text = str(value).strip()
        text = re.sub(r"\\s+", " ", text)
        return text

    def _looks_like_explanatory_text(self, value: Any) -> bool:
        text = self._normalize_preview_text(value)
        if not text:
            return False

        if len(text) > self.MAX_SAMPLE_VALUE_LENGTH:
            return True

        if text.count(".") >= 2:
            return True

        comma_count = text.count(",") + text.count("，") + text.count("；") + text.count(";")
        if comma_count >= 2:
            return True

        tokens = [x for x in re.split(r"[\\s/|,;:]+", text) if x]
        if len(tokens) > self.MAX_SAMPLE_VALUE_TOKENS:
            return True

        return False

    def _detect_core_safe_noise(self, value: Any) -> Optional[str]:
        text = self._normalize_preview_text(value).lower()
        if not text:
            return None

        for token, label in self.CORE_SAFE_NOISE_TOKENS.items():
            if token in text:
                return label

        if self._looks_like_explanatory_text(text):
            return "explanatory_text"

        return None

    def _sanitize_sample_values(self, values: List[Any], limit: int = 3) -> List[Any]:
        cleaned = []
        seen = set()

        for raw in values or []:
            scalar = self._safe_scalar(raw)
            if scalar is None:
                continue

            if isinstance(scalar, float) and pd.isna(scalar):
                continue

            if isinstance(scalar, (int, float)) and not isinstance(scalar, bool):
                text = str(scalar)
                if text not in seen:
                    seen.add(text)
                    cleaned.append(scalar)
                if len(cleaned) >= limit:
                    break
                continue

            text = self._normalize_preview_text(scalar)
            if not text or text.lower() == "nan":
                continue

            if self._looks_like_explanatory_text(text):
                continue

            if text in seen:
                continue

            seen.add(text)
            cleaned.append(text)
            if len(cleaned) >= limit:
                break

        return cleaned

    def _mapping_priority_score(self, item: dict) -> float:
        score = float(item.get("confidence") or 0.0)
        source = str(item.get("mappingSource") or "").lower()
        reasons = {str(x).lower() for x in (item.get("reasons") or [])}

        if item.get("isManual"):
            score += 100.0

        if any(x in source for x in ["registry", "alias", "exact", "canonical"]):
            score += 30.0
        elif any(x in source for x in ["phrase", "rule"]):
            score += 15.0

        if "manual_mapping" in reasons:
            score += 20.0

        if "core_safe_noise_filtered" in reasons:
            score -= 50.0

        original = str(item.get("originalField") or "")
        if original.startswith("Unnamed:") or original.startswith("col_"):
            score -= 5.0

        return score

    def _sanitize_and_reconcile_field_mappings(self, field_mappings: List[dict]) -> List[dict]:
        normalized = []
        protected_best = {}

        for idx, item in enumerate(field_mappings or []):
            current = dict(item or {})
            current["sampleValues"] = self._sanitize_sample_values(current.get("sampleValues") or [], limit=3)

            reasons = [str(x) for x in (current.get("reasons") or [])]
            original_field = str(current.get("originalField") or "")
            standard_field = current.get("standardField")
            noise_label = self._detect_core_safe_noise(original_field)

            if standard_field in self.CORE_FIELDS and noise_label and standard_field != "sku":
                current["noiseCategory"] = noise_label
                current["filteredOutByCoreSafe"] = True
                current["standardField"] = None
                current["dynamicCompanion"] = None
                current["confidence"] = min(float(current.get("confidence") or 0.0), 0.35)
                current["reasons"] = list(dict.fromkeys(reasons + ["core_safe_noise_filtered", f"noise:{noise_label}"]))
            else:
                if noise_label:
                    current["noiseCategory"] = noise_label
                current["reasons"] = reasons

            normalized.append(current)

            protected_target = current.get("standardField")
            if protected_target in self.PROTECTED_TARGETS:
                score = self._mapping_priority_score(current)
                best = protected_best.get(protected_target)
                if best is None or score > best[0]:
                    protected_best[protected_target] = (score, idx)

        for idx, current in enumerate(normalized):
            protected_target = current.get("standardField")
            if protected_target not in self.PROTECTED_TARGETS:
                continue

            winner_idx = protected_best.get(protected_target, (0.0, -1))[1]
            if winner_idx == idx:
                continue

            current["reasons"] = list(dict.fromkeys([*(current.get("reasons") or []), "protected_target_conflict_dropped"]))
            current["standardField"] = None
            current["dynamicCompanion"] = None
            current["confidence"] = min(float(current.get("confidence") or 0.0), 0.25)

        return normalized
'''

    new_preview = '''    def _preview_values_for_column(
        self, df: pd.DataFrame, col: Any, limit: int = 3
    ) -> List[Any]:
        if col not in df.columns:
            return []

        selected = df.loc[:, col]
        raw_values = []

        if isinstance(selected, pd.DataFrame):
            for row in selected.head(max(limit * 3, 9)).itertuples(index=False, name=None):
                for item in row if isinstance(row, tuple) else (row,):
                    raw_values.append(self._safe_scalar(item))
                    if len(raw_values) >= max(limit * 4, 12):
                        return self._sanitize_sample_values(raw_values, limit=limit)
            return self._sanitize_sample_values(raw_values, limit=limit)

        try:
            source = selected.head(max(limit * 3, 9)).tolist()
        except Exception:
            head_values = selected.head(max(limit * 3, 9))
            source = head_values.values.tolist() if hasattr(head_values, "values") else []

        for item in source:
            if isinstance(item, list):
                for nested in item:
                    raw_values.append(self._safe_scalar(nested))
            else:
                raw_values.append(self._safe_scalar(item))

            if len(raw_values) >= max(limit * 4, 12):
                break

        return self._sanitize_sample_values(raw_values, limit=limit)
'''

    new_score = '''    def _score_entity_key_candidate(self, text: str) -> float:
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

        if self._detect_core_safe_noise(raw):
            score -= 0.35

        if self._looks_like_explanatory_text(raw):
            score -= 0.4

        if raw.startswith("Unnamed:") or raw.startswith("col_"):
            score -= 0.15

        return round(max(score, 0.0), 4)
'''

    new_collect = '''    def _collect_entity_key_probe_values(
        self,
        df: pd.DataFrame,
        field_mappings: List[dict],
        limit: int = 12,
    ) -> List[tuple[str, str]]:
        values = []
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

            if self._detect_core_safe_noise(header):
                continue

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

                if self._detect_core_safe_noise(text):
                    continue

                token = self._extract_entity_key_token(text)
                if token:
                    values.append((header, token))
                elif not self._looks_like_explanatory_text(text) and len(text) <= 48:
                    values.append((header, text))

                if len(values) >= limit:
                    return values

        return values
'''

    new_build = '''    def _build_entity_key_suggestion(
        self,
        field_mappings: List[dict],
        profile: Optional[dict] = None,
        df: Optional[pd.DataFrame] = None,
    ) -> Optional[dict]:
        profile = profile or {}
        candidate_pool = []

        for value in profile.get("topUnmappedHeaders") or []:
            if value:
                candidate_pool.append(("profile.topUnmappedHeaders", None, str(value)))

        for value in profile.get("recoveryCandidatePreview") or []:
            if value:
                candidate_pool.append(("profile.recoveryCandidatePreview", None, str(value)))

        for item in field_mappings or []:
            if item.get("standardField") == "sku":
                return None

            original_field = str(item.get("originalField") or "")
            if original_field:
                candidate_pool.append(("fieldMappings.originalField", original_field, original_field))

            for value in self._sanitize_sample_values(item.get("sampleValues") or [], limit=3):
                candidate_pool.append(("fieldMappings.sampleValues", original_field or None, str(value)))

        if df is not None:
            for column_name, value in self._collect_entity_key_probe_values(df, field_mappings):
                candidate_pool.append(("dataProbeValues", column_name, value))

        best_score = 0.0
        best_item = None

        for source, column_name, raw in candidate_pool:
            if self._detect_core_safe_noise(raw):
                continue

            score = self._score_entity_key_candidate(raw)
            if score <= 0:
                continue

            token = self._extract_entity_key_token(raw)
            if source == "fieldMappings.originalField" and column_name and (
                column_name.startswith("Unnamed:") or column_name.startswith("col_")
            ):
                score -= 0.05

            if score > best_score:
                best_score = score
                best_item = {
                    "standardField": "sku",
                    "source": source,
                    "originalField": column_name,
                    "confidence": round(max(score, 0.0), 4),
                    "sampleToken": token,
                    "reason": f"entity_key_candidate:{source}",
                }

        if best_item is None or best_score < self.ENTITY_KEY_MIN_CONFIDENCE:
            return None

        return best_item
'''

    text, count = insert_before_method(text, '_preview_values_for_column', constants_block, 'CORE_SAFE_NOISE_TOKENS')
    if count:
        applied.append('constants')

    text, count = insert_before_method(text, '_preview_values_for_column', helper_block, 'def _normalize_preview_text')
    if count:
        applied.append('helpers')

    for name, src in [
        ('_preview_values_for_column', new_preview),
        ('_score_entity_key_candidate', new_score),
        ('_collect_entity_key_probe_values', new_collect),
        ('_build_entity_key_suggestion', new_build),
    ]:
        text, count = replace_method(text, name, src)
        if count != 1:
            raise RuntimeError(f"方法替换失败: {name}, 命中次数={count}")
        applied.append(name)

    ru_patterns = [
        r'(?m)^\s*\(\["показы"\],\s*"impressions_total"\),\n?',
        r'(?m)^\s*\(\["заказ"\],\s*"orders"\),\n?',
        r'(?m)^\s*\(\["рейтинг"\],\s*"rating_value"\),\n?',
        r'(?m)^\s*\(\["отзыв"\],\s*"review_count"\),\n?',
    ]
    removed = 0
    for pattern in ru_patterns:
        text, count = re.subn(pattern, '', text)
        removed += count
    if removed:
        applied.append(f'ru_rules_removed:{removed}')

    parse_patterns = [
        (
            r'(?m)^(\s*)entity_key_suggestion\s*=\s*self\._build_entity_key_suggestion\(',
            r'\1field_mappings = self._sanitize_and_reconcile_field_mappings(field_mappings)\n\1entity_key_suggestion = self._build_entity_key_suggestion(',
        ),
        (
            r'(?m)^(\s*)return\s*\{',
            r'\1field_mappings = self._sanitize_and_reconcile_field_mappings(field_mappings)\n\1return {',
        ),
    ]
    parse_applied = False
    for pattern, repl in parse_patterns:
        try:
            new_text, count = replace_once_regex(text, pattern, repl, 'parse后处理插入', required=False)
        except RuntimeError:
            count = 0
            new_text = text
        if count == 1:
            text = new_text
            parse_applied = True
            applied.append('parse_postprocess')
            break
    if not parse_applied:
        raise RuntimeError('parse后处理插入失败，未找到 entity_key_suggestion 或 return 位置')

    if text == original:
        raise RuntimeError('补丁未产生任何变更，请检查当前源文件版本')

    BACKUP.parent.mkdir(parents=True, exist_ok=True)
    BACKUP.write_text(original, encoding='utf-8')
    TARGET.write_text(text, encoding='utf-8')

    print('OK')
    print(f'target={TARGET}')
    print(f'backup={BACKUP}')
    print('applied=' + ', '.join(applied))


if __name__ == '__main__':
    main()
