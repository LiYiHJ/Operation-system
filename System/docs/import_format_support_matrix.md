# 导入格式支持矩阵（P0 收口版）

> 目的：明确“格式能力”与“证据强度”是两回事。
> 本矩阵不宣称导入整体已通过，仅用于当前阶段收口。

## 边界声明（必须保留）
1. `/api/import/upload-server-file` 仅用于当前环境测试辅助链路，不等于最终生产上传链路通过。
2. 本轮通过的是“RU 高风险语义映射纠偏”，不等于俄语全场景稳定，也不等于导入整体通过。

## 支持矩阵

| 格式 | Reader/解析实现状态 | 浏览器真实证据 | 证据来源 | 当前结论 |
|---|---|---|---|---|
| `csv` | 已支持（编码探测 + 规范化 + 映射 + confirm） | 有（正式 `/upload`） | `p0_multiformat_browser_network.json`（`cn_csv`：`test-fixture` 取样后走正式 `/upload`+`/confirm`） | 阶段性通过 |
| `xlsx` | 已支持（calamine -> openpyxl values -> OOXML repair -> convert fallback） | 有（正式 `/upload`） | `p0_multiformat_browser_network.json`（`analytics_xlsx`：`test-fixture` 取样后走正式 `/upload`+`/confirm`） | 传输链路阶段性通过（RU 高风险字段同路径复核已完成；未外推为全语义稳定通过） |
| `xls` | 代码路径存在（兼容读取器） | 无（缺真实样本） | 本轮仅完成样本盘点，未发现 `xls` 真实样本 | 未验证/未完成实证 |
| `xlsm` | 代码路径复用 Excel 读取链 | 无（缺真实样本） | 本轮仅完成样本盘点，未发现 `xlsm` 真实样本 | 未验证/未完成实证 |
| `xlsb` | 目标支持（依赖读取器能力） | 无（缺真实样本） | 本轮仅完成样本盘点，未发现 `xlsb` 真实样本 | 未验证/未完成实证 |
| `json` | 历史支持路径存在（非本轮重点） | 无（缺真实样本） | 本轮仅完成样本盘点，未发现 `json` 导入真实样本 | 未验证/未完成实证 |

## 备注
- 上表“阶段性通过”表示：
  - 有实现；
  - 有当前阶段证据；
  - 但仍保留已知风险，不可外推为“导入整体通过”。
- 后续若进入下一阶段，需要补齐 `xls/xlsm/xlsb/json` 的浏览器链路证据，再更新结论。

## 本轮补充证据
- 结构化明细：`docs/p0_multiformat_real_evidence_item.json`
- 说明文档：`docs/p0_multiformat_real_evidence_item.md`
- 当前仍缺浏览器真实证据：`xls/xlsm/xlsb/json`。

- RU 冲突复核：`docs/p0_ru_upload_conflict_root_cause.md`（同一路径对比：offline/upload/browser network）。

- 剩余格式差距清单：`docs/p0_multiformat_remaining_formats_gap.md` / `docs/p0_multiformat_remaining_formats_gap.json`。
