# P0 收口项续推进：多格式真实证据补齐（xls/xlsm/xlsb/json）

## 范围
仅处理剩余 4 个格式：`xls / xlsm / xlsb / json`，不扩展其它模块。

## 核查方法
- 样本盘点命令：
  - `rg --files System/data System/sample_data | rg '\.(xls|xlsx|xlsm|xlsb|json)$'`
- 结果：当前仓库仅发现 `xlsx` 样本，未发现可用于浏览器链路的 `xls/xlsm/xlsb/json` 真实样本。

## 结论（本轮）
1. `xls/xlsm/xlsb/json` 均**不满足“真实样本 + 浏览器证据”**条件。
2. 这四项结论保持“未验证/未完成实证”，不做上调。
3. 不改动既有边界：
   - RU 仅“高风险语义纠偏阶段性通过”；
   - xlsx 仅“传输链路阶段性通过”；
   - 不宣称导入整体通过。

## 后续所需输入
- 每个格式至少 1 个真实样本文件（来源可追溯）。
- 同格式浏览器链路证据（`/api/import/upload + /api/import/confirm` network + screenshot）。

## 当前状态标记
- 该子项在当前样本条件下已阶段性收口，剩余项标记为**外部样本依赖阻塞**。
