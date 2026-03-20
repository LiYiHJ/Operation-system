# 运营系统设计：当前窗口完整交接总文件（可直接接手）

> 用途：给下一个窗口/下一个接手者直接继续工作。  
> 原则：**以本窗口后半段用户上传的当前代码文件为最终基线**，不再以外部公开视图或早期补丁状态为准。

---

## 0. 本文件的结论先行

### 当前最终基线（以本窗口后半段用户上传文件为准）
当前代码基线已经不是“导入页半成品”，而是：

- `App.tsx` 已做 **route-level lazy loading / Suspense**
- `DataImportV2.tsx` 已具备：
  - `dynamicCompanion / excludeFromSemanticGate`
  - `hasManualEdits`
  - “默认优先信后端摘要，手工编辑才本地重算”
  - upload/confirm 调试日志已删除
- `frontend/src/types` 已拆分为：
  - `common.ts`
  - `dashboard.ts`
  - `import.ts`
  - `analysis.ts`
  - `strategy.ts`
  - `profit.ts`
  - `ads.ts`
  - `index.ts` 作为入口
- `import_service.py` 当前应以 **reconciled / 当前上传版** 为准，包含：
  - `_build_field_mapping_summary`
  - 顶层 `mappingCoverage / mappedConfidence`
  - `confirm_import` manual override 顶层透传
- 导入主线相关本地验证在本窗口内已被用户反馈“全部通过”

### 当前阶段判断
- **导入模块 Phase B / core-safe 基线：已基本完成**
- **前端架构优化：A1 / A2 / A3 已完成**
- **A4 / A5：做过方案与替换文件，但是否已经最终稳定落到当前仓库，需要以下一个窗口先按当前真实文件快速复核**
- **整体系统主线还没结束**，后续要回到：
  1. 导入泛化验证
  2. recovery 独立证据
  3. gateMode / hard gate 设计口
  4. 利润配置体系
  5. 策略确认与后台推送闭环

---

## 1. 项目目标与边界（必须记住）

### 项目不是“单页导入工具”
这是一个**跨境电商运营系统**，整体目标是：

- Dashboard
- 数据导入 Import
- ABC 分析
- 价格竞争力
- 漏斗分析
- 库存预警
- 广告管理
- 策略清单
- 利润计算体系
- 批量决策
- 预测
- 确认后通过 API 推送销售后台
- 回写 / 审计 / 失败补偿

### 系统真正的主线
不是“页面差不多做完”，而是：

**导入可信 → 指标可信 → 策略可信 → 人工确认 → API 推送后台 → 结果回写 / 审计**

### 当前不能偏离的业务要求
1. **利润算法不能写死**
   - 可配置
   - 可人工修正
   - 多算法并存
   - SKU 级变量
   - 算法版本化
2. **系统不能只展示**
   - 还要支持批量决策、预测、确认后推送后台、结果回写
3. **当前优先级仍是导入主线**
   - 因为导入是整个系统可信性的入口

---

## 2. 仓库 / 本地 / 运行背景

### 仓库与目录
- GitHub 仓库：`LiYiHJ/Operation-system`
- 本地目录：`C:\Operation-system\System`
- 长期工作分支：`checkpoint/import-stable-51f7df8`

### 这轮里反复出现的现实问题
1. **Codex 环境无法稳定同步 GitHub**
   - 多次出现：
     - `CONNECT tunnel failed, response 403`
     - `git fetch` / `git push` 失败
   - 结论：后续不要再把“让 Codex 直接 push 到 GitHub”当默认流程

2. **补丁多次失配**
   - `.patch` / `.rej` 多次出现
   - 根因是：本地文件已处于“部分已改、部分未改”的中间态，统一 patch 锚点容易失效

3. **PowerShell 与命令差异**
   - `curl` 在 Windows PowerShell 里容易映射到 `Invoke-WebRequest`
   - 正确建议使用 `curl.exe`

4. **`vite preview` 必须先 `npm run build`**
   - 曾报错：`dist does not exist`

5. **测试环境不一定带 `pytest`**
   - 有一次明确报：`No module named pytest`
   - 当时通过 `python -m pip install pytest` 修复

---

## 3. 本窗口一开始的阶段锚点（来自历史文档）

### 文档锚点总结
早期阶段文档与交接报告的共识是：

- 当前系统最先推进的是**导入模块**
- 导入主线已经不是“简单上传文件”
- 已经形成：
  - dual-gate（结构 / 语义）
  - soft gate
  - bad-header recovery
  - runtime audit
- 当前阶段真正的问题不是服务起不来，而是：
  - 导入泛化验证仍不足
  - recovery 独立实证仍不足
  - 中文样本历史上更偏提交层 / importability 层问题
- 后续必须回到：
  - 导入泛化矩阵
  - recovery 独立证据
  - gateMode / hard gate 口子
  - 利润配置体系
  - 策略批量确认与推送闭环

---

