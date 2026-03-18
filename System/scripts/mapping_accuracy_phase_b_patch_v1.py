
from __future__ import annotations

import re
import textwrap
from pathlib import Path

REPO_ROOT = Path(r"C:\Operation-system\System")
IMPORT_SERVICE = REPO_ROOT / "src" / "ecom_v51" / "services" / "import_service.py"
DATAIMPORT_PAGE = REPO_ROOT / "frontend" / "src" / "pages" / "DataImportV2.tsx"


def sub_once(text: str, pattern: str, repl: str, label: str) -> str:
    new_text, count = re.subn(pattern, lambda m: repl, text, count=1, flags=re.S | re.M)
    if count != 1:
        raise RuntimeError(f"[{label}] expected 1 match, got {count}")
    return new_text


def indent4(block: str) -> str:
    return textwrap.indent(textwrap.dedent(block).lstrip("\n"), "    ")


CONSTANTS_BLOCK = indent4("""
DYNAMIC_PATTERNS = [
    "динамик",
    "изменени",
    "change",
    "delta",
    "trend",
    "рост",
    "снижение",
]
SOFT_EXCLUDE_PATTERNS = [
    "динамик",
    "доля",
    "abc-анализ",
    "abc анализ",
    "рекомендац",
    "сколько товаров",
    "среднее время доставки",
    "по сравнению с предыдущим периодом",
]
GENERIC_HEADER_PIECES = {
    "товар",
    "товары",
    "товара",
    "период",
    "показатель",
    "значение",
    "метрика",
    "динамика",
    "изменение",
    "итого",
    "всего",
    "дата",
    "категория",
    "ozon",
    "seller",
    "sku",
    "report",
    "summary",
    "section",
    "metric",
}
PROTECTED_UNIQUE_TARGETS = {
    "sku",
    "orders",
    "order_amount",
    "impressions_total",
    "impressions_search_catalog",
    "product_card_visits",
    "add_to_cart_total",
    "stock_total",
    "review_count",
    "rating_value",
    "price_index_status",
}
RU_PHRASE_CANONICAL_RULES = [
    (["артикул"], "sku"),
    (["seller sku"], "sku"),
    (["offer id"], "sku"),
    (["показы в поиске", "каталоге"], "impressions_search_catalog"),
    (["показы", "всего"], "impressions_total"),
    (["посещ", "карточк"], "product_card_visits"),
    (["переход", "карточк"], "product_card_visits"),
    (["добав", "корзин"], "add_to_cart_total"),
    (["заказано на сумму"], "order_amount"),
    (["сумма заказ"], "order_amount"),
    (["остат", "склад"], "stock_total"),
    (["в наличии"], "stock_total"),
    (["рейтинг"], "rating_value"),
    (["отзыв"], "review_count"),
    (["индекс цен"], "price_index_status"),
    (["средняя позиция", "поиск"], "search_catalog_position_avg"),
]

""")

FLATTEN_BLOCK = indent4("""
def _flatten_headers(
    self, raw_df: pd.DataFrame, header_block: dict
) -> Tuple[List[str], List[str], List[str]]:
    start = int(header_block.get("startRow") or 0)
    end = int(header_block.get("endRow") or start)
    header_rows = raw_df.iloc[start : end + 1].fillna("")
    flattened: List[str] = []
    dropped: List[str] = []
    rescued: List[str] = []
    for col_idx in range(raw_df.shape[1]):
        specific_pieces: List[str] = []
        fallback_pieces: List[str] = []
        for _, row in header_rows.iterrows():
            value = str(self._safe_scalar(row.iloc[col_idx]) or "").strip()
            norm = self._normalize_header(value)
            if value and norm not in {"nan", "none"}:
                fallback_pieces.append(value)
                if norm not in self.GENERIC_HEADER_PIECES:
                    specific_pieces.append(value)
        deduped_specific = list(dict.fromkeys(specific_pieces))
        deduped_fallback = list(dict.fromkeys(fallback_pieces))

        if deduped_specific:
            joined = " / ".join(deduped_specific[-2:]).strip()
        elif deduped_fallback:
            joined = deduped_fallback[-1].strip()
        else:
            joined = f"col_{col_idx + 1}"

        if self._is_placeholder_col(joined):
            dropped.append(joined)
        elif len(deduped_specific) > 1:
            rescued.append(joined)
        flattened.append(joined)
    return flattened, dropped, rescued

""")

