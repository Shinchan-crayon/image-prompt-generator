# Image Prompt Generator

![Image Prompt Generator Logo](plugins/image-prompt-generator/assets/logo.png)

一个可从 GitHub 安装的 Codex Plugin，用于把科技新闻、AI 行业分析、产品评测、商业洞察、
教程和教育内容转化为专业封面与正文配图 Prompt。

插件先理解文章、提炼单一核心观点并设计视觉方案。Prompt 完整展示并经用户明确批准后，
才允许调用已配置的图片渠道。默认渠道为 ThinkAI Image 2，也支持 ThinkAI Nano、火山
引擎 Seedream、OpenAI GPT Image、Google Nano Banana 和受控的其他同步图片接口。

## 从 GitHub 安装

在终端添加本仓库提供的 marketplace：

```bash
codex plugin marketplace add Shinchan-crayon/image-prompt-generator
```

重启 Codex 桌面应用，打开插件页面，选择 **Image Prompt Generator** marketplace，然后
安装同名插件。插件页面会显示本仓库提供的名称、Logo、简介和示例指令。

也可以使用完整 Git 地址：

```bash
codex plugin marketplace add https://github.com/Shinchan-crayon/image-prompt-generator.git
```

## 使用

安装后在新任务中调用：

```text
使用 $image-prompt-generator，为下面这篇文章生成 16:9 封面提示词，
目标模型为 Midjourney。
```

```text
使用 $image-prompt-generator，为整篇文章规划封面和正文配图。
全部 Prompt 审核通过后，再统一生图。
```

插件只支持封面模式和正文配图模式；文章级工作流是两种模式之上的规划、审核和批量执行层。

## 图片渠道

只生成 Prompt 时不需要安装额外依赖或配置 API Key。首次调用图片渠道时，Agent 会在插件
内安装 `requirements.txt` 中的 Python 依赖，并通过隐藏输入引导配置所选渠道的 API Key。
API Key 不应放入对话、命令参数、案例或仓库。

支持的渠道：

- ThinkAI Image 2，默认
- ThinkAI Nano
- 火山引擎 Seedream
- OpenAI GPT Image
- Google Nano Banana
- 受控的其他同步图片接口

## 仓库结构

```text
image-prompt-generator/
├── .agents/plugins/marketplace.json
├── plugins/
│   └── image-prompt-generator/
│       ├── .codex-plugin/plugin.json
│       ├── assets/
│       └── skills/
│           └── image-prompt-generator/
│               ├── SKILL.md
│               ├── AGENTS.md
│               ├── knowledge/
│               ├── rules/
│               ├── templates/
│               ├── examples/
│               ├── data/
│               └── scripts/
├── README.md
└── .gitignore
```

插件 manifest 只负责安装、发现与展示；完整运行逻辑仍由插件内唯一的
`image-prompt-generator` Skill 管理。

## 本地验证

验证原生插件结构：

```bash
python3 ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py \
  plugins/image-prompt-generator
```

验证内置 Skill：

```bash
cd plugins/image-prompt-generator/skills/image-prompt-generator
python3 scripts/check_skill.py
```
