---
name: cover-prompt-designer
description: Use when designing one cover image prompt from a complete article or an approved cover plan, with editorial storytelling, model-aware language, composition, lighting, and a usable title-safe area.
---

# 封面 Prompt 设计师

## 职责

把完整文章或已确认的封面规划转化为一份封面 Prompt 方案。封面表达文章的核心意义，
不复述新闻现场。只设计一张封面，不审核、不批准、不调用图片渠道。

## 输入

- 完整文章，或来自 `$article-visual-planner` 的封面项目与 `understanding_card`。
- `ratio`：缺失时使用 `16:9`。
- `target_model`：缺失时按 GPT Image 通用自然语言处理。
- 可选的渠道、尺寸和风格约束。

## 必读资源

1. [核心规则](../../references/rules/core_rules.md)
2. [封面规则](../../references/rules/cover_rules.md)
3. [知识路由](../../references/rules/knowledge_routing.md)
4. [构图](../../references/knowledge/composition.md)
5. [标题留白](../../references/knowledge/typography.md)
6. [编辑风格](../../references/knowledge/editorial_style.md)
7. [色彩语言](../../references/knowledge/color_language.md)
8. [模型语言](../../references/knowledge/model_language.md)
9. [场景摄影](../../references/knowledge/scene_photography.md)
10. [负面模式](../../references/knowledge/negative_patterns.md)
11. [Prompt 模板](../../templates/prompt_templates.md)
12. [封面输出模板](../../templates/cover_output.md)

需要校准时才从[案例索引](../../references/examples/library/index.md)检索少量相似案例，不复制
案例 Prompt。

## 执行

1. 复核并收敛为一个 `core_viewpoint`。
2. 选择一个现实场景或必要隐喻、一个主体、一个动作或状态变化。
3. 设计主体、动作、镜头、背景、焦点、光线、色彩和标题安全区。
4. 标题安全区必须说明位置、面积与低干扰要求。
5. 根据模型适配语言：GPT Image、Seedream 可用中文或中英混合；Midjourney、Flux、
   Ideogram 使用英文；未知模型使用中性自然语言。
6. 正向 Prompt 压缩为中文 50–60 个汉字或英文 35–45 个单词。

## 输出契约

```yaml
image_goal: 封面的作用
core_viewpoint: 唯一观点
visual_metaphor: 场景或必要隐喻及理由
composition: 主体、动作、镜头、背景、留白、焦点
style: 编辑气质、材质、色彩和光线
prompt: 最终正向 Prompt
negative_prompt: 针对本方案的负面约束
review_metadata:
  mode: cover
  target_model: 目标模型
  ratio: 比例
  prompt_language: 中文、双语或英文
  prompt_length: 实际长度
```

用户可见输出采用[封面输出模板](../../templates/cover_output.md)，所有解释使用中文。

## 边界

- 不得设计正文配图。
- 不得自行判定 `PASS` 或写入批准状态；交给 `$image-prompt-reviewer`。
- 不得调用图片渠道、读取 API Key 或执行生图脚本。
