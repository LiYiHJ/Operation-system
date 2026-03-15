# P0 导入底座重做报告（Reader Chain + Normalization + Mapping + Explainability）

> 本轮仅处理导入子系统，不扩展其他模块。

## 1) Reader Chain（按要求顺序）
1. `calamine` 优先读取（pandas engine=calamine）
2. fallback 到 `openpyxl` 只读值模式（`load_workbook(read_only=True, data_only=True)`）
3. fallback 到 OOXML 轻量修复（修复 horizontal / activePane 枚举）后重试
4. fallback 到 `soffice --headless --convert-to xlsx` 后再读

并输出：
- `readerEngineUsed`
- `readerFallbackStage`

## 2) Normalization（与 Reader 解耦）
- 自动识别 headerRow
- 多层表头展平
- 删除 `Unnamed:*` 占位列
- 删除说明行 / 汇总行
- 删除动态趋势列
- 输出统计：
  - `rawColumns/rawColumnNames`
  - `normalizedColumns/normalizedColumnNames`
  - `candidateColumns/candidateFieldNames`
  - `ignoredColumns/ignoredFields`
  - `removedDescriptionRows`
  - `removedSummaryRows`
  - `droppedPlaceholderColumns`
  - `droppedDynamicColumns`

## 3) Mapping
- header normalize 增强：全角/半角、括号、标点、空格统一
- 去单位后二次匹配
- 中文/俄文/英文 alias 词典并存
- 匹配层：exact / contains / 去修饰匹配
- validator 仅影响 confidence，不否决候选列资格

## 4) 绑定文件回归结果（详见 JSON）
证据文件：`docs/p0_import_reader_chain_regression.json`

关键结论：
- `analytics_report_2026-03-12_23_49.xlsx`：
  - legacy openpyxl 直接失败（stylesheet invalid XML）
  - 现已通过 `fallback_ooxml_repair` 成功 parse，API 200，confirm success（errorRows=0）
- `销售数据分析.xlsx`：candidateColumns=32，mapped=29，中文核心字段命中
- 当前真实 csv 场景：candidateColumns=32，不再缩到 1
- demo 样本：candidateColumns=17，mapped=17，confirm success

## 5) 未关闭项（明确保留）
- 中文真实样本存在行级脏数据，`confirm` 虽成功但 `errorRows` 仍非 0（23/25）。
- 本轮不将“导入整体问题”标记为完全解决，仅确认“稳读、稳映射、可解释性”底座已重做。

## 6) 截图
已尝试使用 browser_container 产出导入页截图，但浏览器容器内 Chromium 启动崩溃（SIGSEGV），本轮无法产出可引用截图。
