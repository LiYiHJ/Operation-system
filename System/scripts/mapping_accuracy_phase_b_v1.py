
from __future__ import annotations

from pathlib import Path
import re

REPO_ROOT = Path(r"C:\Operation-system\System")
IMPORT_SERVICE = REPO_ROOT / "src" / "ecom_v51" / "services" / "import_service.py"
FRONTEND_PAGE = REPO_ROOT / "frontend" / "src" / "pages" / "DataImportV2.tsx"


BACKEND_HELPERS = """
    def _looks_like_explainer_text(self, text) -> bool:
        s = str(text or "").strip()
        if not s:
            return False
        lowered = s.lower()
        if len(lowered) >= 40:
            return True
        patterns = [
            "оцениваем",
            "считаем",
            "для этого",
            "динамика по сравнению",
            "товары a приносят",
            "по общей стоимости",
            "по общему количеству",
            "проверяем остатки",
            "средний срок доставки",
        ]
        return any(p in lowered for p in patterns)

    def _header_soft_excluded(self, header: str) -> bool:
        lowered = str(header or "").strip().lower()
        if not lowered:
            return False
        patterns = [
            "динамик",
            "abc-анализ",
            "abc анализ",
            "доля ",
            "доля в ",
            "рекомендац",
            "сколько товаров",
            "среднее время доставки",
            "по сравнению с предыдущим периодом",
        ]
        return any(p in lowered for p in patterns)

    def _sample_quality_score(self, canonical, value) -> float:
        s = str(value or "").strip()
        if not s:
            return -1.0
        if self._looks_like_explainer_text(s):
            return -5.0

        canonical = str(canonical or "").strip()

        if canonical == "sku":
            if len(s) <= 40 and any(ch.isalpha() for ch in s):
                return 3.0
            if s.isdigit():
                return 0.5
            return 0.0

        if canonical in {"orders", "order_amount", "impressions_total", "impressions_search_catalog",
                         "product_card_visits", "add_to_cart_total", "stock_total",
                         "review_count", "rating_value"}:
            parsed = self._to_number(s)
            return 2.0 if parsed is not None else -2.0

        if canonical.endswith("_cvr") or canonical.endswith("_share") or canonical in {"discount_pct"}:
            parsed = self._to_number(s)
            return 2.0 if parsed is not None else -2.0

        return 1.0

    def _clean_preview_samples(self, header: str, canonical, values):
        result = []
        seen = set()
        values = values or []
        for raw in values:
            s = str(raw or "").strip()
            if not s:
                continue
            if self._looks_like_explainer_text(s):
                continue
            if s in seen:
                continue
            seen.add(s)
            result.append((self._sample_quality_score(canonical, s), s))

        if not result and values:
            for raw in values:
                s = str(raw or "").strip()
                if not s:
                    continue
                if s in seen:
                    continue
                seen.add(s)
                result.append((self._sample_quality_score(canonical, s), s))

        result.sort(key=lambda x: x[0], reverse=True)
        cleaned = [s for _, s in result[:3]]

        if self._header_soft_excluded(header):
            cleaned = cleaned[:1]

        return cleaned

    def _postprocess_field_mappings(self, field_mappings):
        items = []
        for item in list(field_mappings or []):
            row = dict(item)
            header = str(row.get("originalField") or "")
            canonical = row.get("standardField")
            row["sampleValues"] = self._clean_preview_samples(header, canonical, row.get("sampleValues") or [])

            lowered_header = header.lower()

            if self._header_soft_excluded(header):
                row["standardField"] = None
                row["confidence"] = 0.0
                row["mappingSource"] = "postprocess_unmapped"
                reasons = list(row.get("reasons") or [])
                reasons.append("soft_excluded_header")
                row["reasons"] = sorted(set(reasons))
                row["isManual"] = False

            items.append(row)

        # Prefer Артикул over SKU for business sku
        sku_candidates = [x for x in items if x.get("standardField") == "sku"]
        article_like = [
            x for x in sku_candidates
            if "артикул" in str(x.get("originalField") or "").lower()
        ]
        plain_sku = [
            x for x in sku_candidates
            if str(x.get("originalField") or "").strip().lower() == "sku"
        ]
        if article_like and plain_sku:
            article_best = sorted(article_like, key=lambda x: x.get("confidence", 0), reverse=True)[0]
            for loser in plain_sku:
                if loser is article_best:
                    continue
                loser["standardField"] = None
                loser["confidence"] = 0.0
                loser["mappingSource"] = "conflict_dropped"
                reasons = list(loser.get("reasons") or [])
                reasons.append("prefer_artikul_over_platform_sku")
                loser["reasons"] = sorted(set(reasons))

        protected = {
            "sku", "orders", "order_amount", "impressions_total", "impressions_search_catalog",
            "product_card_visits", "add_to_cart_total", "stock_total", "rating_value",
            "review_count", "price_index_status"
        }
        grouped = {}
        for row in items:
            target = row.get("standardField")
            if not target or target not in protected:
                continue
            grouped.setdefault(target, []).append(row)

        for target, group in grouped.items():
            if len(group) <= 1:
                continue
            group.sort(key=lambda x: x.get("confidence", 0), reverse=True)
            winner = group[0]
            for loser in group[1:]:
                loser["standardField"] = None
                loser["confidence"] = 0.0
                loser["mappingSource"] = "conflict_dropped"
                reasons = list(loser.get("reasons") or [])
                reasons.append(f"duplicate_target:{target}")
                loser["reasons"] = sorted(set(reasons))

        return items
"""

