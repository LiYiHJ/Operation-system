# 中文真实样本 item #1 行级差异验证（19 -> 11）

> 状态口径：仅用于“阶段性通过，待行级差异验证”收口。

## 1) 行级差异清单（被忽略行）
详见：`docs/p0_cn_real_item1_row_level_diff.json` 的 `ignoredRowDiff.rows`。

本轮识别到被忽略行共 9 行（全部为标题/伪SKU文本行），典型原始内容：
- `Mop, length 13 cm`
- `Mop, length 25 cm`
- `Vase, 24.8 cm , Resin, 1 pcs`

这些行共同特征：
- SKU 原始单元格是商品标题文本，而非可入库 SKU token；
- 核心业务指标（订单金额/曝光/下单）为空；
- 属于报表展示层行，不应入事实表。

## 2) 是否误忽略真实业务行
结论：**未发现真实业务行被误忽略**。

证据：被忽略行的 `rawSkuCell` 均为标题文本，且 `orderAmount/impressionsTotal/orders` 为空；与可入库事实行特征不一致。

## 3) staging / quarantine / ignored 统计
- stagingRows: 11
- quarantineCount: 0
- errorRows: 0
- rowErrorSummary: `auto_fixed=0, ignorable=0, quarantined=0, fatal=0`

## 4) 最终 confirm 与 fact 写入
- confirm: `status=success, importedRows=11, errorRows=0`
- fact 写入：
  - `fact_sku_daily = 11`
  - `fact_orders_daily = 11`
  - `fact_inventory_daily = 11`
  - `fact_reviews_daily = 11`

## 5) 边界说明
- 本验证用于证明“减少的行是伪数据而非真实业务行”。
- item #1 仍维持“阶段性通过”表述，不扩大为导入整体通过。
