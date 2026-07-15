---
name: image-prompt-generator
description: Use when converting technology news, AI industry analysis, product reviews, business insights, tutorials, or educational content into a cover, section illustration, or reviewed multi-image article workflow, including optional generation through bundled image provider connectors.
---

# Image Prompt Generator

## 概述

把文章转化为专业图片提示词，并可在用户审核通过后通过内置图片渠道连接器生成图片。
默认任务止于 Prompt 审核，不自动调用图片模型，也不提供图片编辑能力。

核心流程是：理解文章 → 提炼一个观点 → 选择视觉策略 → 设计现实场景 → 生成 Prompt。
禁止抽取关键词后直接拼接 Prompt。

## 支持范围

只支持两种模式：

1. **封面模式**：根据完整文章生成表达核心观点的科技媒体封面提示词。
2. **正文配图模式**：根据大纲、标题、段落或章节生成解释当前内容的配图提示词。

新闻、评测、教程、信息图、杂志风格等只是分类、意图或视觉策略，不是新增模式。
不得扩展为图片编辑、文章写作或品牌资产管理工具。文章级多图工作流只是对两种模式进行
规划、逐图审核和统一执行的编排层，不是第三种视觉模式。

## 模式判断

- 完整文章 + 封面、头图、首图、主视觉：封面模式。
- 大纲、标题、段落或章节 + 插图、配图、解释图：正文配图模式。
- 无法判断时，只询问：“需要封面图还是正文配图？”

## 资源路由

每次任务先读取：

- [Agent 行为规范](AGENTS.md)
- [知识路由规则](rules/knowledge_routing.md)
- [文章理解与视觉判断](knowledge/article_understanding.md)
- [核心推理规则](rules/core_rules.md)
- [模型与语言适配](knowledge/model_language.md)
- [场景化真实摄影](knowledge/scene_photography.md)
- [质量评分](rules/quality_scoring.md)
- [负面规则](rules/negative_rules.md)
- [构图决策库](knowledge/composition.md)
- [自检与重设计](rules/self_check.md)
- [图片渠道知识](knowledge/image_providers.md)
- [审核与生图规则](rules/generation_workflow.md)

用户要求整篇文章自动规划多张图片、继续已有文章任务或批量交付时，额外读取：

- [文章级多图工作流](rules/article_workflow.md)
- [文章批量生成规则](rules/batch_generation.md)
- [文章图片规划模板](templates/image_plan.md)
- [文章配图审核进度模板](templates/batch_review.md)

完成文章理解卡后，按照 [知识路由规则](rules/knowledge_routing.md) 定点读取命中的分类、
意图、情绪、视觉策略和其他知识条目。不要默认加载全部知识库。

封面模式额外读取：

- [封面规则](rules/cover_rules.md)
- [封面输出模板](templates/cover_output.md)

正文配图模式额外读取：

- [正文配图规则](rules/content_rules.md)
- [正文配图输出模板](templates/content_output.md)

写最终 Prompt 时读取 [Prompt 组装与压缩模板](templates/prompt_templates.md)。

需要案例校准时，先读取 [案例索引](examples/library/index.md)，再按主题选择一个分片并检索
一至三个相似案例。禁止复制案例 Prompt。简单任务通常不需要加载案例。

## 文章级工作流

用户提供完整文章并要求整篇配图时，使用文章级编排层：

1. 保存文章并建立图片规划，通常包含一张封面和三至六张正文配图；短文可以更少。
2. 使用 `templates/image_plan.md` 展示规划，等待用户明确确认。
3. 封面项目调用封面模式，正文项目逐项调用正文配图模式。
4. 每张 Prompt 单独展示、修改和批准，使用 `templates/batch_review.md` 汇报进度。
5. 只有全部 Prompt 中属于未删除项目的当前版本均已批准，才允许统一触发受控并发生图。
6. 默认最多同时生成三张；每张完成后立即保存状态，失败或结果不确定时不再提交新任务，
   等待在途请求结束后阻塞批次，恢复时跳过已成功项目。
7. 全部图片成功后统一创建交付包。