HELPER_BLOCK = indent4("""
def _is_dynamic_companion(self, text: str) -> bool:
    normalized = self._normalize_header(text)
    return any(token in normalized for token in self.DYNAMIC_PATTERNS)

def _is_soft_excluded_header(self, text: str) -> bool:
    normalized = self._normalize_header(text)
    return any(token in normalized for token in self.SOFT_EXCLUDE_PATTERNS)

def _looks_like_explainer_text(self, text: str) -> bool:
    raw = str(text or "").strip().lower()
    if not raw:
        return False
    return (
        len(raw) >= 40
        or "оцениваем" in raw
        or "считаем" in raw
        or "для этого" in raw
        or "динамика по сравнению" in raw
        or "товары a приносят" in raw
    )

def _to_number_like(self, value: Any) -> Optional[float]:
    text = str(value or "").strip()
    if not text:
        return None
    text = text.replace("\\u00a0", " ").replace("₽", "")
    text = text.replace("%", "").replace(" ", "")
    text = text.replace(",", ".")
    try:
        return float(text)
    except Exception:
        return None

def _sample_quality_score(self, canonical: Optional[str], value: Any) -> float:
    text = str(value or "").strip()
    if not text or text.lower() == "nan":
        return -1.0
    if self._looks_like_explainer_text(text):
        return -5.0
    if canonical == "sku":
        if len(text) <= 40 and any(ch.isalpha() for ch in text):
            return 3.0
        if text.isdigit():
            return 0.5
        return 0.0
    if canonical in self.NUMERIC_CANONICALS or (canonical or "").endswith("_cvr"):
        parsed = self._to_number_like(text)
        return 2.0 if parsed is not None else -2.0
    return 1.0

def _dedupe_auto_targets(self, field_mappings: List[dict]) -> List[dict]:
    grouped: Dict[str, List[dict]] = {}
    for item in field_mappings or []:
        target = str(item.get("standardField") or "").strip()
        if not target:
            continue
        grouped.setdefault(target, []).append(item)

    for target, items in grouped.items():
        if target not in self.PROTECTED_UNIQUE_TARGETS or len(items) <= 1:
            continue

        def sort_key(item: dict) -> tuple:
            reasons = item.get("reasons") or []
            original = self._normalize_header(item.get("originalField") or "")
            sample_values = item.get("sampleValues") or []
            sample_bonus = 0.0
            if sample_values:
                sample_bonus = self._sample_quality_score(target, sample_values[0])
            ru_article_bonus = 1 if "артикул" in original else 0
            alias_bonus = 1 if any(
                str(r).startswith("normalized") or str(r).startswith("without_unit")
                for r in reasons
            ) else 0
            return (float(item.get("confidence") or 0.0), ru_article_bonus, alias_bonus, sample_bonus)

        ranked = sorted(items, key=sort_key, reverse=True)
        for loser in ranked[1:]:
            loser["standardField"] = None
            loser["mappingSource"] = "conflict_dropped"
            loser["confidence"] = 0.0
            loser["reasons"] = list(
                dict.fromkeys(list(loser.get("reasons") or []) + [f"duplicate_target:{target}"])
            )
    return field_mappings

""")

COMPRESS_BLOCK = indent4("""
def _compress_header_phrase(self, original: Any) -> List[Tuple[str, str]]:
    text = str(original or "").strip()
    normalized = self._normalize_header(text)
    normalized_wo_unit = self._normalize_header_without_unit(text)
    candidates: List[Tuple[str, str]] = []
    seen: set[str] = set()
    soft_excluded = self._is_soft_excluded_header(text)

    def push(value: str, reason: str) -> None:
        value = value.strip()
        if value and value not in seen:
            seen.add(value)
            candidates.append((value, reason))

    push(normalized, "normalized")
    if normalized_wo_unit != normalized:
        push(normalized_wo_unit, "without_unit")

    if not soft_excluded:
        for needles, canonical in self.RU_PHRASE_CANONICAL_RULES:
            if all(needle in normalized_wo_unit for needle in needles):
                push(canonical, f"phrase_rule:{canonical}")

    tokens = [
        tok for tok in re.split(r"[^a-zа-я0-9一-龥]+", normalized_wo_unit) if tok
    ]
    meaningful = [
        tok
        for tok in tokens
        if tok not in self.GENERIC_HEADER_PIECES and len(tok) > 2
    ]
    if meaningful and not soft_excluded:
        push(" ".join(dict.fromkeys(meaningful)), "token_compaction")
    return candidates

""")

