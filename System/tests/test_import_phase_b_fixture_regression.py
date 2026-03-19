from __future__ import annotations

import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ecom_v51.services.import_service import ImportService

warnings.filterwarnings(
    'ignore',
    message='Downcasting object dtype arrays on .fillna, .ffill, .bfill is deprecated',
    category=FutureWarning,
)


FIXTURES = {
    'ru_ozon': ROOT / 'data' / 'analytics_report_2026-03-12_23_49.xlsx',
    'cn_control': ROOT / 'data' / '销售数据分析.xlsx',
    'bad_header_missing_sku': ROOT / 'sample_data' / 'ozon_bad_header_or_missing_sku.xlsx',
}


def _parse_fixture(path: Path) -> dict:
    service = ImportService()
    return service.parse_import_file(str(path), shop_id=1, operator='pytest')


def _assert_top_level_mapping_contract(result: dict) -> None:
    assert 'mappedCount' in result
    assert 'unmappedCount' in result
    assert 'mappingCoverage' in result
    assert 'mappedConfidence' in result


def test_ru_ozon_fixture_keeps_phase_b_mapping_contract():
    result = _parse_fixture(FIXTURES['ru_ozon'])

    _assert_top_level_mapping_contract(result)
    top_unmapped_headers = result.get('topUnmappedHeaders') or []
    assert 'Динамика' not in top_unmapped_headers


def test_cn_control_fixture_keeps_phase_b_mapping_contract():
    result = _parse_fixture(FIXTURES['cn_control'])

    _assert_top_level_mapping_contract(result)


def test_bad_header_missing_sku_fixture_still_returns_mapping_contract():
    result = _parse_fixture(FIXTURES['bad_header_missing_sku'])

    _assert_top_level_mapping_contract(result)
