# P0-1 真实报表 confirm_import 失败根因分析与修复报告

## 1) 问题复现（修复前）
复现对象：
- demo：`sample_data/p4_demo_import.csv`
- real A：`src/uploads/20260308_142700_analytics_report_2026-03-06_03_58.xlsx`
- real B：`sample_data/ozon_bad_header_or_missing_sku.xlsx`

修复前结果（见 `p0_confirm_failure_analysis_before.json`）：
- demo：`confirm=success`, `errorRows=0`
- real A：`confirm=failed`, `importedRows=0`, `errorRows=1505`
- real B：`confirm=failed`, `importedRows=0`, `errorRows=1505`

## 2) 根因定位（分层）
### 失败层级判断
- 清洗/标准化：**部分通过**（parse 与映射统计正常）
- 字段映射：**部分通过**（能映射但存在值形态复杂）
- canonical -> fact 写入：**失败主因**
- 扩展事实表写入：受上游失败连带失败

### 具体触发值与失败分组
高频错误：
- `invalid literal for int() with base 10: '90 из 90'`
- `invalid literal for int() with base 10: '36 из 90'`
- `invalid literal for int() with base 10: '88 из 90'`

说明：报表中存在“带文字的数值”（如“90 из 90”），在 `_upsert_daily_facts` 中直接 `int(...)` 转换导致入库异常。

## 3) 最小必要修复
文件：`src/ecom_v51/services/import_service.py`

改动点：
1. 新增 `_to_int/_to_float` 容错转换函数：
   - 先走现有 `clean_numeric`
   - 失败时提取首个数字片段（兼容“90 из 90”）
   - 最终回退默认值
2. 将 `_upsert_daily_facts` 中直接 `int()/float()` 的关键转换替换为容错转换。

## 4) 修复后回归结果
见 `p0_confirm_failure_analysis_after.json`：
- demo：`confirm=success`, `errorRows=0`
- real A：`confirm=success`, `importedRows=1505`, `errorRows=0`
- real B：`confirm=success`, `importedRows=1505`, `errorRows=0`

事实表计数（修复后同一回归库）：
- fact_sku_daily: 1511
- fact_orders_daily: 1511
- fact_reviews_daily: 1511
- fact_ads_daily: 1511
- fact_inventory_daily: 1511
- fact_profit_snapshot: 1511
- fact_sku_ext_daily: 1511

## 5) 修复前后对比
| 样本 | 修复前 confirm | 修复前 errorRows | 修复后 confirm | 修复后 errorRows |
|---|---|---:|---|---:|
| demo | success | 0 | success | 0 |
| real A | failed | 1505 | success | 0 |
| real B | failed | 1505 | success | 0 |

## 6) 结论
P0-1 已达成：
- demo / real A / real B 均 `confirm_import success`
- `errorRows = 0`
- 消除“UI 映射成功但 confirm 落库失败”假成功风险（针对该类值形态）