DETAILS_BLOCK = indent4("""
def _map_single_column_details(
    self, col: Any, sample_values: Optional[List[Any]] = None
) -> Dict[str, Any]:
    original = str(col or "")
    normalized = self._normalize_header(original)
    compressed = self._compress_header_phrase(original)
    dynamic_companion = self._is_dynamic_companion(original)
    soft_excluded = self._is_soft_excluded_header(original)
    reasons: List[str] = []
    conflicts: List[str] = []
    best_canonical: Optional[str] = None
    best_source = "unmapped"
    best_confidence = 0.0
    best_compressed = None

    if dynamic_companion:
        return {
            "originalField": original,
            "normalizedField": normalized,
            "standardField": None,
            "mappingSource": "dynamic_companion",
            "confidence": 0.0,
            "sampleValues": list(sample_values or []),
            "isManual": False,
            "reasons": ["dynamic_companion"],
            "conflicts": conflicts,
            "dynamicCompanion": True,
            "compressedHeader": None,
            "excludeFromSemanticGate": True,
        }

    if soft_excluded:
        return {
            "originalField": original,
            "normalizedField": normalized,
            "standardField": None,
            "mappingSource": "soft_excluded",
            "confidence": 0.0,
            "sampleValues": list(sample_values or []),
            "isManual": False,
            "reasons": ["soft_excluded_header"],
            "conflicts": conflicts,
            "dynamicCompanion": False,
            "compressedHeader": None,
            "excludeFromSemanticGate": False,
        }

    def score_candidate(
        candidate_text: str, candidate_reason: str
    ) -> Tuple[Optional[str], str, float, List[str]]:
        local_reasons: List[str] = []
        if candidate_text in self._alias_lookup:
            local_reasons.append(candidate_reason)
            return (
                self._alias_lookup[candidate_text],
                "registry_alias",
                0.99,
                local_reasons,
            )
        for alias, canonical in self._fallback_mapping.ozon_mapping.items():
            if self._normalize_header(alias) == candidate_text:
                local_reasons.append(candidate_reason)
                return canonical, "ru_builtin", 0.95, local_reasons
        for alias, canonical in self._fallback_mapping.english_mapping.items():
            if self._normalize_header(alias) == candidate_text:
                local_reasons.append(candidate_reason)
                return canonical, "en_builtin", 0.95, local_reasons
        cand_tokens = set(
            t for t in re.split(r"[^a-zа-я0-9一-龥]+", candidate_text) if len(t) > 2
        )
        best_overlap = (None, 0.0)
        for alias_norm, canonical in self._alias_lookup.items():
            alias_tokens = set(
                t for t in re.split(r"[^a-zа-я0-9一-龥]+", alias_norm) if len(t) > 2
            )
            if not cand_tokens or not alias_tokens:
                continue
            overlap = len(cand_tokens & alias_tokens) / max(len(alias_tokens), 1)
            if overlap > best_overlap[1]:
                best_overlap = (canonical, overlap)
        if best_overlap[0] and best_overlap[1] >= 0.66:
            local_reasons.append(f"token_overlap:{best_overlap[1]:.2f}")
            return (
                best_overlap[0],
                "token_overlap",
                round(0.55 + best_overlap[1] * 0.25, 3),
                local_reasons,
            )
        return None, "unmapped", 0.0, local_reasons

    for candidate_text, candidate_reason in compressed:
        canonical, source, confidence, local_reasons = score_candidate(
            candidate_text, candidate_reason
        )
        if canonical and confidence > best_confidence:
            if best_canonical and best_canonical != canonical:
                conflicts.append(best_canonical)
            best_canonical = canonical
            best_source = source
            best_confidence = confidence
            best_compressed = candidate_text
            reasons = local_reasons

    if best_canonical == "sku":
        allowed = {"sku", "seller sku", "offer id", "артикул", "артикул товара"}
        if normalized not in {self._normalize_header(x) for x in allowed}:
            best_canonical = None
            best_source = "unmapped"
            best_confidence = 0.0
            reasons = ["sku_guard_rejected"]

    return {
        "originalField": original,
        "normalizedField": normalized,
        "standardField": best_canonical,
        "mappingSource": best_source,
        "confidence": best_confidence,
        "sampleValues": list(sample_values or []),
        "isManual": False,
        "reasons": reasons,
        "conflicts": conflicts,
        "dynamicCompanion": dynamic_companion,
        "compressedHeader": best_compressed,
        "excludeFromSemanticGate": False,
    }

""")

