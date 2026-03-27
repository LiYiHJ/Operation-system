from pathlib import Path

from ecom_v51.api.routes.import_route import _build_safe_upload_filename


def test_build_safe_upload_filename_preserves_xlsx_suffix_for_cn_name():
    name = _build_safe_upload_filename('销售数据分析.xlsx')
    assert name.endswith('.xlsx')
    assert len(name) > len('.xlsx')


def test_build_safe_upload_filename_falls_back_when_name_is_empty():
    name = _build_safe_upload_filename('')
    assert name.startswith('upload-')
