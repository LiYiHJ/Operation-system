# P0 Import 底座升级（Phase 1 + Phase 2）

## 范围
本阶段只覆盖：
- Phase 1：导入底座升级（Reader / Structure / Mapping / Cleaning & Quarantine）
- Phase 2：confirm + staging/fact 两段写入重构

未扩展：契约统一/Celery/观测门禁（后续阶段处理）。

## 设计要点

### 1) 文件读取层（Reader Chain）
- 已落地链路：`calamine -> openpyxl_values -> OOXML repair -> format convert(soffice)`。
- 返回 `readerEngineUsed` + `readerFallbackStage`，用于前端和证据回放解释。

### 2) 表结构识别层（Structure Detection）
- header scoring + 多行表头扁平化 + 数据区抽取。
- candidate 列仅按结构规则剔除（占位/动态/说明/汇总），不依赖映射命中。

### 3) 字段映射层（Single Registry + Scoring）
- 新增统一字段注册表：`config/import_field_registry.json`。
- 解析时统一走 registry alias（zh/ru/en/platform）+ normalize（全半角、标点、单位）。
- `fieldMappings` 返回 `normalizedField` 与 `mappingSource`。
- 新增 Hungarian 一对一分配步骤，避免多列挤占同一 canonical。

### 4) 行级清洗与隔离层（Row Cleaning + Quarantine）
- 清洗保持宽容（数字、百分比、报表字符串）。
- confirm 结果返回 `rowErrorSummary` + `quarantineCount`。

### 5) staging 落库层（Phase 2 新增）
- 新增表 `import_staging_row`，先写 staging，再写 fact。
- staging 行状态：`staged -> loaded / fact_error`。
- 每行记录 `trace_id`、`row_data_json`、`row_error_summary_json`。

### 6) fact 写入与审计层
- 从 staging 批量循环写入 fact。
- fact 异常同步落 `import_error_log`，并回写 staging `fact_error`。
- confirm API 返回新增：`stagingRows`、`factLoadErrors`。

## 代码改动点
- `src/ecom_v51/services/import_service.py`
- `src/ecom_v51/intelligent_field_mapper.py`
- `src/ecom_v51/db/models.py`
- `src/ecom_v51/api/routes/import_route.py`
- `config/import_field_registry.json`
- `frontend/src/pages/DataImportV2.tsx`
- `frontend/src/services/api.ts`
- `frontend/src/types/index.ts`

## 真实链路证据
- 结构化验证：`docs/p0_phase1_phase2_validation.json`
- 导入专项报告：`docs/p0_import_reopen_special_clearance_report.md`
- 浏览器截图：`browser:/tmp/codex_browser_invocations/74801fc234842823/artifacts/artifacts/p0_import_network_ui.png`
- Network 样例：`browser:/tmp/codex_browser_invocations/74801fc234842823/artifacts/artifacts/p0_import_network_samples.json`

## 风险与未关闭项
1. 中文真实样本存在行级脏值，当前以 quarantine/fact_error 暴露，不视为“导入已完全关闭”。
2. Hungarian 依赖 `scipy` 时为真 Hungarian；无依赖时降级 greedy（仍保证唯一分配）。
3. staging 表为增量落地，后续可加索引与生命周期清理策略。
