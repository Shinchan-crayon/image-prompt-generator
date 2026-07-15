# 审核与生图规则

## 适用边界

本文件只管理 Prompt 输出后的可选执行阶段。它不新增视觉模式，也不改变文章理解、构图、
风格、长度或质量评分规则。渠道详情见
[图片生成渠道](../knowledge/image_providers.md)。

## 审核门

严格按以下状态推进：

```text
Prompt 未展示
→ 禁止生图

Prompt 已展示，等待用户回复
→ 禁止生图

用户明确批准当前 Prompt
→ 允许检查配置并调用所选渠道
```

`批准`、`通过`、`可以生成`、`按这个生成`或语义完全等价的明确答复才算批准。预先授权、
沉默、含糊的“继续”以及看到 Prompt 前的“直接生成”都不算批准。

Prompt、主体、构图、比例、渠道、模型、尺寸或质量发生变化后，必须重新展示并重新批准。

## 渠道选择

用户未指定渠道时使用默认 ThinkAI。需要选择时，按固定顺序给出：

1. ThinkAI
2. 火山引擎 Seedream
3. OpenAI GPT Image
4. Google Nano Banana
5. 其他

正式渠道只让用户选择渠道并安全输入 API Key，不要求普通用户填写 URL 或模型 ID。
配置其他渠道不得改变默认 ThinkAI。

“其他”渠道由 Agent 先核对官方图片 API 文档并选择受支持协议。不能明确映射到
`openai-image-compatible` 或 `generic-sync-json-image` 时，直接说明当前不支持，不编写
临时代码绕过边界。

## 配置

所有凭据只写入当前 Skill 根目录的 `config.json`，不得读取其他 Skill。API Key 禁止放入
对话、命令参数、日志、快照或案例。

列出渠道：

```bash
python3 scripts/configure_provider.py --list
```

配置正式渠道：

```bash
python3 scripts/configure_provider.py thinkai
python3 scripts/configure_provider.py volcengine
python3 scripts/configure_provider.py openai
python3 scripts/configure_provider.py google
```

配置脚本使用隐藏输入。自动化环境只能通过标准输入：

```bash
printf '%s' "$IMAGE_API_KEY" | \
  python3 scripts/configure_provider.py <provider> --api-key-stdin
```

保留兼容入口：

```bash
python3 scripts/configure_api_key.py
```

该入口只配置默认 ThinkAI，并保留其他渠道配置。

“其他”渠道的完整命令由 Agent 根据官方文档构造，参数边界见
`knowledge/image_providers.md`。用户仍只在隐藏输入中填写 API Key。

## 本地预检

配置后先运行：

```bash
python3 scripts/provider_preflight.py --provider <provider>
```

预检不会联网，不会发送生成 POST，也不会产生费用。只有脚本返回 `verified-local` 才能
继续；该状态仅表示本地配置与适配器契约一致。

## 审核哈希

用户明确批准后，使用脚本计算，不要手工猜算：

```bash
python3 scripts/approval_hash.py \
  --provider <provider> \
  --prompt '<APPROVED_PROMPT>' \
  --size '<APPROVED_SIZE>' \
  --quality '<APPROVED_QUALITY>'
```

ThinkAI 为保持旧流程兼容，哈希只绑定精确 Prompt。其他渠道绑定 Prompt、渠道、实际模型、
规范化尺寸和质量参数。哈希只保护版本一致性，不能代替对话中的批准。

## 执行

默认 ThinkAI 可以省略 `--provider`：

```bash
python3 scripts/generate_image.py \
  --approved \
  --approval-hash '<APPROVAL_HASH>' \
  --prompt '<APPROVED_PROMPT>' \
  --size 1k \
  --quality hd
```

其他渠道必须显式传入已审核的渠道 ID：

```bash
python3 scripts/generate_image.py \
  --provider <provider> \
  --approved \
  --approval-hash '<APPROVAL_HASH>' \
  --prompt '<APPROVED_PROMPT>' \
  --size '<APPROVED_SIZE>' \
  --quality '<APPROVED_QUALITY>'
```

执行前告知用户当前渠道、模型、尺寸与质量，并提示实际计费以渠道后台为准。

## 失败处理

- 生成 POST 只发送一次，不会自动重试。
- 超时、断线、分块响应中断或结果不明确时，说明服务端可能已经受理并计费。
- 用户必须先检查所选渠道后台；只有确认后台没有成功任务并明确要求重发后，才能再次发送。
- URL 图片优先使用 Python URL 读取器；连接错误或数据不完整时使用系统 `curl`。
- 超长签名 URL 必须作为一个完整参数交给 `curl`，不能拆分，也不能写进临时配置文件。
- 响应快照移除 Base64 大字段和签名查询参数，不保存请求 Header。
- 输出必须是可识别的 PNG、JPEG 或 WebP，并从文件头读取实际尺寸。

脚本成功后以打印的 JSON 为准，报告：

- 当前渠道与模型
- 本地图片路径
- 请求尺寸与实际尺寸
- `request.json` 路径
- `response.json` 路径

未获得成功摘要或未生成完整文件时，不得宣称生图成功。
