---
name: approved-image-generator
description: Use when generating images only from explicitly approved prompt packages, after validating approval hashes, provider configuration, model, size, quality, batch readiness, and unchanged execution conditions.
---

# 已批准图片生成器

## 职责

只执行已经通过质量审核并由用户明确批准的图片。支持单图和整篇文章批次，但不负责文章
理解、视觉设计或 Prompt 审核。

## 输入

```yaml
approved_items: 已明确批准的单图或文章项目列表
provider: 渠道 ID，未指定时为 thinkai-image2
model: 实际模型
size_or_ratio: 已批准的尺寸或比例
quality: 已批准的质量参数
approval_hashes: 每个当前 Prompt 与执行条件对应的审核哈希
max_workers: 每批图片数量与并发上限，默认 3
```

直接调用本 Skill 时，调用者也必须提供可核验的明确批准记录，不能依赖“用户大概同意”。

## 必读资源

1. [审核与生图](../../references/rules/generation_workflow.md)
2. [批量生成](../../references/rules/batch_generation.md)
3. [图片渠道](../../references/knowledge/image_providers.md)
4. [文章工作流](../../references/rules/article_workflow.md)

只使用插件级共享脚本：

- [渠道配置](../../scripts/configure_provider.py)
- [本地预检](../../scripts/provider_preflight.py)
- [审核哈希](../../scripts/approval_hash.py)
- [单图生成](../../scripts/generate_image.py)
- [文章工作流](../../scripts/article_workflow.py)

## 执行门禁

1. 验证每项当前 Prompt 已展示且获得用户明确批准。
2. 验证 `$image-prompt-reviewer` 的当前版本结果为 `PASS`。
3. 重新计算 approval hash，校验 Prompt、渠道、模型、尺寸和质量没有变化。
4. 运行纯本地预检；`verified-local` 只表示本地配置有效，不代表远端认证成功。
5. 任一项目缺少批准、哈希不匹配或执行条件变化，立即拒绝，不局部放行。
6. 单图调用 `generate_image.py`，必须同时传入 `--approved` 与匹配的
   `--approval-hash`。
7. 文章批次必须确认所有当前 Prompt 均已批准，再使用：

```bash
python3 ../../scripts/article_workflow.py generate \
  --run '<RUN_ID>' \
  --execute \
  --max-workers 3
```

`max_workers` 可在 1–3 内显式调整，默认每批三张。文章图片严格按固定批次生成，例如
`1–3`、`4–6`、`7–9`；当前批次全部成功后才提交下一批，不得在当前批次空出并发槽位时
滚动补入下一批。

## 风险控制

- 每个付费 POST 只发送一次，不自动重试。
- 超时、断线、响应解析失败或下载中断视为结果不确定；等待当前批次已发送请求结束并记录
  状态，但不得提交后续批次。
- 结果不确定时要求用户检查渠道后台；确认没有成功任务并明确批准重发后才可重试。
- 恢复批次时读取真实状态，跳过已经生成成功的项目。
- 全部图片成功前不得创建正式交付包。
- 不输出或记录 API Key，不读取其他插件或 Skill 的配置。

## 输出

成功时报告渠道、模型、本地图片路径、请求尺寸、实际尺寸和快照路径。文章批次全部成功后，
通过 `article_workflow.py deliver` 创建统一交付包。没有完整成功摘要时不得宣称成功。

## 边界

- 不得生成或修改 Prompt。
- 不得把质量审核 `PASS` 当成人工批准。
- 不得绕过 approval hash、全量批准门禁或结果不确定阻断。
