# Image Prompt Generator

一个面向 Codex 的可安装 Skill，用于把科技新闻、AI 行业分析、产品评测、商业洞察、
教程和教育内容转化为专业图片提示词。

它先生成并展示提示词；用户明确审核通过后，可通过内置连接器生成图片。ThinkAI 保持
默认渠道，也支持火山引擎 Seedream、OpenAI GPT Image、Google Nano Banana 和受控的
其他同步图片接口。连接器只使用当前 Skill 的配置，不读取其他 Skill 的凭据或脚本。

## 两种模式

- **封面模式**：读取完整文章，提炼一个核心观点，设计具有科技媒体编辑品质的封面视觉。
- **正文配图模式**：读取标题、段落或章节，生成帮助读者理解概念、关系、过程或变化的配图提示词。

## 核心特点

- 先理解观点，再设计画面，最后生成 Prompt。
- 使用文章理解卡区分事实、作者意图、推断和未知信息。
- 通过文章分类、写作意图、主情绪和视觉策略知识库完成决策。
- 默认采用“真实摄影 + 具体场景 + 动作 + 光线 + 适配色调”。
- 中文 Prompt 控制在 50–60 个汉字，英文 Prompt 控制在 35–45 个单词。
- 根据 GPT Image、Midjourney、Flux、Seedream、Ideogram 自动调整 Prompt 语言。
- 所有分析和说明默认使用中文。
- 强制单一核心信息、明确视觉焦点和标题安全区。
- 使用硬门槛与 10 分质量评分，低于 9 分重新设计。
- 内置 100 个覆盖两种模式和五类目标模型的校准案例。
- 将知识、规则、模板和案例拆分维护，便于持续扩展。
- 提供 5 个渠道入口：ThinkAI、火山引擎、OpenAI、Google、其他。
- 正式渠道只需选择渠道并安全输入 API Key，不要求普通用户填写 URL 或模型 ID。
- API Key 通过隐藏输入保存到本 Skill 自己的 `config.json`，权限为 `0600`。
- 生图命令校验审核哈希；非 ThinkAI 渠道还绑定渠道、模型、尺寸与质量。
- 付费生图 POST 只发送一次；结果不确定时不会自动重试，避免后台已受理却重复扣费。
- 用户确认所选渠道后台没有成功任务并明确要求重发后，才能再次发送生成请求。
- 图片下载发生连接错误或数据不完整时使用系统 `curl` 兜底。

## 安装

将本目录放入 Codex 的 Skills 目录，并保持目录名为 `image-prompt-generator`：

```text
~/.codex/skills/image-prompt-generator/
```

安装生图连接器所需的 Python 依赖：

```bash
cd ~/.codex/skills/image-prompt-generator
python3 -m pip install -r requirements.txt
```

只使用 Prompt 生成功能时不需要安装该依赖；调用任一生图渠道前必须完成安装。

使用示例：

```text
使用 $image-prompt-generator，为下面这篇文章生成 16:9 封面提示词，
目标模型为 Midjourney。
```

```text
使用 $image-prompt-generator，为下面章节生成 4:3 正文配图提示词，
目标模型为 Seedream。
```

## 配置图片渠道

列出固定的 5 个入口：

```bash
cd ~/.codex/skills/image-prompt-generator
python3 scripts/configure_provider.py --list
```

配置任一正式渠道：

```bash
python3 scripts/configure_provider.py thinkai
python3 scripts/configure_provider.py volcengine
python3 scripts/configure_provider.py openai
python3 scripts/configure_provider.py google
```

脚本会隐藏 API Key。正式渠道的地址、推荐模型和默认尺寸由注册表维护，用户不需要填写。
兼容旧版 ThinkAI 的入口仍然可用：

```bash
python3 scripts/configure_api_key.py
```

自动化环境只能通过标准输入传 Key：

```bash
printf '%s' "$IMAGE_API_KEY" | \
  python3 scripts/configure_provider.py <provider> --api-key-stdin
```

不要把 API Key 写在命令参数或对话中。配置完成后运行纯本地预检：

```bash
python3 scripts/provider_preflight.py --provider <provider>
```

`verified-local` 只表示本地配置和请求结构通过，不代表已经调用服务端。

“其他”渠道由 Agent 先核对官方图片 API 文档，只在能映射到受控同步 JSON 协议时配置；
用户仍只需在隐藏输入中填写 API Key。异步轮询、任意代码、图片编辑和视频接口不在支持
范围内。Seedance 是视频模型，不属于本 Skill。

配置其他渠道不会改变默认 ThinkAI。`config.json` 不会被提交；生成结果保存在
`generated/<时间戳>/`。

## 目录

```text
image-prompt-generator/
├── SKILL.md
├── AGENTS.md
├── README.md
├── agents/
├── knowledge/
├── rules/
├── templates/
├── examples/
├── data/
├── scripts/
│   └── providers/
├── requirements.txt
├── config.example.json
└── .gitignore
```

## 工作机制

```text
输入文章
→ 文章理解卡
→ 分类、意图、情绪
→ 单一核心观点
→ 视觉策略与现实场景
→ 构图、光线、色彩与留白
→ 模型语言适配
→ 50–60 汉字或 35–45 英文单词 Prompt
→ 硬门槛与 9 分质量线
→ 展示 Prompt 并等待用户审核
→ 明确批准后调用默认 ThinkAI 或用户显式选择的渠道
→ 保存图片、请求与响应记录
```

运行时先读取固定规则，再按分类、意图和情绪定点加载知识。案例库只在需要校准时通过
索引检索少量相似案例，不作为固定模板。

## 审核机制

Skill 每次都先输出完整视觉方案和 Prompt，然后停止并等待用户质检。只有用户看到当前
Prompt 后明确回复“批准”“通过”“可以生成”等同意语句，才允许执行生图。

即使用户最初要求“直接生成”，也必须先展示 Prompt；任何 Prompt 修改都会使之前的批准
失效。生成脚本还要求显式传入 `--approved` 和当前执行版本的 `--approval-hash`，用于
阻止误把未审核的新版本送去生成。使用 `scripts/approval_hash.py` 计算哈希，不要手工
猜算。哈希是版本一致性保护，不代表脚本能够证明用户真实同意；对话审核门仍是第一道约束。

## 当前边界

- 只支持封面模式和正文配图模式。
- 图片渠道生图是两种模式的可选后续阶段，不是第三种模式。
- 不支持图片编辑、批量生图或绕过审核。
- 不会读取或复用其他 Skill 的 API Key、配置或脚本。
- 未指定渠道时始终使用 ThinkAI；配置其他渠道不会自动切换默认值。
- “其他”只支持受控同步 JSON 图片协议。

## 自检

需要确认安装结构和关键规则是否完整时运行：

```bash
python3 scripts/check_skill.py
```

扩展模型、文章类型、视觉方法或案例时，遵循 `knowledge/extension_guide.md`，不要把完整
知识库重新塞入 `SKILL.md`。
