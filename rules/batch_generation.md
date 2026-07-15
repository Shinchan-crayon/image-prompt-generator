# 文章批量生成规则

## 全量批准门禁

批量生成前必须同时满足：

1. 图片规划已经明确确认。
2. 每个未删除项目都有完整 Prompt 文件。
3. 每个 Prompt 的当前版本均已逐张批准。
4. 渠道、实际模型、尺寸和质量与批准版本一致。
5. 所选渠道通过本地预检。

任一条件不满足，脚本必须拒绝执行。不得使用规划批准、预先授权或最后一张 Prompt 的批准
替代其他图片的逐张批准。

## 执行方式

批量表示统一触发、按规划顺序逐张执行，不表示并行请求：

```bash
python3 scripts/article_workflow.py generate \
  --run '<RUN_ID>' \
  --execute
```

同一任务同时只能有一个生成执行器。第二个并发调用必须直接拒绝，不得等待后再次发送，
也不得与第一个执行器共同推进状态。

顺序固定为封面在前，正文配图按规划顺序执行。每张成功后立即保存本地路径和状态。恢复时
跳过所有已经成功的图片，不重复调用付费接口。

发送付费请求前先记录 `sending`。如果进程中断后恢复时仍发现 `sending`，必须将该项目
视为 `uncertain` 并停止，不得直接重发。

## 失败与结果不确定

- 明确失败：记录 `failed` 并停止整批，不自动发送下一张。
- 超时、断线、响应无法解析或生成后下载失败：记录 `uncertain` 并停止整批。
- 失败或结果不确定时不得自动重试付费生成请求。
- `failed` 项目只有在用户明确批准重试后才能重置。
- `uncertain` 项目必须先检查渠道后台，确认不存在成功任务后，才能批准重发。
- 批准重发时必须先清除该项目上一轮的不完整产物，防止恢复流程误接纳旧文件。

```bash
python3 scripts/article_workflow.py retry-item \
  --run '<RUN_ID>' \
  --item '<ITEM_ID>' \
  --approved
```

结果不确定时还必须传入：

```text
--backend-checked
```

重置后再次运行 `generate --execute`。脚本会跳过此前已成功项目。

如果中断前已经在 `artifacts/<ITEM_ID>/` 写入一张完整图片以及 `request.json`、
`response.json`，用户检查渠道后台并明确同意接纳后，可以执行：

```bash
python3 scripts/article_workflow.py resolve-item \
  --run '<RUN_ID>' \
  --item '<ITEM_ID>' \
  --backend-checked \
  --approved
```

脚本只接受任务目录内唯一且可识别的 PNG、JPEG 或 WebP，拒绝符号链接，并验证两份 JSON
快照。`request.json` 必须与当前已审核 Prompt、渠道、模型、尺寸和质量生成的请求体一致；
产物不完整或审核版本不匹配时保持阻塞，不得伪造成功状态。

## 正式交付

只有全部未删除项目均生成成功后，才能执行：

```bash
python3 scripts/article_workflow.py deliver --run '<RUN_ID>'
```

正式交付包含按顺序命名的图片、`image-map.md`、`prompts.md` 和 `manifest.json`。任务未
完成时只保留 `artifacts/` 过程产物，不创建看似完整的交付包。交付前必须校验每张图片
与生成完成时记录的 SHA-256 一致；图片被替换、缺少哈希或内容变化时拒绝交付。
