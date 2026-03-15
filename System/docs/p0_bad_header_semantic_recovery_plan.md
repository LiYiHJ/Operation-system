# P0 下一轮技术改造计划：bad-header / 脏表头 / 多层表头语义恢复

> 仅针对导入模块技术改造，不是文档计划。

## 0. 目标
将当前“风险可见”推进到“风险可恢复”：对 bad-header / multi-row header 场景显著降低 `semantic=risk` 误伤与漏判。

## 1) Section/Header block detection
### 算法步骤
1. 在前 N 行（建议 N=30）做块扫描，提取：
   - 字符密度、数字占比、空值占比
   - 合并单元格痕迹（重复空列 + 非空标题岛）
   - 关键词触发（如“销售/漏斗/因素”等 section 标识）
2. 用规则+打分识别 header block 起止区间，而不是单行硬判。
3. 输出 `headerBlock: {startRow, endRow, confidence}`。

### 预计修改模块
- `System/src/ecom_v51/services/import_service.py`（read/normalize 阶段）

### 验收标准
- bad-header 样本能稳定识别到多行 header block。
- 不破坏当前 real xlsx/csv 样本头部识别。

## 2) Multi-row header flatten
### 算法步骤
1. 对 header block 内多行做列内拼接（`row1 + row2 + ...`），去重词、清洗单位词。
2. 对“section + 子字段”组合生成 canonical header（例如 `漏斗_展示次数`）。
3. 对拼接后 header 进行 alias+registry 匹配。

### 预计修改模块
- `System/src/ecom_v51/services/import_service.py`
- `System/config/field_aliases_zh_ru_en.yaml`（按需补 alias）

### 验收标准
- `ru_bad_header_xlsx` 的 `mappedCount/mappingCoverage` 明显提升。
- 关键字段命中（orders/impressions/product_card_visits 等）显著改善。

## 3) Placeholder column filtering
### 算法步骤
1. 增强占位列识别：`col_\d+`、`Unnamed:*`、空白标题列。
2. 若列标题占位但值分布像真实指标列，则进入“二次判定池”，否则剔除。
3. 输出 `droppedPlaceholderColumns` 与 `rescuedPlaceholderColumns`。

### 预计修改模块
- `System/src/ecom_v51/services/import_service.py`

### 验收标准
- bad-header 样本中无意义占位列显著减少。
- 避免把真实指标列错误丢弃。

## 4) Structural header scoring
### 算法步骤
1. 构建结构评分 `headerStructureScore`：
   - 有效字段比率
   - 连续可解释列长度
   - section-子字段一致性
2. 与 `mappingCoverage` 联合形成语义前置判据。
3. 输出 `headerStructureRiskSignals`（可解释原因）。

### 预计修改模块
- `System/src/ecom_v51/services/import_service.py`
- `System/frontend/src/pages/DataImportV2.tsx`（风险明细展示）

### 验收标准
- bad-header 可稳定输出结构风险分与风险信号。
- real 样本结构分应稳定高于阈值。

## 5) Semantic gate 前移
### 算法步骤
1. 在 parse 阶段先跑“结构门禁 + 语义门禁”联合判断。
2. 若结构分过低，优先进入恢复流程（header recovery pass），再做 semantic gate 终判。
3. 输出 `preRecoveryStatus` 与 `postRecoveryStatus`。

### 预计修改模块
- `System/src/ecom_v51/services/import_service.py`
- `System/frontend/src/types/index.ts`（新增前后状态字段）

### 验收标准
- bad-header 在 recovery 后出现可量化改善（例如 risk->passed 或 risk 原因减少）。
- 若未改善，risk 原因必须更可解释。

## 6) Risk downgrade / recovery strategy
### 算法步骤
1. 对 `semantic=risk` 样本触发自动恢复链：
   - header block 重判
   - flatten 重建
   - placeholder 过滤重跑
2. 比较前后指标：`mappedCount/mappingCoverage/coreFieldHit`。
3. 仅当超过阈值才 downgrade（risk->passed），否则保留 risk 并附恢复失败原因。

### 预计修改模块
- `System/src/ecom_v51/services/import_service.py`
- `System/src/ecom_v51/api/routes/import_route.py`（返回恢复前后摘要）

### 验收标准
- downgrade 条件严格且可审计。
- 无“链路通过即语义通过”的回退。

---

## 样本与验证集（证明修复有效）
1. `System/sample_data/ozon_bad_header_or_missing_sku.xlsx`（主攻样本）
2. `System/data/analytics_report_2026-03-12_23_49.xlsx`（俄语真实对照）
3. `System/data/销售数据分析.xlsx`（中文真实对照）
4. 追加至少 1 份新脏表头样本（后续补）

验证通过标准（下一轮）：
- bad-header 样本：`semanticStatus` 至少可从 risk 降为可恢复态，或 risk 原因收敛且关键字段命中提升。
- 对照样本：不得退化（保持 passed/passed/passed）。
