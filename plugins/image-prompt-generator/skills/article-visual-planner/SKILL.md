---
name: article-visual-planner
description: Use when planning the visual coverage of a complete article, selecting the core viewpoint, article classification, intent, emotion, and the necessary cover and section illustration positions before any final image prompts are written.
---

# 文章视觉规划师

## 职责

分析文章并制定图片规划。只决定文章需要哪些图片、每张图解释什么，不生成最终 Prompt，
不审核 Prompt，不调用图片渠道，也不得推进工作流状态。

整篇文章规划只是封面模式和正文配图模式的编排准备，不是第三种视觉模式。

## 输入

- `scope`：`full_article`、`cover` 或 `section`。它表示规划范围，不新增视觉模式。
- `article`：完整文章；规划封面或整篇文章时必填。
- `outline`、`heading`、`paragraph`、`section`：规划正文配图时按已有内容提供。
- `ratio`、`target_model`、`provider`：可选执行约束，只用于规划。

## 必读资源

1. [文章理解](../../references/knowledge/article_understanding.md)
2. [文章分类](../../references/knowledge/article_classification.md)
3. [写作意图库](../../references/knowledge/intent_library.md)
4. [情绪库](../../references/knowledge/emotion_library.md)
5. [视觉策略](../../references/knowledge/visual_strategy.md)
6. [知识路由](../../references/rules/knowledge_routing.md)
7. [核心规则](../../references/rules/core_rules.md)
8. 整篇规划时读取[文章工作流](../../references/rules/article_workflow.md)和
   [图片规划模板](../../templates/image_plan.md)

按知识路由定点读取命中的条目，不默认加载全部案例或全部隐喻。

## 执行

1. 区分文章事实、作者立场、设计推断和未知信息。
2. 提炼一个去掉品牌名后仍成立的 `core_viewpoint`。
3. 选择一个 `primary_classification`、至多一个 `secondary_classification`、一个
   `intent` 和一个主 `emotion`。
4. 决定人物行动、实物过程或界面机制中的一条主体路径，并形成 `visual_strategy`。
5. 整篇文章只规划真正增加理解的图片：一张封面，加零张或多张正文配图。不得按标题数量
   机械配图，不得让两张图表达同一观点。
6. 单张封面或正文请求只返回所需项目。

## 输出契约

返回结构化阶段结果，字段不可省略：

```yaml
understanding_card: 文章理解卡
core_viewpoint: 全文或当前章节的唯一观点
primary_classification: 主分类
secondary_classification: 次分类或 null
intent: 主要写作意图
emotion: 主情绪
visual_strategy: 主体路径、场景方向与选择依据
image_plan:
  - id: cover 或稳定的 section-id
    mode: cover 或 content
    source: 对应原文范围
    purpose: 图片承担的唯一任务
    ratio: 目标比例
    style_direction: 风格方向
```

`image_plan` 只包含设计任务，不包含最终正向 Prompt、Negative Prompt 或批准状态。

## 边界

- 不得生成最终 Prompt。
- 不得推进工作流状态或写入 `workflow-state.json`。
- 不得把规划确认当成 Prompt 批准。
- 不得调用图片渠道或读取 API Key。
