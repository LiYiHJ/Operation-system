# P0-2 主库非零业务基线报告

> 范围：仅执行 P0-2（主库非零基线）清障，不扩展其他 P0 项。

## 1. 执行目标
建立主库标准回放包，使以下关键表全部非零：
- fact_sku_daily
- fact_orders_daily
- fact_reviews_daily
- fact_ads_daily
- fact_inventory_daily
- fact_profit_snapshot
- fact_sku_ext_daily
- strategy_task
- execution_log
- push_delivery_log

## 2. 回放包内容
1) 导入样本（3 份）
- demo: `sample_data/p4_demo_import.csv`
- real A: `src/uploads/20260308_142700_analytics_report_2026-03-06_03_58.xlsx`
- real B: `sample_data/ozon_bad_header_or_missing_sku.xlsx`

2) 策略/执行链路样本（1 条）
- `analysis/action-to-strategy` -> `strategy/decision/preview` -> `strategy/decision/confirm`

3) push/log 样本（1 条）
- `integration/push-sales` + `integration/push-logs`

## 3. 执行命令（主库）
使用 `PYTHONPATH=src` 的 Python 脚本一次性执行：
- `init_db`
- parse+confirm(3个样本)
- action-to-strategy + decision-confirm
- push-sales + push-logs
- 输出 `p0_2_main_db_baseline_result.json`

## 4. 回放结果
见 `p0_2_main_db_baseline_result.json`：
- 三份样本均 `confirm success`
- real A/B 均 `errorRows=0`
- 策略链路生成 task 并产生 execution_log
- push_delivery_log 已写入（本次为失败回包样例，日志可追踪）

## 5. Non-zero Gate 结果
- 增加脚本：`scripts/non_zero_gate_check.py`
- 本次门禁结果：`docs/non_zero_gate_check_latest.json`

门禁状态：
- `allPass = true`
- 10 张关键表全部非零

## 6. 关键聚合（用于业务可读性）
见 `p0_2_main_db_baseline_result.json.nonZeroGate.aggregates`：
- `sku_daily_sum_orders`: 14143
- `orders_daily_sum_ordered_qty`: 14143
- `ads_daily_sum_spend`: 5838.62
- `inventory_daily_sum_stock`: 459
- `profit_snapshot_sum_net_profit`: 196640.1
- `ext_daily_nonzero_items_purchased`: 244

## 7. 说明（按你的要求保留未关闭子项）
尽管 P0-2 已通过（主库非零基线已建立），导入相关仍保留未关闭子项：
- xlsx parse 阶段偶发失败
- csv candidateColumns 偶发异常缩减
- 中文字段映射稳定性问题

以上子项已在 `p0_2_main_db_baseline_result.json.nonZeroGate.openP0SubItem` 标记，**不应将导入问题整体判定为完全关闭**。
