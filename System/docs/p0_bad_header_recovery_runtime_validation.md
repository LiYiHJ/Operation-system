# P0 bad-header 语义恢复 runtime 验证

## 1) 三样本 before/after（pre/post recovery）对比

| sample | preRecoveryStatus | postRecoveryStatus | finalStatus | mapped before→after | coverage before→after | core hit before→after |
|---|---|---|---|---|---|---|
| ru_real_xlsx | passed | passed | passed | 24→24 | 0.511→0.511 | 4→4 |
| cn_real_xlsx | passed | passed | passed | 29→29 | 0.906→0.906 | 4→4 |
| ru_bad_header_xlsx | passed | passed | passed | 24→24 | 0.511→0.511 | 4→4 |

## 2) ru_bad_header_xlsx recovery 前后变化

- recoveryAttempted: False
- headerRecoveryApplied: False
- recoveryImproved: False
- mappedCount: 24 -> 24
- unmappedCount: 23 -> 23
- mappingCoverage: 0.511 -> 0.511
- coreFieldHit: 4 -> 4
- semanticGateReasons: semantic_gate_met
- riskOverrideReasons: (empty)

## 3) 最终状态与命名依赖清理

- ru_bad_header_xlsx 最终状态: passed。
- 本轮终判已摆脱 `file_name_risk_hint`；风险/通过仅由结构与语义指标决定。

## 4) real_xlsx / cn_real_xlsx 无退化证明

- ru_real_xlsx: upload=passed/passed/passed; confirm importedRows=1370, errorRows=0, quarantineCount=0, factLoadErrors=0。
- cn_real_xlsx: upload=passed/passed/passed; confirm importedRows=3, errorRows=0, quarantineCount=0, factLoadErrors=0。

## 5) 结论边界

- 本轮是 bad-header recovery 终判去命名依赖的实现收口。
- 不外推为“导入整体通过”。

原始 JSON：`System/docs/p0_bad_header_recovery_runtime_validation.json`
