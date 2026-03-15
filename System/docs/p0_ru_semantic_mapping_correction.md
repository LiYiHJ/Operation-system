# P0 子项：俄语真实报表语义映射纠偏

## 范围
仅处理俄语语义映射纠偏，不扩展其他模块。

## 1) 俄语 Golden Mapping 清单
见 `docs/p0_ru_semantic_mapping_correction.json` 的 `goldenMapping`：
- Заказано на сумму -> `order_amount` -> `fact_orders_daily.ordered_amount`
- Доля в общей сумме заказов -> `order_amount_share` -> `fact_sku_daily.order_amount_share`
- Доставлено товаров -> `items_delivered` -> `fact_orders_daily.delivered_qty`
- Выкуплено товаров -> `items_purchased` -> `fact_sku_daily.items_purchased`
- Отменено товаров* -> `items_canceled` -> `fact_orders_daily.cancelled_qty`
- Возвращено товаров* -> `items_returned` -> `fact_orders_daily.returned_qty`

## 2) 验收指标（替代仅看 mappedCount）
本轮强制输出：
- correctlyMappedCount
- wronglyMappedCount
- unmappedCount

通过门槛：`wronglyMappedCount == 0`。

## 3) 修正策略
1. registry exact/contains 仍优先。
2. 俄语高风险字段加入强约束优先级（`ru_strict_golden` / `ru_strict_pattern`），避免被 `name/orders` 等泛字段抢占。
3. 一对一去重策略改为保守模式：
   - 对非强约束重复 canonical 才去重；
   - 强约束俄语字段不被 duplicate 规则清空。

## 4) 浏览器真实链路复验（俄语真实文件）
采用浏览器链路触发服务器侧真实文件解析（`/api/import/upload-server-file`）并继续 `/api/import/confirm`：
- Network: `browser:/tmp/codex_browser_invocations/fba38ab61f7b44b8/artifacts/artifacts/p0_ru_real_browser_network.json`
- 截图: `browser:/tmp/codex_browser_invocations/fba38ab61f7b44b8/artifacts/artifacts/p0_ru_real_browser_chain.png`

## 5) 本轮结论
- 已从“映射数量高”转为“映射正确性”口径。
- 当前俄语 golden 字段集实现 `wronglyMappedCount = 0`（见 JSON 证据）。
- 仍不把俄语导入整体标记为已可用完成态；后续继续按正确性口径推进。