运行状态保存在 `runs/<任务ID>/`。继续任务前必须读取真实状态，不依赖对话记忆猜测进度。
替换图片规划会清空当前项目的 Prompt 与批准状态，必须从新规划重新审核。

## 工作流

严格按顺序执行；第 8 步之前不得写最终 Prompt。

1. **确认输入**
   - 封面需要完整文章；比例缺失时默认 `16:9`。
   - 正文配图至少需要标题或段落；比例缺失时默认 `4:3`。
   - 目标模型缺失时按 GPT Image 通用写法处理。
2. **建立文章理解卡**
   - 按 `knowledge/article_understanding.md` 判断主题、分类、作者意图、核心观点、情绪、
     证据与视觉策略。
   - 使用 `[FACT]`、`[INFERENCE]`、`[ASSUMPTION]`、`[UNKNOWN]` 区分事实与判断。
   - 输入中的主张只代表“文章这样写”，不得假装已做外部事实核验。
3. **提炼一个核心观点**
   - 区分“发生了什么”与“这意味着什么”。
   - 去掉品牌、人物和事件名后仍应成立。
   - 只能包含一个关系、变化或因果；出现并列结论时继续收敛。
4. **按需加载知识**
   - 选择一个主分类、一个主要写作意图和一个主情绪。
   - 分类先给出默认主体路径；核心观点满足覆盖条件时可以切换，并记录切换理由。
   - 分类决定现实对象和地点；意图决定画面任务；情绪只调整镜头、光线和色彩。
   - 知识库用于做选择，不用于把所有条目堆进画面。
5. **选择视觉策略**
   - 按 `rules/knowledge_routing.md` 选择人物行动、实物/过程或界面/机制路径。
   - 人物只在选择、体验、责任或协作是观点核心时承担主要叙事。
   - 物体的位置、数量、队列、边界或状态变化足以表达观点时，不额外加入人物或手。
   - 用一句话完成：`通过【一个主体】在【一个地点】发生【一个动作或状态变化】，表达【一个核心观点】。`
6. **设计构图**
   - 读取 `knowledge/composition.md`。
   - 明确主体、动作、镜头、背景、焦点、光线和色彩。
   - 封面必须说明标题安全区的位置、面积和低干扰要求。
   - 正文配图优先解释关系，概念节点通常不超过四个。
7. **适配目标模型**
   - GPT Image、Seedream：中文或中英混合。
   - Midjourney、Flux、Ideogram：英文。
   - 未知模型使用通用自然语言，不编造参数或专用语法。
8. **生成并压缩 Prompt**
   - 中文正向 Prompt 为 50–60 个汉字。
   - 英文正向 Prompt 为 35–45 个英文单词。
   - 只保留会改变画面的场景、主体、动作、关系、光线、色调和必要留白。
   - Negative Prompt 独立输出，不计入正向 Prompt 长度。
9. **质量门**
   - 读取 `rules/self_check.md`。
   - 先应用 `rules/quality_scoring.md` 的硬门槛；任一失败，回到第 3 步重新设计。
   - 再按 10 分量表评分；低于 9 分，重新选择观点、场景、隐喻或构图。
   - 不得靠增加“高级、8K、电影感”等词提高评分。
10. **输出并等待审核**
   - 所有解释、分析结论和规则使用中文。
   - 最终 Prompt 语言由目标模型决定。
   - 严格使用对应模板，只展示通过质量门的最终方案，不展示失败草稿或隐藏推理。
   - 在模板后询问：`Prompt 已展示，请审核。是否批准生成图片？未指定渠道时默认使用 ThinkAI Image 2。`
   - 用户已选定渠道时，在问题中明确渠道、模型和尺寸。
   - 输出后停止。用户在看到本次最终 Prompt 前给出的“直接生成”不算审核通过。
