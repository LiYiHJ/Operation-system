from __future__ import annotations

from pathlib import Path
import shutil
import sys

TARGET = Path(r"C:\Operation-system\System\src\ecom_v51\services\import_service.py")
BACKUP_SUFFIX = ".bak_upload_transport_hotfix_v1"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"[{label}] target block not found")
    return text.replace(old, new, 1)


def main() -> None:
    if not TARGET.exists():
        raise FileNotFoundError(f"target file not found: {TARGET}")

    text = TARGET.read_text(encoding="utf-8")

    text = replace_once(
        text,
        "import copy\nimport itertools\nimport json\nimport re\n\nimport pandas as pd\n",
        "import copy\nimport itertools\nimport json\nimport re\nimport zipfile\nimport xml.etree.ElementTree as ET\n\nimport pandas as pd\n",
        "add zip/xml imports",
    )

    text = replace_once(
        text,
        '''    @staticmethod
    def _safe_scalar(value: Any) -> Any:
        if isinstance(value, (list, tuple)):
            return value[0] if value else None
        if hasattr(value, "tolist") and not isinstance(value, (str, bytes)):
            try:
                vals = value.tolist()
                if isinstance(vals, list):
                    return vals[0] if vals else None
            except Exception:
                pass
        return value
''',
        '''    @staticmethod
    def _safe_scalar(value: Any) -> Any:
        if isinstance(value, pd.DataFrame):
            if value.empty:
                return None
            return ImportService._safe_scalar(value.iat[0, 0])
        if isinstance(value, pd.Series):
            if value.empty:
                return None
            return ImportService._safe_scalar(value.iloc[0])
        if isinstance(value, (list, tuple)):
            return value[0] if value else None
        if hasattr(value, "tolist") and not isinstance(value, (str, bytes)):
            try:
                vals = value.tolist()
                if isinstance(vals, list):
                    if vals and isinstance(vals[0], list):
                        return vals[0][0] if vals[0] else None
                    return vals[0] if vals else None
            except Exception:
                pass
        return value

    @staticmethod
    def _excel_col_ref_to_index(cell_ref: str) -> int:
        letters = "".join(ch for ch in str(cell_ref or "") if ch.isalpha()).upper()
        idx = 0
        for ch in letters:
            idx = idx * 26 + (ord(ch) - 64)
        return idx

    def _read_xlsx_via_zip(self, file_path: str, header: Optional[int]) -> Tuple[Optional[pd.DataFrame], Optional[str], Dict[str, Any]]:
        meta = {
            "sheetNames": [],
            "selectedSheet": "",
            "readerEngineUsed": "xlsx_zip_fallback",
            "readerFallbackStage": "zip_xml_styles_bypass",
        }
        ns_main = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        rel_ns = "{http://schemas.openxmlformats.org/package/2006/relationships}"

        try:
            with zipfile.ZipFile(file_path) as zf:
                workbook_root = ET.fromstring(zf.read("xl/workbook.xml"))
                rel_root = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))

                rel_map: Dict[str, str] = {}
                for rel in rel_root.findall(f"{rel_ns}Relationship"):
                    rel_id = rel.attrib.get("Id")
                    target = rel.attrib.get("Target")
                    if rel_id and target:
                        rel_map[rel_id] = target

                sheet_entries: List[Tuple[str, str]] = []
                for sheet in workbook_root.findall("main:sheets/main:sheet", {
                    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
                    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
                }):
                    name = sheet.attrib.get("name") or "Sheet1"
                    rid = sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
                    target = rel_map.get(rid or "")
                    if not target:
                        continue
                    target_path = target.lstrip("/")
                    if not target_path.startswith("xl/"):
                        target_path = f"xl/{target_path}"
                    sheet_entries.append((name, target_path))

                if not sheet_entries:
                    return None, "读取文件失败：xlsx_zip_fallback 未找到工作表", meta

                meta["sheetNames"] = [name for name, _ in sheet_entries]
                meta["selectedSheet"] = sheet_entries[0][0]

                shared_strings: List[str] = []
                if "xl/sharedStrings.xml" in zf.namelist():
                    shared_root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
                    for si in shared_root.findall("main:si", ns_main):
                        text_parts = [node.text or "" for node in si.findall(".//main:t", ns_main)]
                        shared_strings.append("".join(text_parts))

                sheet_xml = zf.read(sheet_entries[0][1])
                sheet_root = ET.fromstring(sheet_xml)

                rows: List[Dict[int, Any]] = []
                max_col_idx = 0
                for row in sheet_root.findall(".//main:sheetData/main:row", ns_main):
                    row_map: Dict[int, Any] = {}
                    for cell in row.findall("main:c", ns_main):
                        ref = cell.attrib.get("r", "")
                        col_idx = self._excel_col_ref_to_index(ref)
                        if col_idx <= 0:
                            continue
                        cell_type = cell.attrib.get("t")
                        value_node = cell.find("main:v", ns_main)
                        inline_node = cell.find("main:is", ns_main)
                        value: Any = ""
                        if cell_type == "s":
                            if value_node is not None and value_node.text not in (None, ""):
                                try:
                                    s_idx = int(float(value_node.text))
                                    value = shared_strings[s_idx] if 0 <= s_idx < len(shared_strings) else value_node.text
                                except Exception:
                                    value = value_node.text
                        elif cell_type == "inlineStr":
                            value = "".join(node.text or "" for node in inline_node.findall(".//main:t", ns_main)) if inline_node is not None else ""
                        elif cell_type == "b":
                            value = value_node.text == "1" if value_node is not None else False
                        else:
                            value = value_node.text if value_node is not None else ""
                        row_map[col_idx] = value
                        max_col_idx = max(max_col_idx, col_idx)
                    rows.append(row_map)

                matrix = [[row_map.get(col_idx, "") for col_idx in range(1, max_col_idx + 1)] for row_map in rows]
                if not matrix:
                    return pd.DataFrame(), None, meta

                if header is None:
                    return pd.DataFrame(matrix), None, meta

                header_row = [str(v or "") for v in matrix[0]]
                body = matrix[1:] if len(matrix) > 1 else []
                return pd.DataFrame(body, columns=header_row), None, meta
        except Exception as exc:
            return None, f"读取文件失败：{exc}", meta

    def _preview_values_for_column(self, df: pd.DataFrame, col: Any, limit: int = 3) -> List[Any]:
        if col not in df.columns:
            return []
        selected = df.loc[:, col]
        values: List[Any] = []

        if isinstance(selected, pd.DataFrame):
            for row in selected.head(limit).itertuples(index=False, name=None):
                for item in row if isinstance(row, tuple) else (row,):
                    values.append(self._safe_scalar(item))
                    if len(values) >= limit:
                        return values[:limit]
            return values[:limit]

        try:
            raw_values = selected.head(limit).tolist()
        except Exception:
            raw_values = selected.head(limit).values.tolist() if hasattr(selected.head(limit), "values") else []
        for item in raw_values:
            if isinstance(item, list):
                for nested in item:
                    values.append(self._safe_scalar(nested))
                    if len(values) >= limit:
                        return values[:limit]
            else:
                values.append(self._safe_scalar(item))
                if len(values) >= limit:
                    return values[:limit]
        return values[:limit]

    @staticmethod
    def _collapse_duplicate_columns(df: pd.DataFrame) -> pd.DataFrame:
        if df is None or not df.columns.duplicated().any():
            return df
        collapsed = pd.DataFrame(index=df.index)
        seen: set[str] = set()
        for col in df.columns:
            col_name = str(col)
            if col_name in seen:
                continue
            selected = df.loc[:, col]
            if isinstance(selected, pd.DataFrame):
                collapsed[col_name] = selected.bfill(axis=1).iloc[:, 0]
            else:
                collapsed[col_name] = selected
            seen.add(col_name)
        return collapsed
''',
        "replace safe scalar and add helpers",
    )

    text = replace_once(
        text,
        '''    def _read_file_default(self, file_path: str) -> Tuple[Optional[pd.DataFrame], Optional[str], Dict[str, Any]]:
        path = Path(file_path)
        meta = {"sheetNames": ["CSV"], "selectedSheet": "CSV", "readerEngineUsed": None, "readerFallbackStage": "none"}
        if not path.exists():
            return None, f"文件不存在：{file_path}", meta
        try:
            if path.suffix.lower() in {".xlsx", ".xls"}:
                excel = pd.ExcelFile(file_path, engine="openpyxl" if path.suffix.lower() == ".xlsx" else None)
                meta["sheetNames"] = list(excel.sheet_names)
                meta["selectedSheet"] = meta["sheetNames"][0] if meta["sheetNames"] else "Sheet1"
                meta["readerEngineUsed"] = "openpyxl" if path.suffix.lower() == ".xlsx" else "xlrd"
                df = pd.read_excel(excel, sheet_name=meta["selectedSheet"])
                return df, None, meta
            if path.suffix.lower() == ".csv":
                for encoding in ["utf-8", "utf-8-sig", "gbk", "cp1251", "latin1"]:
                    try:
                        df = pd.read_csv(file_path, encoding=encoding)
                        meta["readerEngineUsed"] = f"csv:{encoding}"
                        return df, None, meta
                    except Exception:
                        continue
                return None, "无法识别文件编码", meta
            return None, f"不支持的文件格式：{path.suffix}", meta
        except Exception as exc:
            return None, f"读取文件失败：{exc}", meta
''',
        '''    def _read_file_default(self, file_path: str) -> Tuple[Optional[pd.DataFrame], Optional[str], Dict[str, Any]]:
        path = Path(file_path)
        meta = {"sheetNames": ["CSV"], "selectedSheet": "CSV", "readerEngineUsed": None, "readerFallbackStage": "none"}
        if not path.exists():
            return None, f"文件不存在：{file_path}", meta
        try:
            if path.suffix.lower() in {".xlsx", ".xls"}:
                excel = pd.ExcelFile(file_path, engine="openpyxl" if path.suffix.lower() == ".xlsx" else None)
                meta["sheetNames"] = list(excel.sheet_names)
                meta["selectedSheet"] = meta["sheetNames"][0] if meta["sheetNames"] else "Sheet1"
                meta["readerEngineUsed"] = "openpyxl" if path.suffix.lower() == ".xlsx" else "xlrd"
                df = pd.read_excel(excel, sheet_name=meta["selectedSheet"])
                return df, None, meta
            if path.suffix.lower() == ".csv":
                for encoding in ["utf-8", "utf-8-sig", "gbk", "cp1251", "latin1"]:
                    try:
                        df = pd.read_csv(file_path, encoding=encoding)
                        meta["readerEngineUsed"] = f"csv:{encoding}"
                        return df, None, meta
                    except Exception:
                        continue
                return None, "无法识别文件编码", meta
            return None, f"不支持的文件格式：{path.suffix}", meta
        except Exception as exc:
            if path.suffix.lower() == ".xlsx":
                fallback_df, fallback_error, fallback_meta = self._read_xlsx_via_zip(file_path, header=0)
                if fallback_df is not None and fallback_error is None:
                    fallback_meta["readerPrimaryError"] = str(exc)
                    return fallback_df, None, fallback_meta
            return None, f"读取文件失败：{exc}", meta
''',
        "patch read default",
    )

    text = replace_once(
        text,
        '''    def _read_file_raw(self, file_path: str) -> Tuple[Optional[pd.DataFrame], Optional[str], Dict[str, Any]]:
        path = Path(file_path)
        meta = {"sheetNames": ["CSV"], "selectedSheet": "CSV", "readerEngineUsed": None, "readerFallbackStage": "raw_header_scan"}
        try:
            if path.suffix.lower() in {".xlsx", ".xls"}:
                excel = pd.ExcelFile(file_path, engine="openpyxl" if path.suffix.lower() == ".xlsx" else None)
                meta["sheetNames"] = list(excel.sheet_names)
                meta["selectedSheet"] = meta["sheetNames"][0] if meta["sheetNames"] else "Sheet1"
                meta["readerEngineUsed"] = "openpyxl" if path.suffix.lower() == ".xlsx" else "xlrd"
                df = pd.read_excel(excel, sheet_name=meta["selectedSheet"], header=None)
                return df, None, meta
            if path.suffix.lower() == ".csv":
                for encoding in ["utf-8", "utf-8-sig", "gbk", "cp1251", "latin1"]:
                    try:
                        df = pd.read_csv(file_path, encoding=encoding, header=None)
                        meta["readerEngineUsed"] = f"csv:{encoding}"
                        return df, None, meta
                    except Exception:
                        continue
                return None, "无法识别文件编码", meta
            return None, f"不支持的文件格式：{path.suffix}", meta
        except Exception as exc:
            return None, f"读取文件失败：{exc}", meta
''',
        '''    def _read_file_raw(self, file_path: str) -> Tuple[Optional[pd.DataFrame], Optional[str], Dict[str, Any]]:
        path = Path(file_path)
        meta = {"sheetNames": ["CSV"], "selectedSheet": "CSV", "readerEngineUsed": None, "readerFallbackStage": "raw_header_scan"}
        try:
            if path.suffix.lower() in {".xlsx", ".xls"}:
                excel = pd.ExcelFile(file_path, engine="openpyxl" if path.suffix.lower() == ".xlsx" else None)
                meta["sheetNames"] = list(excel.sheet_names)
                meta["selectedSheet"] = meta["sheetNames"][0] if meta["sheetNames"] else "Sheet1"
                meta["readerEngineUsed"] = "openpyxl" if path.suffix.lower() == ".xlsx" else "xlrd"
                df = pd.read_excel(excel, sheet_name=meta["selectedSheet"], header=None)
                return df, None, meta
            if path.suffix.lower() == ".csv":
                for encoding in ["utf-8", "utf-8-sig", "gbk", "cp1251", "latin1"]:
                    try:
                        df = pd.read_csv(file_path, encoding=encoding, header=None)
                        meta["readerEngineUsed"] = f"csv:{encoding}"
                        return df, None, meta
                    except Exception:
                        continue
                return None, "无法识别文件编码", meta
            return None, f"不支持的文件格式：{path.suffix}", meta
        except Exception as exc:
            if path.suffix.lower() == ".xlsx":
                fallback_df, fallback_error, fallback_meta = self._read_xlsx_via_zip(file_path, header=None)
                if fallback_df is not None and fallback_error is None:
                    fallback_meta["readerPrimaryError"] = str(exc)
                    return fallback_df, None, fallback_meta
            return None, f"读取文件失败：{exc}", meta
''',
        "patch read raw",
    )

    text = replace_once(
        text,
        '''    def map_columns(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[dict]]:
        rename_map: Dict[str, str] = {}
        field_mappings: List[dict] = []

        for col in df.columns:
            sample_values = [self._safe_scalar(v) for v in df[col].head(3).tolist()] if col in df.columns else []
            details = self._map_single_column_details(col, sample_values=sample_values)
            field_mappings.append(details)
            canonical = details.get("standardField")
            if canonical:
                rename_map[str(col)] = canonical

        mapped_df = df.rename(columns=rename_map)
        return mapped_df, field_mappings
''',
        '''    def map_columns(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[dict]]:
        rename_map: Dict[str, str] = {}
        field_mappings: List[dict] = []

        for col in df.columns:
            sample_values = self._preview_values_for_column(df, col, limit=3)
            details = self._map_single_column_details(col, sample_values=sample_values)
            field_mappings.append(details)
            canonical = details.get("standardField")
            if canonical:
                rename_map[str(col)] = canonical

        mapped_df = df.rename(columns=rename_map)
        mapped_df = self._collapse_duplicate_columns(mapped_df)
        return mapped_df, field_mappings
''',
        "patch sample value extraction",
    )

    backup = TARGET.with_name(TARGET.name + BACKUP_SUFFIX)
    shutil.copy2(TARGET, backup)
    TARGET.write_text(text, encoding="utf-8", newline="\n")
    print(f"patched: {TARGET}")
    print(f"backup:  {backup}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
