# P0 收口项：多格式真实证据补齐（item）

## 范围
仅处理 `import_overall_gate_split_table` 的“多格式真实证据补齐”项，不扩展其它模块。

## 本轮动作
1. 增加测试样本白名单：`GET /api/import/test-fixture/cn_csv`。
2. 用浏览器真实链路分别执行：
   - `analytics_xlsx` -> 正式 `POST /api/import/upload` -> `POST /api/import/confirm`
   - `cn_csv` -> 正式 `POST /api/import/upload` -> `POST /api/import/confirm`
3. 汇总当前格式证据覆盖与缺口。

## 浏览器证据
- Network: `browser:/tmp/codex_browser_invocations/81231d89c7c44f35/artifacts/artifacts/p0_multiformat_browser_network.json`
- Screenshot: `browser:/tmp/codex_browser_invocations/81231d89c7c44f35/artifacts/artifacts/p0_multiformat_browser_chain.png`

## 结果摘要
- `xlsx`（analytics_xlsx）：upload/confirm 成功，`importedRows=1370`, `errorRows=0`, `quarantineCount=0`。
- `csv`（cn_csv）：upload/confirm 成功，`importedRows=11`, `errorRows=0`, `quarantineCount=0`, `ignoredRows=32`。

## 当前结论（item 级）
- `csv` 与 `xlsx` 的浏览器真实链路证据已补强到“正式 /upload + /confirm”。
- `xls/xlsm/xlsb/json` 仍缺浏览器真实证据，尚不能上调结论。

## 边界
- `test-fixture` 仅用于当前环境浏览器取样，不替代生产上传入口。
- 本项仅是“多格式真实证据补齐”的阶段推进，不等于导入整体通过。
