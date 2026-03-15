# P0 xlsx 双层门禁系统化收口证据

## 1) API 响应样例（3 个 xlsx 样本）
见：`System/docs/p0_xlsx_dual_gate_runtime_closure_evidence.json`

样本结论：
- `ru_real_xlsx`：`transport=passed, semantic=passed, final=passed`
- `cn_real_xlsx`：`transport=passed, semantic=passed, final=passed`
- `ru_bad_header_xlsx`：`transport=passed, semantic=risk, final=risk`

## 2) UI 截图证据（bad-header）
- 风险态页面（可见 transport/semantic/final + 风险提示 + 非绿色按钮）：
  - `browser:/tmp/codex_browser_invocations/adcf55cff4682b2c/artifacts/artifacts/xlsx_gate_ui_before_click.png`
- 点击风险按钮后，二次确认弹框：
  - `browser:/tmp/codex_browser_invocations/adcf55cff4682b2c/artifacts/artifacts/xlsx_gate_ui_confirm_modal.png`

## 3) batch/runtimeAudit 样例
- batch message 示例：
  - `去重100条，错误0条; transport=passed, semantic=risk, final=risk`
- runtimeAudit 示例：
  - `transportStatus=passed`
  - `semanticStatus=risk`
  - `finalStatus=risk`
  - `semanticAcceptanceReason=[header_structure_risk, low_mapping_coverage, semantic_gate_not_met]`

## 4) 当前门禁策略
- **soft gate**：当 `finalStatus=risk` 时，前端允许继续，但必须弹出二次确认并展示风险原因。
- 策略建议：后续可按环境开关升级为 **hard gate**（`finalStatus=risk` 禁止 confirm），用于更严格生产治理。

## 5) 当前结论
- 双层门禁（API + UI + audit）已进入系统运行。
- 导入整体未关闭；当前不外推为“全格式验证完成”。