FRONTEND_HELPERS = """
const protectedTargets = new Set([
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

const detectProtectedConflicts = (mappings: FieldMapping[]) => {
  const grouped = new Map<string, FieldMapping[]>()
  for (const item of mappings) {
    if (!item.standardField || !protectedTargets.has(item.standardField)) continue
    if (!grouped.has(item.standardField)) grouped.set(item.standardField, [])
    grouped.get(item.standardField)!.push(item)
  }
  return [...grouped.entries()].filter(([, arr]) => arr.length > 1)
}
"""


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"[{label}] expected 1 match, got {count}")
    return text.replace(old, new, 1)


def patch_backend() -> None:
    text = IMPORT_SERVICE.read_text(encoding='utf-8')
    backup = IMPORT_SERVICE.with_suffix('.py.bak_mapping_accuracy_phase_b_v1')
    if not backup.exists():
        backup.write_text(text, encoding='utf-8')

    anchor = "\n    def confirm_import(\n"
    if BACKEND_HELPERS.strip() not in text:
        idx = text.find(anchor)
        if idx == -1:
            raise RuntimeError("confirm_import anchor not found in import_service.py")
        text = text[:idx] + "\n" + BACKEND_HELPERS + text[idx:]

    old = """        self.batches.append(
"""
    new = """        result["fieldMappings"] = self._postprocess_field_mappings(result.get("fieldMappings") or [])
        result["mappedCount"] = len([x for x in result["fieldMappings"] if x.get("standardField")])
        result["unmappedCount"] = len([x for x in result["fieldMappings"] if not x.get("standardField")])

        self.batches.append(
"""
    if new not in text:
        text = replace_once(text, old, new, "inject fieldMappings postprocess")

    IMPORT_SERVICE.write_text(text, encoding='utf-8')


def patch_frontend() -> None:
    text = FRONTEND_PAGE.read_text(encoding='utf-8')
    backup = FRONTEND_PAGE.with_suffix('.tsx.bak_mapping_accuracy_phase_b_v1')
    if not backup.exists():
        backup.write_text(text, encoding='utf-8')

    if FRONTEND_HELPERS.strip() not in text:
        anchor = "const buildDisplayStats = (result: ImportResult | null) => {"
        idx = text.find(anchor)
        if idx == -1:
            raise RuntimeError("buildDisplayStats anchor not found in DataImportV2.tsx")
        text = text[:idx] + FRONTEND_HELPERS + "\n" + text[idx:]

    old = """  const confirmImport = async () => {
    if (!importResult) return
"""
    new = """  const confirmImport = async () => {
    if (!importResult) return

    const conflicts = detectProtectedConflicts(importResult.fieldMappings || [])
    if (conflicts.length > 0) {
      message.error('存在一对多映射冲突，请先处理重复目标字段后再确认导入')
      return
    }
"""
    if new not in text:
        text = replace_once(text, old, new, "add protected conflict guard")

    FRONTEND_PAGE.write_text(text, encoding='utf-8')


def main() -> None:
    if not IMPORT_SERVICE.exists():
        raise FileNotFoundError(f"missing file: {IMPORT_SERVICE}")
    if not FRONTEND_PAGE.exists():
        raise FileNotFoundError(f"missing file: {FRONTEND_PAGE}")

    patch_backend()
    patch_frontend()

    print("Applied mapping accuracy phase B patch v1")
    print(f"Patched: {IMPORT_SERVICE}")
    print(f"Patched: {FRONTEND_PAGE}")


if __name__ == "__main__":
    main()