PREVIEW_BLOCK = indent4("""
def _preview_values_for_column(
    self,
    df: pd.DataFrame,
    col: Any,
    limit: int = 3,
    canonical_hint: Optional[str] = None,
) -> List[Any]:
    if col not in df.columns:
        return []
    selected = df.loc[:, col]
    raw_candidates: List[Any] = []
    scan_limit = max(limit * 8, 24)

    if isinstance(selected, pd.DataFrame):
        rows = selected.head(scan_limit).itertuples(index=False, name=None)
        for row in rows:
            for item in row if isinstance(row, tuple) else (row,):
                raw_candidates.append(self._safe_scalar(item))
    else:
        try:
            raw_candidates = selected.head(scan_limit).tolist()
        except Exception:
            raw_candidates = (
                selected.head(scan_limit).values.tolist()
                if hasattr(selected.head(scan_limit), "values")
                else []
            )

    scored: List[Tuple[float, int, Any]] = []
    for idx, item in enumerate(raw_candidates):
        nested_items = item if isinstance(item, list) else [item]
        for nested in nested_items:
            scalar = self._safe_scalar(nested)
            text = str(scalar or "").strip()
            if not text or text.lower() == "nan":
                continue
            if self._looks_like_explainer_text(text):
                continue
            score = self._sample_quality_score(canonical_hint, scalar)
            scored.append((score, idx, scalar))

    scored.sort(key=lambda x: (x[0], -x[1]), reverse=True)
    values: List[Any] = []
    seen: set[str] = set()
    for score, _, scalar in scored:
        if score < 0:
            continue
        key = str(scalar)
        if key in seen:
            continue
        seen.add(key)
        values.append(scalar)
        if len(values) >= limit:
            break
    return values[:limit]

""")

MAP_COLUMNS_BLOCK = indent4("""
def map_columns(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[dict]]:
    field_mappings: List[dict] = []

    for col in df.columns:
        seed_details = self._map_single_column_details(col, sample_values=[])
        canonical_hint = seed_details.get("standardField")
        sample_values = self._preview_values_for_column(
            df,
            col,
            limit=3,
            canonical_hint=str(canonical_hint) if canonical_hint else None,
        )
        details = self._map_single_column_details(col, sample_values=sample_values)
        field_mappings.append(details)

    field_mappings = self._dedupe_auto_targets(field_mappings)

    rename_map: Dict[str, str] = {}
    for details in field_mappings:
        canonical = details.get("standardField")
        original_field = str(details.get("originalField") or "")
        if canonical and original_field:
            rename_map[original_field] = str(canonical)

    mapped_df = df.rename(columns=rename_map)
    mapped_df = self._collapse_duplicate_columns(mapped_df)
    return mapped_df, field_mappings

""")

FRONT_INSERT = textwrap.dedent("""
const PROTECTED_TARGETS = new Set([
  'sku',
  'orders',
  'order_amount',
  'impressions_total',
  'impressions_search_catalog',
  'product_card_visits',
  'add_to_cart_total',
  'stock_total',
  'rating_value',
  'review_count',
  'price_index_status',
])

const findProtectedTargetConflicts = (mappings: FieldMapping[]) => {
  const grouped = new Map<string, FieldMapping[]>()
  for (const item of mappings || []) {
    const target = item?.standardField || null
    if (!target || !PROTECTED_TARGETS.has(target)) continue
    if (!grouped.has(target)) grouped.set(target, [])
    grouped.get(target)!.push(item)
  }
  return [...grouped.entries()].filter(([, items]) => items.length > 1)
}

const STANDARD_FIELDS: Record<string, StandardFieldConfig> = {
""")

FRONT_CONFIRM = textwrap.dedent("""
  const confirmImport = async () => {
    if (!importResult) return

    const confirmedOverrides = buildConfirmedOverrides()
    const effectiveByOriginal = new Map<string, FieldMapping>()
    for (const item of importResult.fieldMappings || []) {
      effectiveByOriginal.set(item.originalField, { ...item })
    }
    for (const item of confirmedOverrides) {
      effectiveByOriginal.set(item.originalField, {
        ...(effectiveByOriginal.get(item.originalField) || item),
        ...item,
        isManual: true,
      })
    }

    const protectedConflicts = findProtectedTargetConflicts([...effectiveByOriginal.values()])
    if (protectedConflicts.length > 0) {
      Modal.error({
        title: '存在重复目标字段映射',
        content: (
          <div>
            {protectedConflicts.map(([target, items]) => (
              <div key={target}>
                {target}: {items.map((x) => x.originalField).join('、')}
              </div>
            ))}
          </div>
        ),
      })
      return
    }

    if (importResult.finalStatus === 'risk') {
      const reasons =
        (importResult.semanticGateReasons || importResult.semanticAcceptanceReason || []).join('、') ||
        'semantic_gate_not_met'

      const proceed = await new Promise<boolean>((resolve) => {
        Modal.confirm({
          title: '存在语义风险，确认继续导入？',
          icon: <ExclamationCircleOutlined />,
          content: `finalStatus=risk，原因：${reasons}`,
          okText: '继续导入',
          cancelText: '返回检查',
          okButtonProps: { danger: true },
          onOk: () => resolve(true),
          onCancel: () => resolve(false),
        })
      })

      if (!proceed) return
    }

    setImporting(true)
    try {
      const raw = await importApi.confirmImport({
        sessionId: importResult.sessionId,
        shopId: SHOP_ID,
        operator: 'ui_manual_confirmation',
        manualOverrides: confirmedOverrides,
      })

      const result = normalizeConfirmResult(raw)
      console.log('confirm raw ->', raw)
      console.log('confirm normalized ->', result)
      if (result?.status !== 'success') {
        throw new Error(result?.errors?.[0] || '导入失败')
      }

      setConfirmResult(result)

      if (result.importabilityStatus === 'risk') {
        message.warning(
          `导入完成，但仍存在可提交性风险：${(result.importabilityReasons || []).join('、') || 'importability_risk'}`,
        )
      } else {
        message.success(`成功导入 ${result.importedRows || 0} 条数据`)
      }

      setCurrentStep(3)
    } catch (error: any) {
      message.error(`导入失败: ${error?.message || '未知错误'}`)
    } finally {
      setImporting(false)
    }
  }

""")


