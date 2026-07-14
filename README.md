# Image Prompt Generator

一个面向 Codex 的可安装 Skill，用于把科技新闻、AI 行业分析、产品评测、商业洞察、
教程和教育内容转化为专业图片提示词。

它先生成并展示提示词；用户明确审核通过后，可通过内置独立 ThinkAI 连接器生成图片。
连接器使用当前 Skill 自己的配置，不读取其他 Skill 的凭据或脚本。

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
- 内置 ThinkAI `gpt-image-2` 连接器，并通过显式审核门阻止未批准生图。
- API Key 通过隐藏输入保存到本 Skill 自己的 `config.json`，权限为 `0600`。
- 生图命令校验批准 Prompt 的 SHA-256，修改 Prompt 后必须重新审核。
- 生图请求采用明确超时和瞬时错误重试，图片下载提供独立兜底。
- 生成请求对瞬时连接错误和可重试 HTTP 状态最多尝试三次。
- 图片下载发生连接错误或数据不完整时使用系统 `curl` 兜底。

## 安装

将本目录放入 Codex 的 Skills 目录，并保持目录名为 `image-prompt-generator`：

```text
~/.codex/skills/image-prompt-generator/
```

安装 ThinkAI 生图所需的 Python 依赖：

```bash
cd ~/.codex/skills/image-prompt-generator
python3 -m pip install -r requirements.txt
```

只使用 Prompt 生成功能时不需要安装该依赖；调用 ThinkAI 生图前必须完成安装。

使用示例：

```text
使用 $image-prompt-generator，为下面这篇文章生成 16:9 封面提示词，
目标模型为 Midjourney。
```

```text
使用 $image-prompt-generator，为下面章节生成 4:3 正文配图提示词，
目标模型为 Seedream。
```

## 配置 ThinkAI

只需配置一次 API Key：

```bash
cd ~/.codex/skills/image-prompt-generator
python3 -m pip install -r requirements.txt
python3 scripts/configure_api_key.py
```

脚本会隐藏输入内容。自动化环境可通过标准输入配置：

```bash
printf '%s' "$THINKAI_API_KEY" | python3 scripts/configure_api_key.py --api-key-stdin
```

不要把 API Key 写在命令参数中，以免进入 shell 历史或进程列表。

连接器固定使用：

- API：`https://www.thinkai.tv/v1/images/generations`
- 模型：`gpt-image-2`
- `1k`：`1920x1088`
- `2k`：`2560x1440`

实际计费以 ThinkAI 后台为准。`config.json` 不会被提交；默认生成结果保存在
`generated/<时间戳>/`。

生成请求通过 `requests` 发送，对瞬时错误最多尝试三次；图片优先通过 Python URL 读取器
下载，连接错误或数据不完整时使用系统 `curl` 兜底。API Key 只从当前 Skill 的本地配置
读取，不写入请求快照或用户回复。

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
├── scripts/
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
→ 明确批准后可选调用 ThinkAI
→ 保存图片、请求与响应记录
```

运行时先读取固定规则，再按分类、意图和情绪定点加载知识。案例库只在需要校准时通过
索引检索少量相似案例，不作为固定模板。

## 审核机制

Skill 每次都先输出完整视觉方案和 Prompt，然后停止并等待用户质检。只有用户看到当前
Prompt 后明确回复“批准”“通过”“可以生成”等同意语句，才允许执行生图。

即使用户最初要求“直接生成”，也必须先展示 Prompt；任何 Prompt 修改都会使之前的批准
失效。生成脚本还要求显式传入 `--approved` 和当前 Prompt 的 `--approval-hash`，用于阻止
误把未审核的新版本送去生成。哈希是版本一致性保护，不代表脚本能够证明用户真实同意；
对话中的审核门仍是第一道约束。

## 当前边界

- 只支持封面模式和正文配图模式。
- ThinkAI 生图是两种模式的可选后续阶段，不是第三种模式。
- 不支持图片编辑、批量生图或绕过审核。
- 不会读取或复用其他 Skill 的 API Key、配置或脚本。

## 自检

需要确认安装结构和关键规则是否完整时运行：

```bash
python3 scripts/check_skill.py
```

扩展模型、文章类型、视觉方法或案例时，遵循 `knowledge/extension_guide.md`，不要把完整
知识库重新塞入 `SKILL.md`。
