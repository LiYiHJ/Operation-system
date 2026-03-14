# 111.patch 清洗与变更清单


## 结论

- 原始 `111.patch` 第 30365 行开始包含一段 shell 包装与整套 diff 的重复内容。
- 可直接使用的补丁文件已另存为 `111_clean.patch`。
- 清洗后唯一变更文件数：**95**。

## 分类统计

| 类别 | 数量 |
|---|---:|
| config | 2 |
| data | 1 |
| docs | 67 |
| frontend | 11 |
| sample_data | 1 |
| scripts | 1 |
| backend_src | 12 |

## 建议不要提交

- `System/data/ecom_v51.db`
- 任何 `System/src/uploads/*` 运行产物

## 代码/配置/样本层面变更文件

### config

- `System/config/field_aliases_zh_ru_en.yaml`  _( +630 / -38 )_
- `System/config/import_field_registry.json`  _( +876 / -0 )_

### backend_src

- `System/src/ecom_v51/api/app.py`  _( +2 / -0 )_
- `System/src/ecom_v51/api/routes/ads.py`  _( +33 / -0 )_
- `System/src/ecom_v51/api/routes/analysis.py`  _( +12 / -0 )_
- `System/src/ecom_v51/api/routes/dashboard.py`  _( +67 / -0 )_
- `System/src/ecom_v51/api/routes/import_route.py`  _( +50 / -2 )_
- `System/src/ecom_v51/api/routes/strategy.py`  _( +77 / -0 )_
- `System/src/ecom_v51/db/models.py`  _( +33 / -0 )_
- `System/src/ecom_v51/intelligent_field_mapper.py`  _( +38 / -4 )_
- `System/src/ecom_v51/services/analysis_service.py`  _( +58 / -10 )_
- `System/src/ecom_v51/services/import_service.py`  _( +1398 / -142 )_
- `System/src/ecom_v51/services/integration_service.py`  _( +31 / -3 )_
- `System/src/ecom_v51/services/strategy_service.py`  _( +97 / -46 )_

### frontend

- `System/frontend/README_FRONTEND.md`  _( +1 / -1 )_
- `System/frontend/src/App.tsx`  _( +1 / -1 )_
- `System/frontend/src/pages/DataImport.tsx`  _( +3 / -3 )_
- `System/frontend/src/pages/DataImport/index.tsx`  _( +3 / -3 )_
- `System/frontend/src/pages/DataImportV2.tsx`  _( +258 / -29 )_
- `System/frontend/src/pages/DecisionEngine.tsx`  _( +27 / -4 )_
- `System/frontend/src/pages/PriceCompetitiveness.tsx`  _( +5 / -1 )_
- `System/frontend/src/pages/StrategyList.tsx`  _( +21 / -2 )_
- `System/frontend/src/pages/SystemSettings.tsx`  _( +12 / -12 )_
- `System/frontend/src/services/api.ts`  _( +17 / -2 )_
- `System/frontend/src/types/index.ts`  _( +130 / -0 )_

### scripts

- `System/scripts/non_zero_gate_check.py`  _( +29 / -0 )_

### sample_data

- `System/sample_data/p0_csv_scene_from_cn.csv`  _( +45 / -0 )_

### data

- `System/data/ecom_v51.db`  _( +0 / -0 )_

## 变更量最大的文件（前 25）

| 文件 | + | - | 总计 |
|---|---:|---:|---:|
| `System/docs/p0_parse_mapping_fix_result.json` | 4205 | 0 | 4205 |
| `System/docs/price_cockpit_api_sample.json` | 3655 | 0 | 3655 |
| `System/docs/p0_import_reader_chain_regression.json` | 1727 | 0 | 1727 |
| `System/src/ecom_v51/services/import_service.py` | 1398 | 142 | 1540 |
| `System/docs/p0_import_reopen_repro_fix.json` | 1188 | 0 | 1188 |
| `System/config/import_field_registry.json` | 876 | 0 | 876 |
| `System/config/field_aliases_zh_ru_en.yaml` | 630 | 38 | 668 |
| `System/docs/strategy_execution_api_samples.json` | 666 | 0 | 666 |
| `System/docs/p0_ru_upload_path_conflict_comparison.json` | 658 | 0 | 658 |
| `System/docs/p0_xlsx_multi_sample_stability_validation.json` | 572 | 0 | 572 |
| `System/docs/p0_bad_header_recovery_runtime_validation.json` | 506 | 0 | 506 |
| `System/frontend/src/pages/DataImportV2.tsx` | 258 | 29 | 287 |
| `System/docs/final_readiness_live_checks.json` | 286 | 0 | 286 |
| `System/docs/p0_2_main_db_baseline_result.json` | 282 | 0 | 282 |
| `System/docs/p0_ru_semantic_mapping_correction.json` | 280 | 0 | 280 |
| `System/docs/strategy_execution_db_samples.json` | 263 | 0 | 263 |
| `System/docs/final_production_readiness_report.md` | 262 | 0 | 262 |
| `System/docs/strategy_ui_closure_api_samples.json` | 242 | 0 | 242 |
| `System/docs/p0_phase1_phase2_business_closure.json` | 228 | 0 | 228 |
| `System/docs/p0_confirm_failure_analysis_before.json` | 206 | 0 | 206 |
| `System/docs/p0_confirm_failure_analysis_after.json` | 149 | 0 | 149 |
| `System/docs/final_readiness_import_checks.json` | 147 | 0 | 147 |
| `System/src/ecom_v51/services/strategy_service.py` | 97 | 46 | 143 |
| `System/docs/import_p0_fix_report.md` | 137 | 0 | 137 |
| `System/docs/p0_cn_real_item1_row_level_diff.json` | 136 | 0 | 136 |