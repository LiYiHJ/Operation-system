# P0 xlsx 多样本稳定性验证（双层门禁：链路 + 语义）

## 范围与边界
- 本轮只做 xlsx 验收逻辑升级：从“链路通过”升级为“链路/语义双层门禁”。
- 只验证正式路径：`POST /api/import/upload` + `POST /api/import/confirm`。
- 不扩模块，不外推为“导入整体通过”。

## 双层门禁与三层状态定义

### 1) 传输门禁（transport gate）
- 判定字段：upload status code、confirm status code、confirm.status、factLoadErrors。
- 通过条件：
  - upload `status_code=200`
  - confirm `status_code=200`
  - confirm `status=success`
  - `factLoadErrors=0`

### 2) 语义门禁（semantic gate）
- 语义最小核心字段集合（必须命中）：
  - `sku`
  - `orders` 或 `order_amount`（二选一）
  - `impressions_total`
  - `product_card_visits` 或 `add_to_cart_total`（二选一）
- 语义增强字段池（至少命中 2 项）：
  - `stock_total` / `rating_value` / `review_count` / `price_index_status` / `promo_days_count`
- 附加阈值：
  - `mappingCoverage >= 0.5`
  - `mappedCount >= 8`
  - `wronglyMappedCount = 0`（如返回该字段）

### 3) 三层状态（每样本必须输出）
- `transportStatus`: `passed` / `failed`
- `semanticStatus`: `passed` / `risk` / `failed`
- `finalStatus`: `passed` / `risk` / `failed`

状态规则：
- `finalStatus=passed` 仅当 `transportStatus=passed` 且 `semanticStatus=passed`
- `finalStatus=risk` 当 `transportStatus=passed` 但 `semanticStatus=risk/failed`
- `finalStatus=failed` 当 `transportStatus=failed`

## 三样本状态总表

| sampleId | 样本类型 | transportStatus | semanticStatus | finalStatus | semanticAcceptanceReason |
|---|---|---|---|---|---|
| `ru_real_xlsx` | real_business_xlsx | passed | passed | passed | `semantic_gate_met` |
| `cn_real_xlsx` | real_business_xlsx | passed | passed | passed | `semantic_gate_met` |
| `ru_bad_header_xlsx` | structure_dirty_variant_xlsx | passed | risk | risk | `low_mapping_coverage`, `header_structure_risk`, `semantic_gate_not_met` |

## 每样本核心证据（摘要）

### ru_real_xlsx
- upload: `200`, `mapped=28`, `unmapped=19`, `candidateColumns=47`
- semantic metrics: `mappingCoverage=0.596`, `mappedConfidence=0.941`, `correctlyMappedCount=8`, `wronglyMappedCount=0`
- coreFieldHitSummary: 核心组全命中，增强字段命中 5 项
- confirm: `status=success`, `importedRows=1370`, `errorRows=0`, `quarantineCount=0`, `stagingRows=1370`, `factLoadErrors=0`
- DB: `import_batch(success_count=1370,error_count=0)`, `import_staging_row=1370`, `import_error_log=0`, `fact_sku_daily=1370`, `fact_orders_daily=1370`

### cn_real_xlsx
- upload: `200`, `mapped=29`, `unmapped=3`, `candidateColumns=32`
- semantic metrics: `mappingCoverage=0.906`, `mappedConfidence=0.945`, `correctlyMappedCount=0`, `wronglyMappedCount=0`
- coreFieldHitSummary: 核心组全命中，增强字段命中 4 项
- confirm: `status=success`, `importedRows=11`, `errorRows=0`, `quarantineCount=0`, `ignoredRows=34`, `stagingRows=11`, `factLoadErrors=0`
- DB: `import_batch(success_count=11,error_count=0)`, `import_staging_row=11`, `import_error_log=0`, `fact_sku_daily=11`, `fact_orders_daily=11`

### ru_bad_header_xlsx
- upload: `200`, `mapped=4`, `unmapped=69`, `candidateColumns=73`
- semantic metrics: `mappingCoverage=0.055`, `mappedConfidence=0.925`, `correctlyMappedCount=0`, `wronglyMappedCount=0`
- coreFieldHitSummary: 仅 `sku` 命中；`orders/order_amount`、`impressions_total`、`product_card_visits/add_to_cart_total` 均未命中；增强字段命中 0 项
- confirm: `status=success`, `importedRows=1505`, `errorRows=0`, `quarantineCount=0`, `stagingRows=1505`, `factLoadErrors=0`
- DB: `import_batch(success_count=1505,error_count=0)`, `import_staging_row=1505`, `import_error_log=0`, `fact_sku_daily=1505`, `fact_orders_daily=1505`
- 结论：链路通过 ≠ 语义通过，必须标记为 `semantic risk`，不可归入 passed。

## 必答 5 问

### A. 三个样本中，哪些是 transport pass？
- `ru_real_xlsx`、`cn_real_xlsx`、`ru_bad_header_xlsx` 全部 `transportStatus=passed`。

### B. 三个样本中，哪些是 semantic pass？
- `semanticStatus=passed`：`ru_real_xlsx`、`cn_real_xlsx`
- `semanticStatus=risk`：`ru_bad_header_xlsx`

### C. `ru_bad_header_xlsx` 为什么不能算真正 passed？
- 虽然 `/upload + /confirm + fact write` 均成功，但语义门禁未满足：
  - `mappingCoverage=0.055` 过低（`low_mapping_coverage`）
  - `candidateColumns=73` 且 `unmapped=69`，表头结构风险高（`header_structure_risk`）
  - 核心语义字段组未命中完整（`semantic_gate_not_met`）
- 因此只能判为 `finalStatus=risk`，不能是 passed。

### D. gate table 里的 xlsx 行最终应该怎么写？
- 应写成：
  - “`xlsx 上传链路：阶段性通过`（路径层稳定）”
  - 同时明确“多样本语义门禁未全部通过（bad-header 为 semantic risk）”。

### E. 这轮是逻辑收口，还是仍然只是文案修正？
- 是**逻辑收口**：已引入双层门禁与三层状态，并对 3 个样本按统一规则重新判定；不是单纯措辞微调。

## 本轮结论
- 路径层：`3/3 passed`
- 语义层：`2/3 passed`，`1/3 risk`
- 最终：**xlsx 多样本验收为“阶段性通过（路径稳定，但语义门禁未全部通过）”**。
