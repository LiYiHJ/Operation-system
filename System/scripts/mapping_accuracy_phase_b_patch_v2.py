from pathlib import Path
import re
import shutil

REPO_ROOT = Path(r"C:\Operation-system\System")
TARGET = REPO_ROOT / r"src\ecom_v51\services\import_service.py"
BACKUP = TARGET.with_suffix(TARGET.suffix + ".phase_b_patch_v2.bak")


def replace_once(text: str, pattern: str, repl: str, label: str) -> str:
    new_text, count = re.subn(pattern, repl, text, count=1, flags=re.DOTALL)
    if count != 1:
        raise RuntimeError(f"{label} 替换失败，命中次数={count}")
    return new_text


def main() -> None:
    text = TARGET.read_text(encoding="utf-8")
    shutil.copyfile(TARGET, BACKUP)

    text = replace_once(
        text,
        r"SOFT_EXCLUDE_PATTERNS = \{.*?\n    \}\n    PROTECTED_UNIQUE_TARGETS = \{",
        '''SOFT_EXCLUDE_PATTERNS = {
        "динамик",
        "доля",
        "abc",
        "abc-анализ",
        "abc анализ",
        "рекомендац",
        "рекомендация",
        "recommend",
        "建议",
        "补货",
        "时效",
        "平均时效",
        "сколько товаров",
        "среднее время доставки",
        "среднее время",
        "по сравнению с предыдущим периодом",
    }
    PROTECTED_UNIQUE_TARGETS = {''',
        "soft exclude patterns",
    )

    text = replace_once(
        text,
        r"def _looks_like_explainer_text\(self, text: str\) -> bool:\n.*?\n\n    def _postprocess_field_mappings",
        '''def _looks_like_explainer_text(self, text: str) -> bool:
        raw = str(text or "").strip().lower()
        if not raw:
            return False

        token_count = len([tok for tok in re.split(r"[\s/|,;:()\[\]{}]+", raw) if tok])
        punctuation_count = sum(raw.count(ch) for ch in [",", ";", ":", "，", "；", "："])

        return (
            len(raw) >= 40
            or token_count >= 8
            or punctuation_count >= 3
            or "оцениваем" in raw
            or "считаем" in raw
            or "для этого" in raw
            or "динамика по сравнению" in raw
            or "товары a приносят" in raw
            or "建议" in raw
            or "补货" in raw
            or "平均时效" in raw
        )

    def _postprocess_field_mappings''',
        "looks like explainer text",
    )

    text = replace_once(
        text,
        r"dynamic_companion = self\._is_dynamic_companion\(original\)\n        soft_excluded = self\._is_soft_excluded_header\(original\)",
        '''dynamic_companion = self._is_dynamic_companion(original)
        soft_excluded = self._is_soft_excluded_header(original)
        explainer_like = self._looks_like_explainer_text(original)''',
        "map_single dynamic/excluded prelude",
    )

    text = replace_once(
        text,
        r"if soft_excluded:\n            return \{\n                \"originalField\": original,\n                \"normalizedField\": normalized,\n                \"standardField\": None,\n                \"mappingSource\": \"soft_excluded\",\n                \"confidence\": 0\.0,\n                \"sampleValues\": list\(sample_values or \[\]\),\n                \"isManual\": False,\n                \"reasons\": \[\"soft_excluded_header\"\],\n                \"conflicts\": conflicts,\n                \"dynamicCompanion\": False,\n                \"compressedHeader\": None,\n                \"excludeFromSemanticGate\": False,\n            \}",
        '''if soft_excluded or explainer_like:
            return {
                "originalField": original,
                "normalizedField": normalized,
                "standardField": None,
                "mappingSource": "soft_excluded",
                "confidence": 0.0,
                "sampleValues": list(sample_values or []),
                "isManual": False,
                "reasons": ["soft_excluded_header"] + (["explainer_header"] if explainer_like else []),
                "conflicts": conflicts,
                "dynamicCompanion": False,
                "compressedHeader": None,
                "excludeFromSemanticGate": False,
            }''',
        "map_single soft excluded return",
    )

    text = replace_once(
        text,
        r"cand_tokens = set\(\n                t for t in re\.split\(r\"\[\^a-zа-я0-9一-龥\]\+\", candidate_text\) if len\(t\) > 2\n            \)\n            best_overlap = \(None, 0\.0\)",
        '''cand_tokens = set(
                t for t in re.split(r"[^a-zа-я0-9一-龥]+", candidate_text) if len(t) > 2
            )
            if len(cand_tokens) < 2:
                return None, "unmapped", 0.0, local_reasons
            best_overlap = (None, 0.0)''',
        "token overlap guard",
    )

    TARGET.write_text(text, encoding="utf-8")
    print("已完成导入 Phase B 映射准确率小补丁 v2")
    print(f"备份: {BACKUP}")


if __name__ == "__main__":
    main()
