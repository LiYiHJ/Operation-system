# P0-import-reopen 专项清障报告（真实文件 parse/mapping 稳定性）

> 范围：仅导入子系统（Reader/Normalization/Mapping/Parse explainability），不推进 P0-3/P0-4。

## 一、先复现（按真实输入）
复现文件：
- `analytics_report_2026-03-12_23_49.xlsx`
- `销售数据分析.xlsx`
- 用户当前 csv 场景（`sample_data/p0_csv_scene_from_cn.csv`）
- `p4_demo_import.csv`

复现结论（修复前表现）：
- `analytics_report_2026-03-12_23_49.xlsx` 在 legacy openpyxl 直接报 `stylesheet invalid XML`，可导致上传 500。
- 中文 xlsx/csv 在旧候选口径下存在 candidateColumns 被误裁剪风险。
- 中文列头在真实报表上存在匹配不足。

## 二、分层根因（A~G）
A. 文件读取层：`openpyxl` 对坏样式 XML 敏感，直接抛错。
B. 表头识别层：读失败时无法进入 header 识别。
C. 数据区抽取层：读失败时数据区不可达。
D. 规范化层：旧逻辑会把 `col_*` 与占位逻辑混用，可能误裁候选列。
E. 候选字段层：旧实现中候选口径易与映射命中耦合。
F. 中文匹配层：normalize + alias 覆盖不足，contains/去单位匹配不充分。
G. 前端消费层：DataImportV2 按后端 `stats + ignoredFields` 计算展示，后端口径异常会直接反映为页面候选/映射异常。

## 三、直接修复（本轮）
1. Reader Chain：`calamine -> openpyxl(read_only,data_only) -> OOXML repair -> soffice convert`。
2. candidateColumns 口径修正：与映射命中解耦，仅按列属性剔除。
3. 单一字段注册表（Single Field Registry）：统一 canonical/aliases/type/unit/enum/validator/factTarget/displayLabel，并通过 `/api/import/field-registry` 同步给前后端。
4. 中文映射增强：header normalize + 去单位匹配 + 中文 alias 扩展 + registry 优先匹配。
5. 映射结果解释增强：`fieldMappings` 返回 `originalField/normalizedField/standardField/mappingSource/confidence`。
6. validator 仅影响 confidence，不一票否决候选资格。
7. confirm 增加行级隔离统计：`rowErrorSummary`（auto_fixed/ignorable/quarantined/fatal）。

## 四、通过标准对照
- xlsx 不再 500：通过。
- csv candidateColumns 不再异常缩减：通过。
- 中文核心字段命中：通过。
- parse 结果可解释：通过（reader/stats 全量返回）。
- confirm_import 不退化：通过（四样本均 success；中文样本仍有脏行 errorRows，属数据质量子项）。

## 五、证据清单
- 结构化证据：`docs/p0_import_reopen_repro_fix.json`
- Reader 重构回归：`docs/p0_import_reader_chain_regression.json`
- Reader 重构说明：`docs/p0_import_reader_chain_redesign_report.md`
- 本报告：`docs/p0_import_reopen_special_clearance_report.md`

## 六、前端截图
- 已成功抓取导入页解析后截图（csv 场景）：
  `browser:/tmp/codex_browser_invocations/74801fc234842823/artifacts/artifacts/p0_import_network_ui.png`

## 七、浏览器 Network 样例
- 上传链路 network 样例：
  `browser:/tmp/codex_browser_invocations/74801fc234842823/artifacts/artifacts/p0_import_network_samples.json`

- 样例字段包含：
  - `/api/import/upload` 响应状态码
  - upload body（mappedCount/candidateColumns 等）

## 八、状态声明（按你的限制）
- 本轮不推进 P0-3 / P0-4。
- 不将“导入整体问题”标记为彻底关闭；中文真实样本仍有行级脏数据 errorRows，需要后续数据治理。
