# RU 映射冲突复核：`analytics_xlsx` 同一路径对比（item）

## 1) 冲突定位结论

### 1.1 RU strict / golden 是否接入了真实 `/api/import/upload`
是，已接入同一路径。
- `/api/import/upload` 路由直接调用 `ImportService.parse_import_file`。
- `parse_import_file` 内部执行 `_strict_ru_mapping`（高优先级）并计算 `ruMappingQuality` 后返回。

### 1.2 真实 upload 与离线 RU correctness 是否同一套逻辑
本次复核对同一文件 `analytics_report_2026-03-12_23_49.xlsx` 做了“同一路径对比”：
- 离线：直接调用 `ImportService.parse_import_file`
- 在线：通过 `/api/import/upload`
- 浏览器：`test-fixture -> /api/import/upload` network 返回

结论：三者使用的是同一 `parse_import_file` 输出口径（同一代码路径/registry/后处理），关键高风险字段映射一致。

### 1.3 为什么会出现“日志看错映射、返回却正确”
根因是**日志打印时机**：
- 运行日志中那批“`Заказано на сумму -> orders` / `Доставлено товаров -> name`”来自 `map_columns -> intelligent_mapper` 的中间输出（早期候选）。
- 真实返回的 `fieldMappings` 来自 `parse_import_file` 后续流程，已经过 `_strict_ru_mapping` + alias/extra_map + 去重后处理。

因此，冲突不是“返回值错误”，而是“中间日志与最终结果混在一起被误读”。

## 2) 同一路径对比证据
详见：`docs/p0_ru_upload_path_conflict_comparison.json`

关键高风险字段（offline / upload / browser network）一致：
- `Заказано на сумму -> order_amount`
- `Доля в общей сумме заказов -> order_amount_share`
- `Доставлено товаров -> items_delivered`
- `Выкуплено товаров -> items_purchased`
- `Отменено товаров (на дату отмены) -> items_canceled`
- `Возвращено товаров (на дату возврата) -> items_returned`

并且：
- `ruMappingQuality.wronglyMappedCount = 0`
- `samePathConsistent = true`

浏览器链路证据：
- network: `browser:/tmp/codex_browser_invocations/0243c2d5196e4a37/artifacts/artifacts/p0_ru_conflict_browser_network_v3.json`
- screenshot: `browser:/tmp/codex_browser_invocations/0243c2d5196e4a37/artifacts/artifacts/p0_ru_conflict_browser_chain_v3.png`

## 3) 当前口径（按要求收敛）
在冲突复核说明期间：
- `xlsx` 在格式矩阵中只表述为“传输链路阶段性通过”，不把语义层直接写成已通过。
- `俄语真实样本` 在整体门禁表中改成“阶段性通过（证据冲突待复核）”。

## 4) 备注
本轮只处理 RU 冲突复核，不扩展到 `xls/xlsm/xlsb/json` 新项。
