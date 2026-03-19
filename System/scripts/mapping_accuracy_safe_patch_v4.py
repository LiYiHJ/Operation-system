#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
import re
import shutil
import sys

ROOT = Path.cwd()
TARGET = ROOT / 'src' / 'ecom_v51' / 'services' / 'import_service.py'
BACKUP = ROOT / 'scripts' / 'mapping_accuracy_safe_patch_v4.import_service.backup.py'


def replace_once(text: str, pattern: str, repl: str, label: str) -> str:
    new_text, count = re.subn(pattern, repl, text, count=1, flags=re.DOTALL)
    if count != 1:
        raise RuntimeError(f'{label} 替换失败，命中次数={count}')
    return new_text


def main() -> None:
    if not TARGET.exists():
        raise FileNotFoundError(f'未找到文件: {TARGET}')

    text = TARGET.read_text(encoding='utf-8')
    shutil.copyfile(TARGET, BACKUP)

    # 1) 修正 explanatory text 里的逗号计数行，避免乱码/引号问题。
    text = replace_once(
        text,
        r'\n\s*comma_count\s*=\s*.*?\n\s*if comma_count >= 2:\n',
        '\n        comma_count = text.count(",") + text.count(";") + text.count("，") + text.count("；")\n        if comma_count >= 2:\n',
        'comma_count 行',
    )

    # 2) 修正 _build_entity_key_suggestion，恢复原调用契约，同时保留更保守的候选筛选。
    new_entity_key_func = '''    def _build_entity_key_suggestion(
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
            if item:
                candidate_pool.append(("topUnmappedHeaders", None, str(item)))

        for candidate in recovery_candidate_preview or []:
            for example in candidate.get("flattenedHeaderExamples") or []:
                if example:
                    candidate_pool.append(("recoveryCandidatePreview", None, str(example)))

        for item in field_mappings or []:
            if item.get("standardField") == "sku":
                return None
            if item.get("dynamicCompanion"):
                continue

            original_field = str(item.get("originalField") or "")
            if original_field:
                candidate_pool.append(
                    ("fieldMappings.originalField", original_field, original_field)
                )
            for value in self._sanitize_sample_values(item.get("sampleValues") or [], limit=3):
                candidate_pool.append(
                    ("fieldMappings.sampleValues", original_field or None, str(value))
                )

        if df is not None:
            for column_name, value in self._collect_entity_key_probe_values(
                df, field_mappings or []
            ):
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

            score = round(max(score, 0.0), 4)
            if score > best_score:
                best_score = score
                best_item = {
                    "field": "sku",
                    "confidence": score,
                    "sourceHeader": source,
                    "sourceColumn": column_name,
                    "sampleToken": token,
                    "detectedBy": "value_pattern" if token else "header_hint",
                    "rawCandidate": raw,
                }

        if best_item is None or best_score < self.ENTITY_KEY_MIN_CONFIDENCE:
            return None

        return best_item
'''

    text = replace_once(
        text,
        r'\n\s*def _build_entity_key_suggestion\(.*?\n\s*def _read_file_default\(',
        '\n' + new_entity_key_func + '\n    def _read_file_default(',
        '_build_entity_key_suggestion 函数',
    )

    # 3) 修正 parse_import_file 中 field_mappings 未定义 + 时机错误的问题。
    old_block_pattern = r'''\n\s*mapped_canonical_fields = list\(.*?\n\s*entity_key_suggestion = self\._build_entity_key_suggestion\(\n\s*top_unmapped_headers=top_unmapped_headers,\n\s*recovery_candidate_preview=recovery_candidate_preview,\n\s*mapped_canonical_fields=mapped_canonical_fields,\n\s*field_mappings=active_bundle\.get\("fieldMappings"\) or \[\],\n\s*df=active_bundle\["df"\],\n\s*\)\n'''

    new_block = '''
        active_bundle["fieldMappings"] = self._sanitize_and_reconcile_field_mappings(
            active_bundle.get("fieldMappings") or []
        )

        mapped_canonical_fields = list(
            dict.fromkeys(
                [
                    str(item.get("standardField"))
                    for item in (active_bundle.get("fieldMappings") or [])
                    if item.get("standardField")
                ]
            )
        )[:20]

        top_unmapped_headers = [
            str(item.get("originalField"))
            for item in (active_bundle.get("fieldMappings") or [])
            if not item.get("standardField") and not item.get("dynamicCompanion")
        ][:20]

        recovery_candidate_preview = list(recovery_result.get("candidatePreview") or [])

        entity_key_suggestion = self._build_entity_key_suggestion(
            top_unmapped_headers=top_unmapped_headers,
            recovery_candidate_preview=recovery_candidate_preview,
            mapped_canonical_fields=mapped_canonical_fields,
            field_mappings=active_bundle.get("fieldMappings") or [],
            df=active_bundle["df"],
        )
'''

    text = replace_once(text, old_block_pattern, '\n' + new_block, 'parse_import_file 建议块')

    TARGET.write_text(text, encoding='utf-8')
    print('OK: patched', TARGET)
    print('BACKUP:', BACKUP)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        sys.exit(1)
