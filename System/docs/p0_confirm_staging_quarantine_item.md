# P0 收口项：confirm / staging / quarantine 脏行治理（item）

## 范围
仅处理 `import_overall_gate_split_table` 的 `中文真实样本` 数据质量解释能力增强，不扩展其它模块。

## 本轮改动
1. 细化 ignored 分类，不再长期停留在 `no_sku_noise_row` 大桶：
   - `summary_row`
   - `title_row`
   - `description_row`
   - `empty_row`
   - `non_business_noise_row`
2. 分类前增加“有效单元格”过滤（`none/null/nan/—/-` 等不计入有效内容），降低误判。
3. `confirm` 返回保持稳定：
   - `ignoredRows`
   - `ignoredReasonSummary`
   - `ignoredRowSamples`（含 `rowSummary`）

## 同一中文真实样本复验
- 样本文件：`System/data/销售数据分析.xlsx`
- parse：`mappedCount=29, unmappedCount=3`
- confirm（分类细化后）：
  - `status=success`
  - `importedRows=11`
  - `errorRows=0`
  - `quarantineCount=0`
  - `stagingRows=11`
  - `factLoadErrors=0`
  - `ignoredRows=34`
- ignored 分类分布：
  - `summary_row=0`
  - `title_row=20`
  - `description_row=1`
  - `empty_row=11`
  - `non_business_noise_row=2`

## 每类样例（前若干条）
- `title_row`：
  - row 4: `A`
  - row 5: `请添加至促销活动`
- `description_row`：
  - row 1: `根据金额和数量 | 目前 | 最近 28 天内`
- `empty_row`：
  - row 6: ``
  - row 10: ``
- `non_business_noise_row`：
  - row 2: `1.0 | 213.0 | 0,15%`
  - row 3: `0.0`
- `summary_row`：本样本本次为 0（口径已预置，待后续样本触发）。

## 关键证明
分类细化不改变当前核心结果：
- `importedRows` 仍为 11
- `errorRows` 仍为 0
- `quarantineCount` 仍为 0
- `stagingRows` 仍为 11
- `factLoadErrors` 仍为 0

## 边界
- 本项仅是中文真实样本的数据质量解释能力增强，不等于中文真实样本整体通过。
- 不等于导入整体通过。


## 补充泛化验证
- 详见：`docs/p0_cn_real_generalization_validation.md` / `docs/p0_cn_real_generalization_validation.json`。
- 在 `销售数据分析.xlsx` 与 `p0_csv_scene_from_cn.csv` 两份中文样本下，ignored 分类均保持多类分布且核心指标未退化。