def patch_import_service() -> None:
    text = IMPORT_SERVICE.read_text(encoding="utf-8")
    backup = IMPORT_SERVICE.with_suffix(".py.bak_mapping_accuracy_phase_b_v1")
    if not backup.exists():
        backup.write_text(text, encoding="utf-8")

    text = sub_once(text, r"    DYNAMIC_PATTERNS = \[[\s\S]*?^    def __init__", CONSTANTS_BLOCK + "    def __init__", "constants")
    text = sub_once(text, r"    def _flatten_headers\([\s\S]*?^    def _materialize_from_raw", FLATTEN_BLOCK + "    def _materialize_from_raw", "flatten_headers")
    text = sub_once(text, r"    def _is_dynamic_companion\([\s\S]*?^    def _compress_header_phrase", HELPER_BLOCK + "    def _compress_header_phrase", "helpers")
    text = sub_once(text, r"    def _compress_header_phrase\([\s\S]*?^    def _map_single_column_details", COMPRESS_BLOCK + "    def _map_single_column_details", "compress_header_phrase")
    text = sub_once(text, r"    def _map_single_column_details\([\s\S]*?^    def _map_single_column", DETAILS_BLOCK + "    def _map_single_column", "map_single_column_details")
    text = sub_once(text, r"    def _preview_values_for_column\([\s\S]*?^    @staticmethod\n    def _collapse_duplicate_columns", PREVIEW_BLOCK + "    @staticmethod\n    def _collapse_duplicate_columns", "preview_values_for_column")
    text = sub_once(text, r"    def map_columns\(self, df: pd.DataFrame\) -> Tuple\[pd.DataFrame, List\[dict\]\]:[\s\S]*?^    def clean_data", MAP_COLUMNS_BLOCK + "    def clean_data", "map_columns")

    IMPORT_SERVICE.write_text(text, encoding="utf-8")


def patch_dataimport_page() -> None:
    text = DATAIMPORT_PAGE.read_text(encoding="utf-8")
    backup = DATAIMPORT_PAGE.with_suffix(".tsx.bak_mapping_accuracy_phase_b_v1")
    if not backup.exists():
        backup.write_text(text, encoding="utf-8")

    if "const PROTECTED_TARGETS = new Set([" not in text:
        text = text.replace(
            "const STANDARD_FIELDS: Record<string, StandardFieldConfig> = {",
            FRONT_INSERT,
            1,
        )

    text = sub_once(
        text,
        r"  const confirmImport = async \(\) => \{[\s\S]*?^  const renderUploadStep = \(\) => \(",
        FRONT_CONFIRM + "  const renderUploadStep = () => (",
        "confirm_import",
    )

    DATAIMPORT_PAGE.write_text(text, encoding="utf-8")


def main() -> None:
    if not IMPORT_SERVICE.exists():
        raise FileNotFoundError(f"missing file: {IMPORT_SERVICE}")
    if not DATAIMPORT_PAGE.exists():
        raise FileNotFoundError(f"missing file: {DATAIMPORT_PAGE}")

    patch_import_service()
    patch_dataimport_page()

    print("Applied mapping accuracy Phase B patch v1")
    print(f"Patched: {IMPORT_SERVICE}")
    print(f"Patched: {DATAIMPORT_PAGE}")


if __name__ == "__main__":
    main()
