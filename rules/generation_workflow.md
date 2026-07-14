# ThinkAI 审核与生图规则

## 适用边界

本文件只管理 Prompt 输出后的可选执行阶段。它不新增视觉模式，不改变文章理解、构图、
风格、长度或质量评分规则。

## 审核门

严格按以下状态推进：

```text
Prompt 未展示
→ 禁止生图

Prompt 已展示，等待用户回复
→ 禁止生图

用户明确批准当前 Prompt
→ 允许检查配置并调用 ThinkAI
```

以下回复可视为批准：`批准`、`通过`、`可以生成`、`按这个生成`、语义完全等价的明确同意。

以下情况不算批准：

- 用户在看到最终 Prompt 前要求“一步完成”或“直接生成”。
- 用户只说“继续”“看看”“试试”，但没有指向当前 Prompt。
- 用户修改了 Prompt、比例、主体、风格或其他画面条件。
- 当前展示的是旧 Prompt，之后已发生重新设计。

只要 Prompt 或画面条件发生变化，就必须重新展示并重新等待批准。

批准后为用户看到的精确 Prompt 计算 SHA-256。哈希只用于检查执行版本与审核版本是否一致，
不能替代对话中的明确批准。任何字符变化都会使旧哈希失效。

## 固定连接器契约

- API：`POST https://www.thinkai.tv/v1/images/generations`
- 模型：`gpt-image-2`
- `1k`：`1920x1088`
- `2k`：`2560x1440`
- 默认质量：`hd`
- 默认数量：`1`
- 返回格式：`url`

执行前告知用户：

`当前使用 ThinkAI gpt-image-2，可生成 1k、2k 图片，实际计费以 ThinkAI 后台为准。`

不猜测其他尺寸、模型、价格或服务能力。

## 配置

只使用当前 Skill 根目录的 `config.json`。若缺失或 `api_key` 为空，询问用户提供 API Key，
然后运行：

```bash
python3 scripts/configure_api_key.py
```

脚本默认隐藏输入。自动化环境只能通过标准输入运行：

```bash
printf '%s' "$THINKAI_API_KEY" | python3 scripts/configure_api_key.py --api-key-stdin
```

禁止读取其他 Skill 的配置文件。禁止把 API Key 放入命令参数、日志、请求快照、回复或
案例库。配置脚本必须使用仅当前用户可读写的临时文件和原子替换。

## 执行

用户批准后运行：

```bash
python3 scripts/generate_image.py \
  --approved \
  --approval-hash '<APPROVED_PROMPT_SHA256>' \
  --prompt '<APPROVED_PROMPT>' \
  --size 1k \
  --quality hd
```

必须原样使用用户批准的最终 Prompt。若需要修改 Prompt，回到审核阶段。

安全约束：

- `--approval-hash` 必须对应用户看到并批准的精确 Prompt。
- ThinkAI 地址固定为 `https://www.thinkai.tv/v1`，模型固定为 `gpt-image-2`；配置被篡改
  时停止执行。
- 生成请求使用 `requests`、明确的连接与读取超时，以及瞬时错误重试规则，最多尝试三次。
- API Key 仅从本 Skill 权限为 `0600` 的 `config.json` 读取，不写入命令参数、日志、请求
  快照或用户回复。
- ThinkAI 返回内容必须是完整 JSON，并包含 `data[0].url`；结构不符合时停止执行。
- 图片优先使用 Python URL 读取器，它可直接处理 ThinkAI 返回的
  `data:image/png;base64,...`，也可读取普通 HTTP 图片地址。
- HTTP 图片读取发生连接错误或数据不完整时，使用系统 `curl` 兜底。
- 图片必须具有有效 PNG 文件头，并从 PNG 头部读取实际尺寸。
- 输出目录固定在本 Skill 的 `generated/`，不向命令行开放任意输出路径。

脚本成功后，以打印的 JSON 为准，向用户报告：

- 本地图片路径
- 请求尺寸与实际尺寸
- `request.json` 路径
- `response.json` 路径

未获得脚本成功摘要或未生成完整文件时，不得宣称生图成功。
