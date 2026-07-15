# Image Prompt Generator

Image Prompt Generator 是一个面向各类文章的 Codex Plugin。它把文章理解、视觉规划、
封面设计、正文配图设计、Prompt 质检和已批准生图拆成一个总控 Skill 与五个专项 Skill，
同时共享同一套知识库、规则、模板、案例和图片渠道连接器。

## 六个 Skill

| Skill | 作用 |
|---|---|
| `image-prompt-generator` | 默认总控入口，管理完整流程、任务状态和人工审核门禁 |
| `article-visual-planner` | 理解文章，规划封面和必要的正文配图 |
| `cover-prompt-designer` | 设计具有编辑品质和标题留白的封面 Prompt |
| `section-illustration-designer` | 为指定标题、段落或章节设计解释型正文配图 Prompt |
| `image-prompt-reviewer` | 执行硬门槛、模型适配和九分质量审核 |
| `approved-image-generator` | 校验明确批准与版本哈希后执行单图或批量生图 |

通常使用 `$image-prompt-generator` 完成端到端工作。需要单独规划、设计、质检或执行已批准
图片时，也可以显式调用对应专项 Skill。

## 工作边界

插件只支持两种视觉模式：

- 封面模式：表达全文的一个核心观点。
- 正文配图模式：解释当前章节的一个关系、过程或变化。

整篇文章流程只是对两种模式的编排，不是第三种视觉模式。文章不局限于科技新闻，也可以是
商业、教育、医疗、政策、产品、教程、行业观察和其他具有明确内容结构的文章。

## 完整流程

```text
理解文章
→ 制定图片规划
→ 用户确认规划
→ 分别设计封面与正文 Prompt
→ 独立质量审核
→ 用户逐张审核 Prompt
→ 全部 Prompt 当前版本审核通过
→ 可选统一批量生图
→ 全部成功后交付
```

默认先交付 Prompt。用户看到当前 Prompt 并明确批准前，不会调用图片服务。任何 Prompt、
渠道、模型、尺寸或质量变化都会使旧批准失效。

## Prompt 语言

- 所有解释、规划与审核结论使用中文。
- GPT Image、Seedream 使用中文或中英混合 Prompt。
- Midjourney、Flux、Ideogram 使用英文 Prompt。
- 未知模型使用通用自然语言，不编造专用参数。

## 图片渠道

默认渠道为 ThinkAI Image 2。插件还支持 ThinkAI Nano、火山引擎 Seedream、OpenAI
GPT Image、Google Nano Banana 和符合受控同步协议的其他图片渠道。

只生成 Prompt 时无需配置 API Key。需要生图时，Agent 会让用户选择渠道，并通过隐藏输入
配置 API Key。配置保存在插件根目录的 `config.json`，不会进入发布包。

安装图片连接器依赖：

```bash
python3 -m pip install -r requirements.txt
```

列出和配置渠道：

```bash
python3 scripts/configure_provider.py --list
python3 scripts/configure_provider.py <provider>
python3 scripts/provider_preflight.py --provider <provider>
```

本地预检不会联网，也不能证明远端 API Key 有效。付费生成请求只发送一次；结果不确定时
不会自动重试。

## 共享结构

```text
image-prompt-generator/
├── .codex-plugin/plugin.json
├── AGENTS.md
├── README.md
├── references/
│   ├── knowledge/
│   ├── rules/
│   └── examples/
├── templates/
├── scripts/
│   └── providers/
├── assets/data/
├── skills/
│   ├── image-prompt-generator/
│   ├── article-visual-planner/
│   ├── cover-prompt-designer/
│   ├── section-illustration-designer/
│   ├── image-prompt-reviewer/
│   └── approved-image-generator/
├── config.example.json
└── requirements.txt
```

六个 Skill 只保留入口和 UI 元数据。共享知识库与运行代码只维护一份，避免规则漂移。
