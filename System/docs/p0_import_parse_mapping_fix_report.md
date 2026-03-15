# P0 导入重开：parse / mapping 稳定性修复报告（仅本项）

## 范围
仅处理导入 P0 parse/mapping 稳定性，不推进 P0-3/P0-4。

## 修复项
1. **XLSX 读取修复**
   - 默认 `openpyxl` 读取。
   - 遇到 stylesheet/worksheet 枚举异常时自动执行 OOXML 轻量修复后重试。
   - 已覆盖修复值：
     - `horizontal="Right" -> "right"`
     - `horizontal="Left" -> "left"`
     - `activePane="bottom-right" -> "bottomRight"`
     - `activePane="bottom-left" -> "bottomLeft"`
2. **candidateColumns 口径修复**
   - candidateColumns 仅排除：占位列（Unnamed/空）、动态列、汇总/说明列。
   - 不再因未命中字典提前剔除候选列。
3. **中文映射修复**
   - header normalize 增强：全角/半角、空白、中文标点、括号统一。
   - 增加去单位匹配变体。
   - 扩充中文 alias 词典（销售分析中文列头）。
   - 匹配支持 exact / contains / 去单位后匹配。
4. **validator 逻辑修复**
   - validator 仅在已有结构匹配（关键词/正则）时提升 confidence。
   - 不再允许“仅凭 validator”触发字段映射，也不会因此丢弃候选列。
5. **API 上传中文文件名修复**
   - `secure_filename` 产生无扩展名时，补齐原始扩展名，避免 `不支持的文件格式`。

## 复现与回归文件
- `data/analytics_report_2026-03-12_23_49.xlsx`
- `data/销售数据分析.xlsx`
- `sample_data/p0_csv_scene_from_cn.csv`（用于复现“csv candidateColumns 缩减”场景）
- `sample_data/p4_demo_import.csv`

## 关键结果
详见：`docs/p0_parse_mapping_fix_result.json`

- xlsx 样式异常文件：legacy openpyxl 读取失败 -> 修复后 parse 成功，`sourceType=xlsx_repaired`。
- csv 场景：`candidateColumns=32`（未缩减到 1），中文字段可映射到核心业务字段。
- 中文字段映射命中清单已输出到 `after.*.chineseHitFields`。
- confirm_import 回归：四个样本 `status=success`（其中中文文件存在业务脏行，`errorRows` 非 0，但不再整批失败）。
- API 样例：`apiSamples` 包含 upload/confirm 请求返回。

## 未关闭项（保持 P0 子项开启）
- 中文样本 `销售数据分析.xlsx` / `csv_scene` 仍存在脏行（`errorRows=23`），需要后续做“行级清洗策略”才能逼近 `errorRows=0`。
- 本次仅完成 parse/mapping 稳定性与读文件 500 修复，不将导入问题整体标记为全部关闭。

## 截图说明
已尝试用 browser 工具进行页面截图（登录 -> 导入页 -> 上传 -> 解析），但工具调用超时，未成功产出可引用截图；相关尝试日志见本轮执行记录。
