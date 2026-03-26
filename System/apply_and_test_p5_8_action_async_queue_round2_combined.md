# apply_and_test_p5_8_action_async_queue_round2_combined

## 本轮交付
- patch_bundle_20260325_p5_8_action_async_queue_round2_patch_singlelayer.zip

## 改动目标
- 在 P5.8 Round 1 已通过的 async push / jobId 基线之上，补齐 callback / compensation -> action job timeline。
- 新增 request -> jobs 查询面：`GET /api/v1/actions/requests/{requestId}/jobs`。
- 保持当前 `/api/v1/jobs/{jobId}`、`/events` 与既有 P5.2 / P5.7 contract 兼容。

## 本轮不做
- 不引入真实队列中间件 / worker 进程。
- 不做 bulk automation。
- 不做前端正式 action job tracking 页面。

## 下载与覆盖
```powershell
$zip  = "D:/A浏览器下载/下载/patch_bundle_20260325_p5_8_action_async_queue_round2_patch_singlelayer.zip"
$temp = "D:/A浏览器下载/下载/patch_bundle_20260325_p5_8_action_async_queue_round2_patch_singlelayer"

Remove-Item $temp -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive -LiteralPath $zip -DestinationPath $temp -Force
Copy-Item "$temp/System/*" "C:/Operation-system/System" -Recurse -Force
```

## 定向测试
```powershell
pytest -q System/tests/services/test_p5_8_action_queue_service.py
pytest -q System/tests/api/test_p5_8_v1_action_async_push_contract.py
pytest -q System/tests/api/test_p5_8_v1_action_request_jobs_contract.py
```

## 全量回归
```powershell
pytest -q
```

## 导出 diff
```powershell
git diff --stat > p5_8_action_async_queue_round2_git_diff_stat_20260325.txt
git diff > p5_8_action_async_queue_round2_git_diff_20260325.patch
```

## 需要回传的文件
- 定向测试输出
- 全量 pytest 输出
- `p5_8_action_async_queue_round2_git_diff_stat_20260325.txt`
- `p5_8_action_async_queue_round2_git_diff_20260325.patch`

## 验收口径
- `push` 继续返回 `202 + jobId + queueStatus=queued`。
- `GET /api/v1/actions/requests/{requestId}/jobs` 能返回对应动作作业。
- 回调写入后，`GET /api/v1/jobs/{jobId}/events` 包含 `callback_received`。
- 补偿评估后，`GET /api/v1/jobs/{jobId}/events` 包含 `compensation_evaluated`。
- 不破坏现有全量 pytest 基线。
