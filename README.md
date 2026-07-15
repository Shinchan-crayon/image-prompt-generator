# Image Prompt Generator

![Image Prompt Generator Logo](plugins/image-prompt-generator/assets/logo.png)

Image Prompt Generator 是一个可从 GitHub 安装的 Codex Plugin，用于把各类文章转化为专业
封面与正文配图 Prompt。插件由一个总控 Skill、五个专项 Skill 和一套插件级共享知识库组成。

它先完成文章理解、图片规划、视觉设计和独立质检。只有全部 Prompt 的当前版本都展示给
用户并审核通过后，才允许调用已配置的图片渠道。

## 安装

把本仓库地址交给 Codex，要求添加并安装这个 marketplace；也可以在终端执行：

```bash
codex plugin marketplace add https://github.com/Shinchan-crayon/image-prompt-generator.git
```

然后在 Codex 插件页面安装 **Image Prompt Generator**，并在新任务中使用。

## 六个 Skill

- `$image-prompt-generator`：默认总控入口，管理完整工作流和人工审核门禁。
- `$article-visual-planner`：理解文章并规划封面与正文配图。
- `$cover-prompt-designer`：设计封面 Prompt。
- `$section-illustration-designer`：设计指定章节的正文配图 Prompt。
- `$image-prompt-reviewer`：执行硬门槛和九分质量审核。
- `$approved-image-generator`：只生成已明确批准且版本哈希一致的图片。

通常只需要调用 `$image-prompt-generator`。专项 Skill 适合需要单独规划、设计、质检或执行
已批准生图的用户。

## 使用

```text
使用 $image-prompt-generator，为这篇文章规划封面和正文配图。
先让我确认图片规划，全部 Prompt 审核通过后再统一生图。
```

```text
使用 $cover-prompt-designer，为这篇文章设计 16:9 封面 Prompt，
目标模型为 Midjourney。
```

```text
使用 $section-illustration-designer，为这个章节设计 4:3 解释型配图 Prompt，
目标模型为 Seedream。
```

插件只支持封面模式和正文配图模式。整篇文章流程是两种模式之上的编排层，不是第三种模式。

## 图片渠道

只生成 Prompt 时无需 API Key。需要生图时支持：

- ThinkAI Image 2，默认
- ThinkAI Nano
- 火山引擎 Seedream
- OpenAI GPT Image
- Google Nano Banana
- 符合受控同步协议的其他图片渠道

Agent 会让用户选择渠道，并通过隐藏输入配置 API Key。付费请求结果不确定时不会自动重试。

## 仓库结构

```text
image-prompt-generator/
├── .agents/plugins/marketplace.json
├── plugins/image-prompt-generator/
│   ├── .codex-plugin/plugin.json
│   ├── README.md
│   ├── AGENTS.md
│   ├── references/
│   │   ├── knowledge/
│   │   ├── rules/
│   │   └── examples/
│   ├── templates/
│   ├── scripts/
│   ├── assets/data/
│   └── skills/
│       ├── image-prompt-generator/
│       ├── article-visual-planner/
│       ├── cover-prompt-designer/
│       ├── section-illustration-designer/
│       ├── image-prompt-reviewer/
│       └── approved-image-generator/
└── README.md
```

共享知识库、规则、模板、案例和连接器只维护一份；六个 Skill 只保留各自入口与 UI 元数据。

## 验证

```bash
python3 plugins/image-prompt-generator/scripts/check_skill.py
python3 ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py \
  plugins/image-prompt-generator
```
