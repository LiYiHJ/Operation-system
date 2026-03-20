from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

try:
    import yaml  # type: ignore
except Exception:
    yaml = None  # type: ignore


class DatasetRegistryService:
    CONTRACT_VERSION = "p0.v1"

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

    def list_datasets(self) -> Dict[str, Any]:
        datasets: List[Dict[str, Any]] = []
        if not self._registry_dir.exists():
            return {"contractVersion": self.CONTRACT_VERSION, "datasets": datasets}

        for path in sorted(self._registry_dir.glob("*.yaml")):
            payload = self._load_yaml(path)
            if not payload:
                continue
            datasets.append(
                {
                    "datasetKind": payload.get("dataset_kind") or path.stem,
                    "sourceType": payload.get("source_type") or "file",
                    "platform": payload.get("platform") or "generic",
                    "grain": payload.get("grain") or "",
                    "requiredCoreFields": list(payload.get("required_core_fields") or []),
                    "optionalCommonFields": list(
                        payload.get("optional_common_fields") or []
                    ),
                    "loaderTarget": payload.get("loader_target") or "",
                    "gatePolicy": payload.get("gate_policy") or "core_safe",
                    "schemaVersion": payload.get("schema_version") or "v1",
                }
            )
        return {"contractVersion": self.CONTRACT_VERSION, "datasets": datasets}
