from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml  # type: ignore
except Exception:
    yaml = None  # type: ignore


class DatasetRegistryService:
    CONTRACT_VERSION = "p1.v1"

    def __init__(self, root_dir: Path) -> None:
        self._root_dir = root_dir
        self._registry_dir = self._root_dir / "config" / "dataset_registry"

    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        text = path.read_text(encoding="utf-8")
        if yaml is None:
            return {}
        data = yaml.safe_load(text)
        return data if isinstance(data, dict) else {}

    def _normalize_payload(self, payload: Dict[str, Any], *, fallback_stem: str) -> Dict[str, Any]:
        dataset_kind = str(payload.get("dataset_kind") or fallback_stem)
        import_profile = str(payload.get("import_profile") or dataset_kind)
        entity_key_field = str(payload.get("entity_key_field") or "sku")
        return {
            "datasetKind": dataset_kind,
            "importProfile": import_profile,
            "label": str(payload.get("label") or dataset_kind),
            "sourceType": payload.get("source_type") or "file",
            "platform": payload.get("platform") or "generic",
            "grain": payload.get("grain") or "",
            "requiredCoreFields": list(payload.get("required_core_fields") or []),
            "optionalCommonFields": list(payload.get("optional_common_fields") or []),
            "loaderTarget": payload.get("loader_target") or "",
            "gatePolicy": payload.get("gate_policy") or "core_safe",
            "schemaVersion": payload.get("schema_version") or "v1",
            "entityKeyField": entity_key_field,
        }

    def list_datasets(self) -> Dict[str, Any]:
        datasets: List[Dict[str, Any]] = []
        if not self._registry_dir.exists():
            return {"contractVersion": self.CONTRACT_VERSION, "datasets": datasets}

        for path in sorted(self._registry_dir.glob("*.yaml")):
            payload = self._load_yaml(path)
            if not payload:
                continue
            datasets.append(self._normalize_payload(payload, fallback_stem=path.stem))

        return {"contractVersion": self.CONTRACT_VERSION, "datasets": datasets}

    def get_dataset(self, dataset_kind: Optional[str] = None, import_profile: Optional[str] = None) -> Dict[str, Any]:
        registry = self.list_datasets()
        datasets = registry.get("datasets") or []
        dataset_kind = str(dataset_kind or "").strip()
        import_profile = str(import_profile or "").strip()

        for item in datasets:
            if dataset_kind and str(item.get("datasetKind") or "") == dataset_kind:
                return dict(item)
            if import_profile and str(item.get("importProfile") or "") == import_profile:
                return dict(item)

        if datasets:
            return dict(datasets[0])

        return {
            "datasetKind": dataset_kind or "orders",
            "importProfile": import_profile or dataset_kind or "orders",
            "label": dataset_kind or "orders",
            "sourceType": "file",
            "platform": "generic",
            "grain": "",
            "requiredCoreFields": ["sku"],
            "optionalCommonFields": [],
            "loaderTarget": "",
            "gatePolicy": "core_safe",
            "schemaVersion": "v1",
            "entityKeyField": "sku",
        }
