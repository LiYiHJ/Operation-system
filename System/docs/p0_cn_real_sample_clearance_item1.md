# P0 收口项 #1：中文真实样本清障（当前轮）

## 目标
仅处理 `import_overall_gate_split_table` 中“中文真实样本（阶段性通过）”这一项，不扩展其他模块。

## 本轮处理
1. 放宽 `col_1` 的 SKU 识别特征（支持 `货号/sku` 标记型值）。
2. 增加 SKU 值标准化：
   - 从 `货号/артикул/sku` 文本中抽取标准 SKU token；
   - 明显商品标题/描述文本不作为 SKU 入库。
3. 调整验证阶段：
   - 对“仅 SKU 为空”的说明/汇总类行不进入 quarantine（避免大量假错误）。

## 结果（同一真实样本）
- 文件：`System/data/销售数据分析.xlsx`
- 解析：`mappedCount=29, unmappedCount=3, candidateColumns=32`
- confirm：`status=success, importedRows=11, errorRows=0`
- `rowErrorSummary`: `quarantined=0, fatal=0`

## 边界说明
- 该结果只代表“中文真实样本此项清障推进”，不等于导入整体通过。
- 当前 importedRows 降低，表示样本内大量无 SKU 行被按说明/汇总类处理并忽略；后续仍需数据治理细化规则。
