# 导入整体门禁拆分表（P0 当前态）

> 说明：本表用于“拆分判定”，避免把局部通过误写成整体通过。

## 边界声明（必须保留）
1. `upload-server-file` 只是测试辅助链路，不可替代最终产品上传链路结论。
2. RU 本轮通过范围仅限“高风险语义映射纠偏”，不代表俄语全场景稳定。

## 门禁拆分

| 维度 | 当前状态 | 判定依据 | 备注 |
|---|---|---|---|
| 中文简化样本 | 通过 | CSV 简化场景 parse/confirm 成功，映射与确认返回一致 | 仅代表简化输入 |
| 中文真实样本 | 阶段性通过 | item#1 + item#2 已收口：confirm `errorRows=0`、`quarantineCount=0`；ignored 已细化为 `summary/title/description/empty/non_business_noise` | 分类解释能力已增强；在 xlsx+csv 两份中文样本下均呈现稳定多类分布（title/description/empty/non_business_noise），仍需更多异构真实样本验证泛化稳定性 |
| 俄语真实样本 | 阶段性通过 | RU 同路径复核已完成（offline/upload/browser 一致，`wronglyMappedCount=0`） | 仅覆盖高风险字段集合；不外推为俄语全场景稳定通过 |
| xlsx 上传链路 | 阶段性通过 | 已切换为“链路/语义双层门禁”：3 份 xlsx 均 transport pass（正式 `/api/import/upload + /api/import/confirm` + DB 对齐），其中 2 份 semantic pass、1 份 semantic risk | 路径层稳定，但语义门禁未全部通过（`ru_bad_header_xlsx` 为 `semanticStatus=risk`），不可上调为整体通过 |
| csv 上传链路 | 通过（阶段内） | 浏览器真实上传与 confirm 证据已具备 | 仍受整体导入未闭环约束 |
| confirm / staging / quarantine | 阶段性通过 | 与 item 文档一致：已回传 `ignoredRows/ignoredReasonSummary/ignoredRowSamples`，并与 `rowErrorSummary/stagingRows/factLoadErrors/import_batch/import_staging_row/import_error_log` 对齐 | 可观测性 item 已收口；ignored 原因分类已从粗桶细化为稳定分类集，但仍需更多真实样本验证泛化稳定性 |

## 总结结论（避免写大）
- 当前不能把“导入整体”标记为已解决。
- 合理表述应为：
  - RU 高风险语义映射纠偏：阶段性通过；
  - 导入底座：可用性提升明显；
  - 导入整体门禁：仍有未关闭项（尤其中文真实数据质量与部分格式实证缺口）。

## 下一步优先 item
- **中文真实样本：阶段性通过（解释性增强已收口）**。
- **xlsx 多样本稳定性验证：阶段性通过（双层门禁：transport 3/3 通过，semantic 2/3 通过）**。
- 下一优先：继续补更多异构真实 xlsx 样本，验证 mapping/header 泛化稳定性（不外推为整体导入通过）。
- `xls/xlsm/xlsb/json`：当前无真实样本，维持外部样本依赖阻塞，待样本补齐后再重开。
