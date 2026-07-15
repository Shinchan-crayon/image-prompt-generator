# Image Prompt Generator 多 Skill 架构设计

## 1. 目标

将当前由单个 `image-prompt-generator` Skill 承担的文章理解、视觉规划、Prompt 设计、
质量审核和图片生成职责，拆分为一个总控 Skill 与五个专项 Skill。

拆分后必须保持：

- 用户仍可从 `$image-prompt-generator` 完成端到端工作流。
- 封面模式与正文配图模式仍是仅有的两种视觉模式。
- 整篇文章工作流仍是编排层，不新增第三种视觉模式。
- Prompt 必须先展示并获得明确批准，才允许调用付费图片渠道。
- 现有多渠道配置、审核哈希、并发限制、断点恢复和统一交付能力不降级。
- 共享知识只有一份，不在多个 Skill 中复制。

## 2. 非目标

本次迁移不执行以下改动：

- 不新增文章写作、图片编辑、视频生成或品牌资产管理功能。
- 不按文章分类、视觉风格或图片渠道分别创建 Skill。
- 不改变现有图片供应商协议和默认渠道。
- 不修改 Prompt 长度、评分门槛或用户批准规则。
- 不重写已经通过验证的图片生成连接器。

## 3. 目标目录

```text
plugins/image-prompt-generator/
├── .codex-plugin/
│   └── plugin.json
├── assets/
│   ├── icon.png
│   ├── logo.png
│   ├── workflow-state-schema.json
│   └── image-plan-schema.json
├── references/
│   ├── knowledge/
│   └── rules/
├── templates/
├── scripts/
│   └── providers/
├── skills/
│   ├── image-prompt-generator/
│   │   └── SKILL.md
│   ├── article-visual-planner/
│   │   └── SKILL.md
│   ├── cover-prompt-designer/
│   │   └── SKILL.md
│   ├── section-illustration-designer/
│   │   └── SKILL.md
│   ├── image-prompt-reviewer/
│   │   └── SKILL.md
│   └── approved-image-generator/
│       └── SKILL.md
├── config.example.json
└── requirements.txt
```

案例库作为共享参考资料迁移到 `references/examples/`。运行产生的 `config.json`、
`generated/` 和 `runs/` 保持在插件可写运行目录，不提交到仓库。

## 4. Skill 职责

### 4.1 `image-prompt-generator`

唯一推荐的完整工作流入口。

负责：

- 判断单张封面、单张正文配图或整篇文章工作流。
- 创建、读取和恢复文章任务状态。
- 按顺序调用专项 Skill。
- 展示规划、Prompt 和审核进度。
- 维护人工确认门禁。
- 在全部 Prompt 批准后调用图片生成 Skill。

不负责：

- 直接完成文章分类和视觉方案细节。
- 直接组装最终 Prompt。
- 自行降低质量评分。
- 直接发送图片生成请求。

### 4.2 `article-visual-planner`

负责文章理解与视觉规划。

输入：

```yaml
article: string
request_scope: cover | section | full_article
section: object | null
target_platform: string | null
```

输出：

```yaml
understanding_card: object
core_viewpoint: string
primary_classification: string
secondary_classification: string | null
intent: string
emotion: string
visual_strategy: object
image_plan: [object]
```

整篇文章输出一张封面和零至多张正文配图规划；单图请求只输出对应项目。

### 4.3 `cover-prompt-designer`

负责封面模式。

输入：

```yaml
article: string
understanding_card: object
visual_strategy: object
ratio: string
target_model: string
```

输出必须包含图片目标、核心观点、视觉隐喻、构图、风格、Prompt、Negative Prompt 和
质量检查所需元数据。

封面必须表达文章意义、只有一个焦点，并保留标题安全区。

### 4.4 `section-illustration-designer`

负责正文配图模式。

输入：

```yaml
article_context: string | null
section_heading: string
section_content: string
understanding_card: object
visual_strategy: object
ratio: string
target_model: string
```

输出结构与封面 Skill 一致，但目标是解释当前章节，不承担整篇文章主视觉任务。

### 4.5 `image-prompt-reviewer`

负责独立质量检查，不调用图片渠道。

输入：

```yaml
mode: cover | section
source_content: string
understanding_card: object
prompt_package: object
```

输出：

```yaml
status: PASS | REDESIGN_REQUIRED
score: number
hard_gate_results: [object]
dimension_scores: [object]
redesign_instructions: [string]
reviewed_prompt_package: object | null
```

任一硬门槛失败或综合评分低于 9 分时返回 `REDESIGN_REQUIRED`。修改必须回到相应设计
Skill 重新生成，不允许只添加风格词提高评分。

### 4.6 `approved-image-generator`

负责审核通过后的渠道配置、单图或批量生成和交付。

输入：

```yaml
approved_items: [object]
provider: string
model: string
size_or_ratio: string
approval_hashes: [string]
max_workers: integer
```

