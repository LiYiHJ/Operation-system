# P0 xlsx 最终产品上传路径实证（item）

## 范围
仅处理 `xlsx` 最终产品上传路径实证，不扩展其它模块。

## 三种路径口径（明确区分）
1. `test-fixture`：`GET /api/import/test-fixture/<name>`
   - 仅用于浏览器环境“取样”，不参与解析落库结论。
2. `upload-server-file`：`POST /api/import/upload-server-file`
   - 服务器侧直读已有文件，属于测试辅助路径，不等于最终产品上传入口。
3. **正式产品路径**：`POST /api/import/upload`
   - 浏览器以 `multipart/form-data(file)` 直传，这是最终产品上传入口。

## 本轮实证链路
- Browser: `test-fixture(取样) -> 正式 /api/import/upload -> /api/import/confirm`
- 关键点：解析与入库动作都发生在正式 `/upload + /confirm` 路径。

## 浏览器证据
- network: `browser:/tmp/codex_browser_invocations/69efb3c554e1e07e/artifacts/artifacts/p0_xlsx_final_upload_path_network_v4.json`
- screenshot: `browser:/tmp/codex_browser_invocations/69efb3c554e1e07e/artifacts/artifacts/p0_xlsx_final_upload_path_browser_v4.png`

## 返回结果（本轮）
- parse(`/upload`)：
  - `mappedCount=28`
  - `unmappedCount=19`
  - `stats.candidateColumns=47`
- confirm(`/confirm`)：
  - `status=success`
  - `importedRows=1370`
  - `errorRows=0`
  - `quarantineCount=0`
  - `stagingRows=1370`
  - `factLoadErrors=0`

## DB 结果（同批次）
- `import_batch`: `status=success, success_count=1370, error_count=0`
- `import_staging_row`: `loaded=1370`
- `import_error_log`: `0`
- facts:
  - `fact_sku_daily=1370`
  - `fact_orders_daily=1370`
  - `fact_inventory_daily=1370`
  - `fact_reviews_daily=1370`

## 问题回答
这一项完成后，**xlsx 上传链路仍需保守写为“阶段性通过”**。
- 原因：当前虽已补“最终产品 `/upload` 路径”实证，但证据仍基于当前样本与当前环境，不可外推为“全场景稳定通过”。

## 边界
- 不把 `test-fixture` / `upload-server-file` 当作生产上传替代物。
- 不宣称导入整体通过。
