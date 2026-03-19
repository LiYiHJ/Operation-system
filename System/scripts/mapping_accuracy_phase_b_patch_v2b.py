from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TARGET = REPO_ROOT / "src" / "ecom_v51" / "services" / "import_service.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label} 替换失败，命中次数={count}")
    return text.replace(old, new, 1)


def main() -> None:
    text = TARGET.read_text(encoding="utf-8")

    old_soft_exclude = '''    SOFT_EXCLUDE_PATTERNS = {
        "динамик",
        "доля",
        "abc-анализ",
        "abc анализ",
        "рекомендац",
        "сколько товаров",
        "среднее время доставки",
        "по сравнению с предыдущим периодом",
    }
'''
    new_soft_exclude = '''    SOFT_EXCLUDE_PATTERNS = {
        "динамик",
        "доля",
        "abc-анализ",
        "abc анализ",
        "abc",
        "рекомендац",
        "recommend",
        "建议",
        "补货",
        "时效",
        "平均时效",
        "среднее время",
        "среднее время доставки",
        "сколько товаров",
        "по сравнению с предыдущим периодом",
    }
'''
    text = replace_once(text, old_soft_exclude, new_soft_exclude, "SOFT_EXCLUDE_PATTERNS")

    old_explainer = '''    def _looks_like_explainer_text(self, text: str) -> bool:
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
'''
    new_explainer = '''    def _looks_like_explainer_text(self, text: str) -> bool:
        raw = str(text or "").strip().lower()
        if not raw:
            return False

        compact = " ".join(raw.split())
        token_count = len([tok for tok in re.split(r"[^a-zа-я0-9一-龥]+", compact) if tok])
        punctuation_count = sum(compact.count(ch) for ch in [",", ";", ":", "，", "；", "："])

        return (
            len(compact) >= 40
            or token_count >= 8
            or punctuation_count >= 2
            or "оцениваем" in compact
            or "считаем" in compact
            or "для этого" in compact
            or "по сравнению" in compact
            or "динамика по сравнению" in compact
            or "товары a приносят" in compact
            or "recommend" in compact
            or "рекомендац" in compact
            or "建议" in compact
            or "平均时效" in compact
            or "среднее время" in compact
        )
'''
    text = replace_once(text, old_explainer, new_explainer, "_looks_like_explainer_text")

    old_soft_assign = '''        dynamic_companion = self._is_dynamic_companion(original)
        soft_excluded = self._is_soft_excluded_header(original)
        reasons: List[str] = []
'''
    new_soft_assign = '''        dynamic_companion = self._is_dynamic_companion(original)
        soft_excluded = self._is_soft_excluded_header(original)
        explainer_like_header = self._looks_like_explainer_text(original)
        soft_excluded = soft_excluded or explainer_like_header
        reasons: List[str] = []
'''
    text = replace_once(text, old_soft_assign, new_soft_assign, "map_single_column soft_excluded prelude")

    old_overlap = '''            # token overlap fallback for long phrases
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
'''
    new_overlap = '''            # token overlap fallback for long phrases
            cand_tokens = {
                t
                for t in re.split(r"[^a-zа-я0-9一-龥]+", candidate_text)
                if len(t) > 2 and t not in self.GENERIC_HEADER_PIECES
            }
            if len(cand_tokens) >= 2:
                best_overlap = (None, 0.0)
                for alias_norm, canonical in self._alias_lookup.items():
                    alias_tokens = {
                        t
                        for t in re.split(r"[^a-zа-я0-9一-龥]+", alias_norm)
                        if len(t) > 2 and t not in self.GENERIC_HEADER_PIECES
                    }
                    if len(alias_tokens) < 2:
                        continue
                    overlap = len(cand_tokens & alias_tokens) / max(len(alias_tokens), 1)
                    if overlap > best_overlap[1]:
                        best_overlap = (canonical, overlap)
                if best_overlap[0] and best_overlap[1] >= 0.75:
                    local_reasons.append(f"token_overlap:{best_overlap[1]:.2f}")
                    return (
                        best_overlap[0],
                        "token_overlap",
                        round(0.52 + best_overlap[1] * 0.22, 3),
                        local_reasons,
                    )
'''
    text = replace_once(text, old_overlap, new_overlap, "token_overlap fallback")

    TARGET.write_text(text, encoding="utf-8")
    print("已完成导入 Phase B 小补丁 v2b")
    print("修改: src/ecom_v51/services/import_service.py")
    print("内容: soft exclude 扩展 / explainer header 收紧 / token overlap 收紧")


if __name__ == "__main__":
    main()