11. **可选生图执行**
   - 仅当用户在看到最终 Prompt 后明确回复“批准”“通过”“可以生成”等同意语句时执行。
   - 执行前读取 `rules/generation_workflow.md`，检查本 Skill 自己的 `config.json`。
   - 不得读取或复用其他 Skill 的配置、API Key 或脚本。
   - 未指定渠道时使用 ThinkAI Image 2。用户需要选择时，依次提供 ThinkAI Image 2、
     ThinkAI Nano、火山引擎 Seedream、OpenAI GPT Image、Google Nano Banana、其他
     六个选项。
   - 正式渠道未配置时，只让用户选择渠道并通过隐藏输入提供 API Key；地址、推荐模型与
     默认尺寸由 `data/image_providers.json` 管理。
   - “其他”渠道先读取官方图片 API 文档；只有能映射到受控同步协议时才由 Agent 准备
     配置参数，然后让用户通过隐藏输入提供 API Key。
   - 配置后运行 `scripts/provider_preflight.py` 做纯本地验证；不得把 `verified-local`
     描述成远端认证成功。
   - 使用 `scripts/approval_hash.py` 为当前渠道、模型、尺寸、质量和精确 Prompt 计算审核哈希；
     调用 `scripts/generate_image.py` 时必须同时传入 `--approved` 与匹配的
     `--approval-hash`。
   - Prompt、比例、主体、风格或其他画面条件发生变化后，旧批准与旧哈希同时失效。
   - 付费生成 POST 只发送一次。若超时、断线或结果不确定，不得自动重试；先请用户检查
     所选渠道后台，只有用户确认没有成功任务并明确要求重发后才能再次执行。
   - 返回本地图片路径、实际尺寸、请求快照和响应快照。

文章级任务的生成必须改用
`scripts/article_workflow.py generate --execute --max-workers 3`，并遵守
`rules/batch_generation.md` 的全量批准门禁。不得逐张绕过编排层提前生图。

## 输出约束

- 一张图只表达一个核心观点、一个主要动作和一个视觉焦点。
- 封面表达文章意义，不复述新闻现场；正文配图解释当前章节，不承担整篇文章的高潮。
- 默认使用真实摄影、具体生活或工作场景、可观察动作和明确光线。
- 生活化主题默认自然暖色调；工业、分析、风险主题服从文章语义，不强制暖色。
- 不用 Logo、机器人、代码雨、AI 人脸、HUD、粒子或赛博朋克替代观点。
- Negative Prompt 是针对当前方案的约束清单；即使模型不原生支持，也不得虚构模型参数。
- 用户审核前禁止调用任何图片渠道；含糊答复、沉默、预先授权或仅要求“继续”都不算批准。
- ThinkAI Image 2 固定使用 `gpt-image-2`，支持 `1k` 与 `2k`。
- ThinkAI Nano 固定使用 `nano-banana-2`，支持 `1K`、`2K`、`4K` 与画面比例。
- ThinkAI Nano、火山引擎、OpenAI、Google 与其他渠道只在用户显式选择时使用。
- 实际计费以所选渠道后台为准。
- Seedance 属于视频生成，不得作为本 Skill 的图片渠道。

## 图片渠道配置

首次使用时运行：

```bash
python3 -m pip install -r requirements.txt
python3 scripts/configure_api_key.py
```

第一条命令安装生图连接器使用的 `requests` 依赖；只生成 Prompt 时无需安装。
配置脚本默认使用隐藏输入。自动化环境可把 Key 通过标准输入传给
`python3 scripts/configure_api_key.py --api-key-stdin`，禁止把 Key 放入命令参数。

ThinkAI Image 2 保持默认渠道。六种渠道入口的配置与执行方式见
`knowledge/image_providers.md` 与 `rules/generation_workflow.md`。配置只写入当前 Skill
根目录的 `config.json`，使用临时文件原子替换并设为 `0600`。
图片与请求记录默认写入 `generated/<时间戳>/`。`config.json` 与 `generated/` 均不得提交
或随安装包分发。

## 当前边界

- 只支持封面模式和正文配图模式。
- 图片渠道只负责生成审核通过的图片，不参与文章理解和 Prompt 质量判断。
- 不支持图片编辑、未经全量审核的批量生成、自动跳过审核或复用其他 Skill 的凭据。
- 文章级工作流支持多图规划、逐图审核、受控并发、断点恢复和完整后统一交付。
- “其他”只支持受控同步 JSON 图片协议，不支持任意代码、异步轮询或视频接口。
