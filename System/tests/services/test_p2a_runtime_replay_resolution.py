from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ecom_v51.services.batch_runtime_service import BatchRuntimeService


class _Dummy:
    pass


def _build_service(tmp_path: Path) -> BatchRuntimeService:
    return BatchRuntimeService(
        root_dir=tmp_path,
        import_service=_Dummy(),
        workspace_service=_Dummy(),
        batch_service=_Dummy(),
    )


def test_get_source_path_prefers_source_object_file_path(tmp_path: Path):
    source = tmp_path / "sample.xlsx"
    source.write_text("ok", encoding="utf-8")
    svc = _build_service(tmp_path)
    detail = {
        "sourceObjects": [{"filePath": str(source)}],
        "rawRecords": [],
    }
    assert svc._get_source_path(detail) == source.resolve()


def test_get_source_path_falls_back_to_raw_record_source_path(tmp_path: Path):
    source = tmp_path / "sample2.xlsx"
    source.write_text("ok", encoding="utf-8")
    svc = _build_service(tmp_path)
    detail = {
        "sourceObjects": [],
        "rawRecords": [{"payload": {"sourcePath": str(source)}}],
    }
    assert svc._get_source_path(detail) == source.resolve()