## 4. 本窗口中真实做过的主要工作（按结果归纳）

### 4.1 导入主线 Phase B / core-safe 收口
本窗口内，围绕 `import_service.py`、`DataImportV2.tsx`、`frontend/src/types/index.ts` 做了长期收口，最后以**用户上传的当前真实代码**作为确认基线。

#### 最终应保留的导入主线结果
- `dynamicCompanion / excludeFromSemanticGate` 已接入前端与类型
- `isIgnoredField()` 已按新口径处理动态伴生/语义排除字段
- `buildDisplayStats()` 已按：
  - 默认优先信后端摘要
  - `hasManualEdits === true` 时才本地重算
- upload / confirm 调试 `console.log` 已删除
- `import_service.py` 内已形成共享摘要 helper：
  - `_build_field_mapping_summary`
- 顶层透出：
  - `mappedCount`
  - `unmappedCount`
  - `mappingCoverage`
  - `mappedConfidence`
  - `mappedCanonicalFields`
  - `topUnmappedHeaders`
- `confirm_import()` manual override 路径已对齐顶层摘要字段
- `candidatePreview` / bundle 消费来源已做统一

### 4.2 测试补齐
本窗口内曾针对导入主线补 3 类测试：

1. `tests/test_import_mapping_summary_contract.py`
   - 锁 `_build_field_mapping_summary`
   - 锁 `mappingCoverage / mappedConfidence`
   - 锁 `confirm_import` manual override 顶层摘要契约

2. `tests/test_import_api_contract_smoke.py`
   - 锁 `/api/import/upload`
   - 锁 `/api/import/confirm`
   - 锁顶层 mapping 摘要字段

3. `tests/test_import_phase_b_fixture_regression.py`
   - 锁 RU / 中文 / bad-header fixture regression

### 4.3 前端结构优化
#### A1：`App.tsx`
- 已改为 route-level lazy load / `Suspense`
- 这件事后期由用户上传的真实 `App.tsx` 证实为完成

#### A2：`DataImportV2.tsx`
- 从大页开始向结构化拆分推进
- 后期已生成 `data-import-v2` 子组件方案
- 用户上传的当前 `DataImportV2.tsx` 显示主页面已经不是最初的旧大页状态

#### A3：`frontend/src/types`
- 已拆分成：
  - `common.ts`
  - `dashboard.ts`
  - `import.ts`
  - `analysis.ts`
  - `strategy.ts`
  - `profit.ts`
  - `ads.ts`
  - `index.ts`

### 4.4 决策页与重复文件清理（提出并开始）
后期重点已转向：
- `DecisionEngine.tsx` 结构/类型收口
- `Dashboard_RealAPI.tsx`
- `ApiTest.tsx`
- `DataImport.tsx`
这些重复/过渡页面的清理

但这部分需要下个窗口先按当前真实文件快速复核，不应盲目假定已全部完成。

---

## 5. 本窗口里“已明确完成”的事项

### 明确完成（以下一窗口可以默认成立，但建议先快速 grep / build 验）
1. **App 路由 lazy-load**
2. **导入页 `dynamicCompanion / excludeFromSemanticGate / hasManualEdits`**
3. **导入后端 `_build_field_mapping_summary`**
4. **顶层 `mappingCoverage / mappedConfidence` 契约**
5. **导入相关测试补齐并本地通过**
6. **前端 types 分域拆分**

### 不能再重复做的事
1. 不要再重复给 `App.tsx` 做 A1
2. 不要再重复给 `DataImportV2.tsx` 做 Phase B 基线补丁
3. 不要再把旧版 `import_service.py` 当当前基线
4. 不要再默认让 Codex 直接 push 到 GitHub

---

## 6. 本窗口里发生过的坑（下个窗口必须避免）

### 6.1 关于 Codex / 远端同步
- 不要把“Codex 环境能直接 push GitHub”当默认假设
- 如果必须用 Codex，只让它：
  - 改代码
  - 跑测试
  - 给 commit hash / diff / 运行证明
- 真正 push，优先在用户本地环境做

### 6.2 关于 patch
- 不要再优先发统一 patch
- 当前仓库已反复处于“半改状态”
- 优先方案：
  - 直接替换文件
  - 或者用幂等脚本按当前文件内容定点改

### 6.3 关于目录与命令
- 在 `frontend` 目录里不要再 `cd frontend`
- `py_compile` 路径要从仓库根目录跑
- `vite preview` 之前必须 `npm run build`
- Windows 下尽量用 `curl.exe`

### 6.4 关于导入主线边界
- 当前主线不是利润 runtime
- 当前主线也不是重启大引擎实验
- 当前主线是：**收导入可信、补泛化证据、再往后半段走**

---

## 7. 你（下个窗口）接手时应优先读取的真实文件

以下文件以本窗口后半段用户上传的版本为准：

