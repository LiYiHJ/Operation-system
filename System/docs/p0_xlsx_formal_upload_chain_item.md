# 中文真实样本后续项：xlsx 正式上传链路（item）

## 范围
仅处理 `import_overall_gate_split_table` 的“xlsx 上传链路（阶段性通过）”项，不扩展其它模块。

## 本轮动作
1. 新增测试辅助取样接口：`GET /api/import/test-fixture/<name>`
   - 仅用于浏览器环境获取受控真实文件样本。
2. 浏览器真实链路改为：
   - `test-fixture` 取到真实 xlsx Blob
   - 调用正式 `POST /api/import/upload`
   - 再调用 `POST /api/import/confirm`

## 证据
- Browser Network: `browser:/tmp/codex_browser_invocations/2aae3bb142efd02e/artifacts/artifacts/p0_xlsx_formal_upload_network.json`
- Browser Screenshot: `browser:/tmp/codex_browser_invocations/2aae3bb142efd02e/artifacts/artifacts/p0_xlsx_formal_upload_chain.png`
- 结构化结果：`docs/p0_xlsx_formal_upload_chain_item.json`

## 结果摘要
- 正式上传链路（/upload）与 confirm 均可通。
- service 交叉验证：
  - `confirm.status = success`
  - `errorRows = 0`
  - `stagingRows > 0`
  - `factLoadErrors = 0`

## 边界
- `test-fixture` 仅用于浏览器测试环境取样，不替代生产上传入口。
- 本项只是 xlsx 上传链路清障推进，不等于导入整体通过。