负责：

- 图片渠道选择、配置和本地预检。
- 审核哈希二次验证。
- 单图生成。
- 最多三个并发任务的文章批量生成。
- 失败不确定状态阻断、断点恢复和成功项跳过。
- 生成记录、文件哈希和最终交付包。

无有效批准记录、Prompt 已变化或哈希不一致时必须拒绝生成。直接调用此 Skill 也不能
绕过门禁。

## 5. 调用流程

### 5.1 单张封面

```text
image-prompt-generator
→ article-visual-planner
→ cover-prompt-designer
→ image-prompt-reviewer
→ 用户审核
→ approved-image-generator（可选）
```

### 5.2 单张正文配图

```text
image-prompt-generator
→ article-visual-planner
→ section-illustration-designer
→ image-prompt-reviewer
→ 用户审核
→ approved-image-generator（可选）
```

### 5.3 整篇文章

```text
image-prompt-generator
→ article-visual-planner
→ 用户确认图片规划
→ cover-prompt-designer / section-illustration-designer
→ image-prompt-reviewer（逐图）
→ 用户逐图审核
→ 全量批准门禁
→ approved-image-generator
→ 统一交付
```

## 6. 共享资源边界

以下资源迁移到插件根目录，成为所有 Skill 的唯一事实来源：

- `knowledge/` → `references/knowledge/`
- `rules/` → `references/rules/`
- `examples/` → `references/examples/`
- `templates/` → `templates/`
- `scripts/` → `scripts/`
- `data/` → `assets/data/`
- `config.example.json` 与 `requirements.txt` → 插件根目录

专项 Skill 只声明职责、输入输出和资源路由，不复制完整知识内容。

## 7. 状态协议

文章级状态由总控 Skill 独占维护，专项 Skill 返回结果但不自行推进阶段。

建议阶段：

```text
planning
plan_confirmation
prompt_design
prompt_review
user_approval
generation
delivery
completed
```

每个图片项目至少记录：

```yaml
id: string
mode: cover | section
source_ref: string
prompt_version: integer
review_status: PENDING | PASS | REDESIGN_REQUIRED
approval_status: PENDING | APPROVED | REJECTED
approval_hash: string | null
generation_status: NOT_STARTED | IN_FLIGHT | SUCCEEDED | FAILED | UNKNOWN
output_path: string | null
```

Prompt、模型、渠道、尺寸或画面条件变化时，批准状态和批准哈希必须同时失效。

## 8. 触发与可见性

`image-prompt-generator` 是 README 和插件默认 Prompt 中推荐的完整入口。五个专项 Skill
随插件安装，并允许用户显式调用：

- “只分析这篇文章应该配哪些图”触发 `article-visual-planner`。
- “只设计封面 Prompt”触发 `cover-prompt-designer`。
- “为这一段设计解释图”触发 `section-illustration-designer`。
- “检查这条图片 Prompt”触发 `image-prompt-reviewer`。
- “配置图片渠道”或“生成已批准图片”触发 `approved-image-generator`。

专项 Skill 的描述必须避免重叠。未明确指定专项 Skill 的完整文章请求优先进入总控。

## 9. 迁移策略

迁移采用一次性切换，不长期保留两套运行结构：

1. 先建立插件级共享目录并移动资源。
2. 新建五个专项 Skill 和精简后的总控 Skill。
3. 更新全部相对路径、脚本根目录定位和配置文件定位。
4. 更新插件介绍、README、默认 Prompt 和 Skill 数量说明。
5. 删除旧主 Skill 内已经迁移的重复资源。
6. 在临时目录模拟干净安装并执行完整验证。

Git 历史负责回滚，不在发布包中保留旧版副本、迁移日志或兼容壳。

## 10. 验证标准

结构验证：

- 官方 Plugin validator 通过。
- 六个 Skill 均通过官方 Skill validator。
- 插件目录不存在第七个意外 Skill 或旧入口副本。
- 所有共享资源链接可解析。

行为验证：

- 单张封面与正文配图均可从总控完成。
- 五个专项 Skill 可被显式调用。
- 整篇文章规划、逐图审核、全量批准和批量生成顺序不变。
- 未批准 Prompt 无法调用图片生成。
- Prompt 变化后旧批准哈希失效。
- 并发上限、失败阻断和断点恢复通过回归测试。

发布验证：

- 使用文件允许名单检查插件成品目录。
- 扫描 API Key、绝对用户路径、开发日志和未知文件。
- 临时干净副本通过全部验证。
- 从 GitHub 重新克隆后可添加 marketplace 并安装插件。

## 11. 架构结论

采用一个总控 Skill 与五个专项 Skill。拆分依据是独立职责和稳定输入输出，而不是知识条目
数量。共享知识、模板、脚本和数据提升到插件根目录，确保只有一份事实来源；总控维护状态，
专项 Skill 完成阶段任务，图片生成 Skill 强制执行批准门禁。
