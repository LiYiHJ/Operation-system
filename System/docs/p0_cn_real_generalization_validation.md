# P0 中文真实样本：ignored 分类泛化验证（item）

## 范围
仅继续中文真实样本数据质量治理解释能力验证，不扩展其它模块。

## 验证样本
1. `System/data/销售数据分析.xlsx`（真实 xlsx）
2. `System/sample_data/p0_csv_scene_from_cn.csv`（同口径 csv 场景）

## 结果对比
### A) `销售数据分析.xlsx`
- parse: `mappedCount=29`, `unmappedCount=3`
- confirm: `importedRows=11`, `errorRows=0`, `quarantineCount=0`, `ignoredRows=34`, `stagingRows=11`, `factLoadErrors=0`
- ignoredReasonSummary:
  - `title_row=20`
  - `empty_row=11`
  - `non_business_noise_row=2`
  - `description_row=1`
  - `summary_row=0`

### B) `p0_csv_scene_from_cn.csv`
- parse: `mappedCount=29`, `unmappedCount=3`
- confirm: `importedRows=11`, `errorRows=0`, `quarantineCount=0`, `ignoredRows=32`, `stagingRows=11`, `factLoadErrors=0`
- ignoredReasonSummary:
  - `title_row=20`
  - `empty_row=9`
  - `non_business_noise_row=2`
  - `description_row=1`
  - `summary_row=0`

## 结论
1. ignored 分类在两份中文样本下都呈现多类非零分布（不再是单桶）。
2. 核心导入指标未退化（`importedRows/errorRows/quarantineCount/stagingRows/factLoadErrors` 保持稳定）。
3. 当前可判定为“解释性增强在现有中文样本下具备可迁移性”；但仍需更多异构真实样本验证泛化稳定性。

## 边界
- 本项不等于中文真实样本整体通过。
- 不等于导入整体通过。
