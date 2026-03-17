
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(r"C:\Operation-system\System")
IMPORT_SERVICE = REPO_ROOT / "src" / "ecom_v51" / "services" / "import_service.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"[{label}] expected 1 match, got {count}")
    return text.replace(old, new, 1)


def main() -> None:
    if not IMPORT_SERVICE.exists():
        raise FileNotFoundError(f"missing file: {IMPORT_SERVICE}")

    text = IMPORT_SERVICE.read_text(encoding="utf-8")
    backup = IMPORT_SERVICE.with_suffix(".py.bak_entity_key_suggestion_v2")
    if not backup.exists():
        backup.write_text(text, encoding="utf-8")

    # 1) extend helper signature
    old_sig = """    def _build_entity_key_suggestion(
        self,
        top_unmapped_headers: List[str],
        recovery_candidate_preview: List[dict],
        mapped_canonical_fields: List[str],
    ) -> Optional[dict]:
"""
    new_sig = """    def _build_entity_key_suggestion(
        self,
        top_unmapped_headers: List[str],
        recovery_candidate_preview: List[dict],
        mapped_canonical_fields: List[str],
        field_mappings: Optional[List[dict]] = None,
    ) -> Optional[dict]:
"""
    text = replace_once(text, old_sig, new_sig, "extend helper signature")

    # 2) add fieldMappings sampleValues into candidate pool
    old_pool = """        for candidate in recovery_candidate_preview or []:
            for example in candidate.get("flattenedHeaderExamples") or []:
                candidate_pool.append(("recoveryCandidatePreview", str(example)))

        best = None
"""
    new_pool = """        for candidate in recovery_candidate_preview or []:
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

        best = None
"""
    text = replace_once(text, old_pool, new_pool, "extend candidate pool")

    # 3) pass field mappings into helper call
    old_call = """        entity_key_suggestion = self._build_entity_key_suggestion(
            top_unmapped_headers=top_unmapped_headers,
            recovery_candidate_preview=recovery_candidate_preview,
            mapped_canonical_fields=mapped_canonical_fields,
        )
"""
    new_call = """        entity_key_suggestion = self._build_entity_key_suggestion(
            top_unmapped_headers=top_unmapped_headers,
            recovery_candidate_preview=recovery_candidate_preview,
            mapped_canonical_fields=mapped_canonical_fields,
            field_mappings=active_bundle.get("fieldMappings") or [],
        )
"""
    text = replace_once(text, old_call, new_call, "pass field mappings to helper")

    # 4) use precomputed variables and return entityKeySuggestion in upload result
    old_result_slice = """            "platform": active_bundle["platform"],
            "fieldMappings": active_bundle["fieldMappings"],
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
            "mappedCount": mapped_count,
"""
    new_result_slice = """            "platform": active_bundle["platform"],
            "fieldMappings": active_bundle["fieldMappings"],
            "mappedCanonicalFields": mapped_canonical_fields,
            "topUnmappedHeaders": top_unmapped_headers,
            "entityKeySuggestion": entity_key_suggestion,
            "mappedCount": mapped_count,
"""
    text = replace_once(text, old_result_slice, new_result_slice, "inject entityKeySuggestion into result")

    # 5) only replace the result-level recoveryCandidatePreview block, not the stats block
    old_result_preview = """            "recoveryDiff": recovery_diff,
            "recoveryCandidatePreview": list(
                recovery_result.get("candidatePreview") or []
            ),
            "status": status_map.get(active_bundle["finalStatus"], "partial"),
"""
    new_result_preview = """            "recoveryDiff": recovery_diff,
            "recoveryCandidatePreview": recovery_candidate_preview,
            "status": status_map.get(active_bundle["finalStatus"], "partial"),
"""
    text = replace_once(text, old_result_preview, new_result_preview, "reuse recovery preview in result")

    IMPORT_SERVICE.write_text(text, encoding="utf-8")
    print("Applied entity key suggestion patch v2")
    print(f"Patched: {IMPORT_SERVICE}")
    print(f"Backup:  {backup}")


if __name__ == "__main__":
    main()
