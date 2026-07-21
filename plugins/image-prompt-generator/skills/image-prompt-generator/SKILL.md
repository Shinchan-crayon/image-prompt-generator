---
name: image-prompt-generator
description: Use when a user provides a complete article or article section and wants an end-to-end visual workflow that plans, designs, reviews, obtains human approval for, and optionally generates cover or section images.
---

# Image Prompt Generator

## 职责

作为插件的唯一推荐总控入口，编排文章理解、图片规划、Prompt 设计、质量审核、人工批准和
可选生图。总控只管理流程、状态和人工门禁，不复制专项 Skill 的专业判断。

只支持两种视觉模式：

1. **封面模式**：从完整文章设计一张表达核心观点的封面。
2. **正文配图模式**：从标题、段落或章节设计一张解释型配图。

整篇文章多图工作流只是编排这两种模式，不是第三种视觉模式。

## 专项调用顺序

端到端流程严格按以下顺序调用：

1. `$article-visual-planner`：理解文章并制定单图任务或整篇图片规划。
2. `$cover-prompt-designer`：设计封面项目。
3. `$section-illustration-designer`：逐项设计正文配图项目。
4. `$image-prompt-reviewer`：独立执行硬门槛和九分质量审核。
5. `$approved-image-generator`：仅在人工批准门禁满足后执行生图。

封面任务不调用正文设计师；正文任务不调用封面设计师。上面的顺序表示完整文章工作流中的
职责先后，不要求无关专项空跑。

## 输入路由

- 完整文章 + 封面、头图、主视觉：封面模式。
- 标题、段落或章节 + 插图、配图、解释图：正文配图模式。
- 完整文章 + 整篇配图、图片规划、批量交付：文章级编排。
- 无法判断单图类型时，只询问需要封面图还是正文配图。

文章类型不限于科技内容。分类、意图、情绪和风格由共享知识库与规划 Skill 判断。

## 单图流程

1. 调用 `$article-visual-planner` 返回当前图片任务和理解卡。
2. 按模式调用对应设计师生成 Prompt package。
3. 调用 `$image-prompt-reviewer`。
4. 若结果为 `REDESIGN_REQUIRED`，把重设计指令交回同一设计师，再次审核。
5. 结果为 `PASS` 后，完整展示当前方案和 Prompt，等待用户明确批准。
6. 用户修改任何画面或执行条件时，重新设计、审核和展示，旧批准失效。
7. 用户只要 Prompt 时到此结束；用户明确要求生图且批准当前版本后，才调用
   `$approved-image-generator`。

质量审核 `PASS` 不能代替用户批准。用户在看到当前 Prompt 前给出的“直接生成”、含糊的
“继续”或预先授权都不算明确批准。

## 整篇文章流程

总控独占文章任务状态，状态保存在：

```text
runs/<任务ID>/workflow-state.json
```

读取[文章工作流规则](../../references/rules/article_workflow.md)、
[批量生成规则](../../references/rules/batch_generation.md)、
[图片规划模板](../../templates/image_plan.md)和
[审核进度模板](../../templates/batch_review.md)，按以下顺序执行：

1. 通过共享 `article_workflow.py init` 创建任务并保存原文。
2. 调用 `$article-visual-planner` 生成一张封面和必要的正文配图规划。
3. 完整展示图片规划，等待用户明确确认；未确认前停止。
4. 保存已确认规划后，按顺序调用对应设计师和 `$image-prompt-reviewer`。
5. 每张通过质量门的 Prompt 都必须逐张展示，等待用户明确批准或修改。
6. 每次修改都生成新版本，只使该图片的旧批准失效。
7. 只有全部当前版本 Prompt 都通过质量审核并获得明确批准，才调用 `$approved-image-generator`
   统一批量生图。
8. 生成阶段严格按规划顺序固定分批，每批最多三张；当前批次全部成功后才生成下一批，
   任一失败或结果不确定都会阻塞后续批次，恢复时跳过已成功项目。
9. 全部图片成功后才创建正式交付包。

规划确认不等于 Prompt 批准，最后一张批准不能代替其他图片批准。

## 状态所有权

- 只有本总控 Skill 可以创建任务、保存规划、记录 Prompt 版本、批准状态和流程阶段。
- 专项 Skill 只返回阶段结果，不直接修改 `workflow-state.json`。
- 继续任务时必须读取真实状态：

```bash
python3 ../../scripts/article_workflow.py status --run '<RUN_ID>'
```

- `plan_review`：继续规划确认。
- `prompt_review`：继续第一张未批准 Prompt。
- `ready`：全量批准门禁已满足。
- `generating`：继续未完成项目。
- `blocked`：先处理失败或不确定结果。
- `complete`：检查或重建交付，不重复生图。

不得依赖对话记忆猜测进度，不得手工修改状态文件。

## 共享资源

- 插件级行为规范：[AGENTS.md](../../AGENTS.md)
- 知识路由：[knowledge_routing.md](../../references/rules/knowledge_routing.md)
- 文章工作流脚本：[article_workflow.py](../../scripts/article_workflow.py)
- 渠道配置与风险规则：[generation_workflow.md](../../references/rules/generation_workflow.md)

知识、规则、模板、案例和脚本只存在于插件根目录；不得复制回任何 Skill。

## 输出与边界

- 所有解释、规划、审核结论使用中文；最终 Prompt 语言由目标模型决定。
- 默认先交付 Prompt。未明确要求生图时，不进入图片渠道配置。
- 不支持图片编辑、文章写作、视频生成或绕过审核。
- 图片渠道只执行已批准 Prompt，不参与文章理解和视觉决策。
