# P0 双层门禁：风险可见 ≠ 风险已解决（边界说明）

## 四条明确结论
1. **本轮完成的是 dual-gate runtime visibility（风险可见）**：
   - API 已返回 `transportStatus/semanticStatus/finalStatus`
   - UI 已展示三层状态与风险原因
   - audit 已记录 runtime risk 状态。

2. **本轮未完成的是 bad-header 语义恢复与映射泛化修复**：
   - `ru_bad_header_xlsx` 仍是 `transport=passed, semantic=risk, final=risk`。

3. **soft gate 不等于 semantic fix**：
   - 当前策略是 risk 可继续但需二次确认，作用是“风险暴露与操作控制”，不是“自动修复语义错误”。

4. **当前不能上调结论**：
   - 不能上调为“xlsx 稳定通过”；
   - 更不能上调为“导入整体通过”。
