# 111.patch 同步 GitHub 操作步骤

## 1) 先备份当前工作区

```bash
git status --short
git branch backup/pre-111-patch-$(date +%Y%m%d-%H%M%S)
```

## 2) 放入清洗后的补丁

把 `111_clean.patch` 放到仓库根目录同级，或任意你方便的位置。

## 3) 先检查补丁是否可应用

```bash
git apply --check /path/to/111_clean.patch
```

若报上下文冲突，再用三方合并：

```bash
git apply --3way --check /path/to/111_clean.patch
```

## 4) 应用补丁

```bash
git apply --3way /path/to/111_clean.patch
```

## 5) 丢弃不应提交的数据库文件

```bash
git restore -- System/data/ecom_v51.db 2>/dev/null || true
```

若产生 uploads 运行文件，也不要提交：

```bash
git restore --staged System/src/uploads 2>/dev/null || true
git restore --worktree System/src/uploads 2>/dev/null || true
```

## 6) 检查本次改动

```bash
git status --short
```

## 7) 分批提交（推荐）

### 7.1 核心代码与配置

```bash
git add \
  System/config/field_aliases_zh_ru_en.yaml \
  System/config/import_field_registry.json \
  System/src/ecom_v51/api/app.py \
  System/src/ecom_v51/api/routes/ads.py \
  System/src/ecom_v51/api/routes/analysis.py \
  System/src/ecom_v51/api/routes/dashboard.py \
  System/src/ecom_v51/api/routes/import_route.py \
  System/src/ecom_v51/api/routes/strategy.py \
  System/src/ecom_v51/db/models.py \
  System/src/ecom_v51/intelligent_field_mapper.py \
  System/src/ecom_v51/services/analysis_service.py \
  System/src/ecom_v51/services/import_service.py \
  System/src/ecom_v51/services/integration_service.py \
  System/src/ecom_v51/services/strategy_service.py

git commit -m "feat: apply import recovery and semantic gate patch"
```

### 7.2 前端与契约

```bash
git add \
  System/frontend/README_FRONTEND.md \
  System/frontend/src/App.tsx \
  System/frontend/src/pages/DataImport.tsx \
  System/frontend/src/pages/DataImport/index.tsx \
  System/frontend/src/pages/DataImportV2.tsx \
  System/frontend/src/pages/DecisionEngine.tsx \
  System/frontend/src/pages/PriceCompetitiveness.tsx \
  System/frontend/src/pages/StrategyList.tsx \
  System/frontend/src/pages/SystemSettings.tsx \
  System/frontend/src/services/api.ts \
  System/frontend/src/types/index.ts

git commit -m "feat: update frontend import runtime visibility and related pages"
```

### 7.3 文档与验证产物

```bash
git add System/docs System/scripts/non_zero_gate_check.py System/sample_data/p0_csv_scene_from_cn.csv

git commit -m "docs: add runtime validation evidence and readiness artifacts"
```

## 8) 推送

```bash
git push origin main
```

## 9) 推送后立即复核

```bash
git rev-parse --short HEAD
git status --short
```

然后打开 GitHub 上至少核对这几个文件是否恢复正常格式：

- `System/src/ecom_v51/services/import_service.py`
- `System/frontend/src/pages/DataImportV2.tsx`
- `System/frontend/src/types/index.ts`
- `System/frontend/src/services/api.ts`
- `System/src/ecom_v51/api/routes/import_route.py`