### 前端
- `frontend/src/App.tsx`
- `frontend/src/pages/DataImportV2.tsx`
- `frontend/src/pages/DecisionEngine.tsx`
- `frontend/src/pages/ABCAnalysis.tsx`
- `frontend/src/pages/AdsManagement.tsx`
- `frontend/src/pages/Dashboard.tsx`
- `frontend/src/types/index.ts`
- `frontend/src/types/common.ts`
- `frontend/src/types/dashboard.ts`
- `frontend/src/types/import.ts`
- `frontend/src/types/analysis.ts`
- `frontend/src/types/strategy.ts`
- `frontend/src/types/profit.ts`
- `frontend/src/types/ads.ts`

### 后端
- `src/ecom_v51/services/import_service.py`  
  > 注意：本窗口里上传过两个 `import_service.py`，下一个窗口必须明确以**当前 reconciled / 用户确认在用的版本**为准，不能拿旧简化版误当当前基线。
- `src/ecom_v51/services/dashboard_service.py`

---

## 8. 目前阶段到底在干什么

### 当前阶段
**导入模块已从“能上传文件”推进到“可信导入 + 前端结构化 + 契约化验证”的阶段。**

### 现在不是在干什么
- 不是在重做导入基础链路
- 不是在重新做 `App.tsx`
- 不是在继续试远端同步能力
- 不是在写大而全的新总结

### 现在真正该做什么
按阶段文档和本窗口现实进展，正确顺序是：

1. **先快速复核当前本地真实基线**
   - `App.tsx`
   - `DataImportV2.tsx`
   - `import_service.py`
   - `frontend/src/types/*`
   - 3 类导入测试
2. **补导入泛化验证矩阵**
3. **补 recovery 独立触发证据**
4. **设计 gateMode / hard gate 口子**
5. **进入利润配置体系设计**
6. **进入策略确认与后台推送闭环**
7. **最后做系统级生产化收口**

---

## 9. 整体完成度与阶段判断

### 工程判断（只用于内部，不对外宣传）
参考阶段文档的锚点：

- **导入模块：约 88%**
- **整系统：约 75%**

### 这是什么意思
#### 已经完成到什么程度
- 导入主链可运行
- dual-gate / soft-gate / recovery 已不是纸面设计
- 前后端导入摘要契约已补齐
- 前端入口和类型层已经开始结构化
- 本地 build / health / preview / 关键测试在本窗口内被反馈通过

#### 还没完成什么
- 不能说“导入整体已经完全稳定”
- 不能说“整系统已经完成”
- 不能说“利润引擎与策略推送闭环已经完成”

---

## 10. 对下一个窗口最重要的“源真相”规则

### 规则 1：以用户上传的当前真实文件为准
本窗口后半段已经证明：
- 公开视图、远端视图、Codex 本地视图可能不一致
- 用户上传的当前文件才是可直接接手的最可靠基线

### 规则 2：不要再重复已经完成的批次
以下批次视为已完成，不要再重做：
- A1（App 路由 lazy-load）
- A2（导入页前端主线收口）
- A3（types 分域拆分）
- 导入主线 Phase B / core-safe 契约

### 规则 3：不要直接拿大 patch 打
优先：
- 直接替换文件
- 或幂等脚本

---

## 11. 下一窗口建议的第一轮动作（最短闭环）

### 第一轮只做这 4 件事
1. 打开并确认：
   - `App.tsx`
   - `DataImportV2.tsx`
   - 当前在用的 `import_service.py`
   - `frontend/src/types/index.ts`
2. 跑：
   - `python -m py_compile src/ecom_v51/services/import_service.py`
   - `python -m pytest tests/test_import_mapping_summary_contract.py -q`
   - `python -m pytest tests/test_import_api_contract_smoke.py -q`
   - `python -m pytest tests/test_import_phase_b_fixture_regression.py -q`
   - `cd frontend && npm run build`
3. 明确仓库里是否还存在：
   - `Dashboard_RealAPI.tsx`
   - `ApiTest.tsx`
   - `DataImport.tsx`
4. 如果前三步都稳，再继续做：
   - `DecisionEngine.tsx` 收口
   - 删除重复/过渡页面
   - 导入泛化矩阵

---

## 12. 本窗口里用户已明确表达的工作方式偏好（下个窗口必须遵守）

1. 不要空口说“我看了仓库”，必须给能核对的文件/命令/输出
2. 不要再让用户一轮轮试一堆模糊方案
3. 优先给：
   - 直接替换文件
   - 或一键本地脚本
4. 不能再用“可能”“也许”敷衍当前真实代码状态
5. 在窗口卡顿时，要直接产出 handoff 文件，不要再延迟

---

## 13. 一句话交接

> **当前这条线已经从“导入能不能用”推进到了“导入契约已收、前端结构化已开始、可以转入泛化验证与后半段系统闭环”的阶段；下一个窗口不要再重做 App / DataImportV2 / import_service 基线，而应先复核当前真实文件，再继续做导入泛化、DecisionEngine 收口、重复页面清理、利润配置体系与策略推送闭环。**
