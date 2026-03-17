
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
    backup = IMPORT_SERVICE.with_suffix(".py.bak_entity_key_suggestion_v1")
    if not backup.exists():
        backup.write_text(text, encoding="utf-8")

    old_signature = """    def _build_entity_key_suggestion(
        self,
        top_unmapped_headers: List[str],
        recovery_candidate_preview: List[dict],
        mapped_canonical_fields: List[str],
    ) -> Optional[dict]:
"""
    new_signature = """    def _build_entity_key_suggestion(
        self,
        top_unmapped_headers: List[str],
        recovery_candidate_preview: List[dict],
        mapped_canonical_fields: List[str],
        field_mappings: Optional[List[dict]] = None,
    ) -> Optional[dict]:
"""
    text = replace_once(text, old_signature, new_signature, "entity suggestion signature")

    old_pool = """        for item in top_unmapped_headers or []:
            candidate_pool.append(("topUnmappedHeaders", str(item)))

        for candidate in recovery_candidate_preview or []:
            for example in candidate.get("flattenedHeaderExamples") or []:
                candidate_pool.append(("recoveryCandidatePreview", str(example)))

        best = None
"""
    new_pool = """        for item in top_unmapped_headers or []:
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

        best = None
"""
    text = replace_once(text, old_pool, new_pool, "entity suggestion candidate pool")

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
    text = replace_once(text, old_call, new_call, "entity suggestion call")

    old_result_block = """            "fieldMappings": active_bundle["fieldMappings"],
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
    new_result_block = """            "fieldMappings": active_bundle["fieldMappings"],
            "mappedCanonicalFields": mapped_canonical_fields,
            "topUnmappedHeaders": top_unmapped_headers,
            "entityKeySuggestion": entity_key_suggestion,
"""
    text = replace_once(text, old_result_block, new_result_block, "upload result suggestion block")

    old_recovery_preview = """            "recoveryCandidatePreview": list(
                recovery_result.get("candidatePreview") or []
            ),
"""
    new_recovery_preview = """            "recoveryCandidatePreview": recovery_candidate_preview,
"""
    text = replace_once(text, old_recovery_preview, new_recovery_preview, "reuse recovery candidate preview")

    IMPORT_SERVICE.write_text(text, encoding="utf-8")
    print("Applied entity key suggestion patch v1")
    print(f"Patched: {IMPORT_SERVICE}")
    print(f"Backup:  {backup}")


if __name__ == "__main__":
    main()
