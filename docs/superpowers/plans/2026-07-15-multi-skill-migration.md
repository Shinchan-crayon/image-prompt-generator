# Image Prompt Generator Multi-Skill Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有单 Skill 插件迁移为一个总控 Skill、五个专项 Skill 和一套插件级共享资源，并保持现有审核门禁、多渠道生图、受控并发、断点恢复与交付能力不降级。

**Architecture:** 插件根目录是唯一运行根目录，承载共享 `references/`、`templates/`、`scripts/`、`assets/data/`、配置示例和依赖声明。六个 Skill 只包含精简入口与 UI 元数据：总控独占文章任务状态和人工门禁，五个专项 Skill 通过明确输入输出契约分别完成规划、封面设计、正文设计、质量审核和已批准图片生成。

**Tech Stack:** Codex Plugin marketplace、Codex Skills、Markdown、YAML、JSON、Python 3 标准库、requests、unittest。

## Global Constraints

- 仅保留封面模式和正文配图模式；整篇文章工作流只是编排层，不是第三种视觉模式。
- 共享知识、规则、案例、模板、脚本和数据只能存在一份，不得复制到多个 Skill。
- `image-prompt-generator` 是唯一推荐的端到端入口；五个专项 Skill 允许用户显式调用。
- 总控 Skill 独占维护文章工作流状态；专项 Skill 返回阶段结果，不自行推进状态。
- 全部当前版本 Prompt 审核通过后才允许批量生图。
- `approved-image-generator` 被直接调用时也必须验证明确批准、approval hash 及 Prompt、模型、渠道、尺寸一致性。
- 保持现有图片供应商协议、默认 ThinkAI Image 2、多渠道选择、最多三个默认并发、失败阻断、断点恢复和统一交付行为。
- 不重写稳定图片连接器，只调整插件根路径和调用说明。
- `config.json`、`generated/`、`runs/`、开发计划、测试、日志和调试资料不得进入插件成品目录。
- 所有用户可见说明和分析使用中文；模型 Prompt 语言继续按目标模型适配。

---

## File Map

### Plugin-Level Shared Runtime

- Move: `plugins/image-prompt-generator/skills/image-prompt-generator/knowledge/` → `plugins/image-prompt-generator/references/knowledge/`
- Move: `plugins/image-prompt-generator/skills/image-prompt-generator/rules/` → `plugins/image-prompt-generator/references/rules/`
- Move: `plugins/image-prompt-generator/skills/image-prompt-generator/examples/` → `plugins/image-prompt-generator/references/examples/`
- Move: `plugins/image-prompt-generator/skills/image-prompt-generator/templates/` → `plugins/image-prompt-generator/templates/`
- Move: `plugins/image-prompt-generator/skills/image-prompt-generator/scripts/` → `plugins/image-prompt-generator/scripts/`
- Move: `plugins/image-prompt-generator/skills/image-prompt-generator/data/` → `plugins/image-prompt-generator/assets/data/`
- Move: `plugins/image-prompt-generator/skills/image-prompt-generator/config.example.json` → `plugins/image-prompt-generator/config.example.json`
- Move: `plugins/image-prompt-generator/skills/image-prompt-generator/requirements.txt` → `plugins/image-prompt-generator/requirements.txt`
- Move and rewrite: `plugins/image-prompt-generator/skills/image-prompt-generator/.gitignore` → `plugins/image-prompt-generator/.gitignore`
- Create: `plugins/image-prompt-generator/README.md`
- Create: `plugins/image-prompt-generator/AGENTS.md`

### Skill Entrypoints

- Rewrite: `plugins/image-prompt-generator/skills/image-prompt-generator/SKILL.md`
- Rewrite: `plugins/image-prompt-generator/skills/image-prompt-generator/agents/openai.yaml`
- Delete after migration: `plugins/image-prompt-generator/skills/image-prompt-generator/README.md`
- Delete after migration: `plugins/image-prompt-generator/skills/image-prompt-generator/AGENTS.md`
- Create: `plugins/image-prompt-generator/skills/article-visual-planner/SKILL.md`
- Create: `plugins/image-prompt-generator/skills/article-visual-planner/agents/openai.yaml`
- Create: `plugins/image-prompt-generator/skills/cover-prompt-designer/SKILL.md`
- Create: `plugins/image-prompt-generator/skills/cover-prompt-designer/agents/openai.yaml`
- Create: `plugins/image-prompt-generator/skills/section-illustration-designer/SKILL.md`
- Create: `plugins/image-prompt-generator/skills/section-illustration-designer/agents/openai.yaml`
- Create: `plugins/image-prompt-generator/skills/image-prompt-reviewer/SKILL.md`
- Create: `plugins/image-prompt-generator/skills/image-prompt-reviewer/agents/openai.yaml`
- Create: `plugins/image-prompt-generator/skills/approved-image-generator/SKILL.md`
- Create: `plugins/image-prompt-generator/skills/approved-image-generator/agents/openai.yaml`

### Validation Outside Product Package

- Create: `/Users/shinchan/Documents/Skill Development/image-prompt-generator-dev/tests/test_multi_skill_plugin.py`
- Modify: `/Users/shinchan/Documents/Skill Development/image-prompt-generator-dev/tests/test_codex_plugin_marketplace.py`
- Modify: `/Users/shinchan/Documents/Skill Development/image-prompt-generator-dev/tests/test_release_cleanliness.py`
- Modify: `/Users/shinchan/Documents/Skill Development/image-prompt-generator-dev/tests/test_category_subject_routing.py`
- Modify: `/Users/shinchan/Documents/Skill Development/image-prompt-generator-dev/tests/test_generation_transport.py`
- Modify: `/Users/shinchan/Documents/Skill Development/image-prompt-generator-dev/tests/test_article_workflow_concurrency.py`
- Modify: `/Users/shinchan/Documents/Image Prompt Generator Development/tests/test_*.py`

---

### Task 1: Add Failing Multi-Skill Structure Tests

**Files:**
- Create: `/Users/shinchan/Documents/Skill Development/image-prompt-generator-dev/tests/test_multi_skill_plugin.py`
- Modify: `/Users/shinchan/Documents/Skill Development/image-prompt-generator-dev/tests/test_codex_plugin_marketplace.py`

**Interfaces:**
- Consumes: 当前插件根路径 `plugins/image-prompt-generator/`
- Produces: `PLUGIN_ROOT`, `EXPECTED_SKILLS` 和共享目录契约，后续任务以这些断言为验收标准

- [ ] **Step 1: Write the failing structure test**

```python
PLUGIN_ROOT = REPO_ROOT / "plugins" / "image-prompt-generator"
EXPECTED_SKILLS = {
    "image-prompt-generator",
    "article-visual-planner",
    "cover-prompt-designer",
    "section-illustration-designer",
    "image-prompt-reviewer",
    "approved-image-generator",
}

def test_plugin_exposes_exactly_six_skills(self):
    skill_names = {
        path.parent.name
        for path in (PLUGIN_ROOT / "skills").glob("*/SKILL.md")
    }
    self.assertEqual(skill_names, EXPECTED_SKILLS)

def test_shared_runtime_exists_only_at_plugin_level(self):
    for path in (
        "references/knowledge",
        "references/rules",
        "references/examples",
        "templates",
        "scripts",
        "assets/data",
    ):
        self.assertTrue((PLUGIN_ROOT / path).is_dir(), path)
    for skill_root in (PLUGIN_ROOT / "skills").iterdir():
        for forbidden in ("knowledge", "rules", "examples", "templates", "scripts", "data"):
            self.assertFalse((skill_root / forbidden).exists())
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
python3 -m unittest \
  "/Users/shinchan/Documents/Skill Development/image-prompt-generator-dev/tests/test_multi_skill_plugin.py" \
  "/Users/shinchan/Documents/Skill Development/image-prompt-generator-dev/tests/test_codex_plugin_marketplace.py" -v
```

Expected: FAIL because only one Skill exists and shared resources still live inside it.

- [ ] **Step 3: Commit the failing tests**

```bash
git add docs/superpowers/plans/2026-07-15-multi-skill-migration.md
git commit -m "test: define multi-skill plugin contract"
```

The external tests remain outside the product repository and are not staged.

---

### Task 2: Move Shared Resources to Plugin Root

**Files:**
- Move all paths listed under “Plugin-Level Shared Runtime”
- Modify: `plugins/image-prompt-generator/scripts/provider_registry.py`
- Modify: `plugins/image-prompt-generator/scripts/configure_api_key.py`
- Modify: `plugins/image-prompt-generator/scripts/configure_provider.py`
- Modify: `plugins/image-prompt-generator/scripts/approval_hash.py`
- Modify: `plugins/image-prompt-generator/scripts/provider_preflight.py`
- Modify: `plugins/image-prompt-generator/scripts/generate_image.py`
- Modify: `plugins/image-prompt-generator/scripts/article_workflow.py`
- Modify: `plugins/image-prompt-generator/scripts/check_skill.py`

**Interfaces:**
- Consumes: Existing provider adapters and workflow APIs unchanged
- Produces: `PLUGIN_ROOT = Path(__file__).resolve().parent.parent`, registry at `assets/data/image_providers.json`, runtime files under plugin root

- [ ] **Step 1: Add path-resolution assertions**

Add tests that import each script from `PLUGIN_ROOT / "scripts"` and assert:

```python
self.assertEqual(provider_registry.PLUGIN_ROOT, PLUGIN_ROOT)
self.assertEqual(
    provider_registry.DEFAULT_REGISTRY_PATH,
    PLUGIN_ROOT / "assets" / "data" / "image_providers.json",
)
```

Also assert `configure_provider`, `provider_preflight`, `generate_image` and `article_workflow` default to plugin-root `config.json`, `generated/` and `runs/`.

- [ ] **Step 2: Run the path tests and verify RED**

Expected: FAIL because the shared directories and `PLUGIN_ROOT` contract do not yet exist.

- [ ] **Step 3: Move resources without duplicating them**

Use filesystem moves, then remove empty old directories. Do not leave compatibility copies under the total-control Skill.

- [ ] **Step 4: Update script root constants**

Use this invariant in plugin-level scripts:

```python
PLUGIN_ROOT = Path(__file__).resolve().parent.parent
```

Replace old `SKILL_ROOT` CLI defaults with `PLUGIN_ROOT` while preserving public function parameters named `skill_root` where existing tests and callers depend on them.

Update the provider registry:

```python
DEFAULT_REGISTRY_PATH = PLUGIN_ROOT / "assets" / "data" / "image_providers.json"
```

- [ ] **Step 5: Update shared Markdown links**

All shared Markdown links must be relative to their new file locations. Skill entrypoints must link upward to:

```text
../../references/...
../../templates/...
../../scripts/...
```

Shared reference files must not point back into a specific Skill.

- [ ] **Step 6: Run provider and workflow regression tests**

Run both external suites with `IMAGE_PROMPT_GENERATOR_PLUGIN_ROOT` or updated path constants. Expected: all provider, transport, state, batch, concurrency and delivery tests PASS.

- [ ] **Step 7: Commit**

```bash
git add plugins/image-prompt-generator
git commit -m "refactor: move shared runtime to plugin root"
```

---

### Task 3: Create the Planning and Prompt-Design Skills

**Files:**
- Create: `plugins/image-prompt-generator/skills/article-visual-planner/SKILL.md`
- Create: `plugins/image-prompt-generator/skills/article-visual-planner/agents/openai.yaml`
- Create: `plugins/image-prompt-generator/skills/cover-prompt-designer/SKILL.md`
- Create: `plugins/image-prompt-generator/skills/cover-prompt-designer/agents/openai.yaml`
- Create: `plugins/image-prompt-generator/skills/section-illustration-designer/SKILL.md`
- Create: `plugins/image-prompt-generator/skills/section-illustration-designer/agents/openai.yaml`

**Interfaces:**
- Produces planner output keys: `understanding_card`, `core_viewpoint`, `primary_classification`, `secondary_classification`, `intent`, `emotion`, `visual_strategy`, `image_plan`
- Produces designer package keys: `image_goal`, `core_viewpoint`, `visual_metaphor`, `composition`, `style`, `prompt`, `negative_prompt`, `review_metadata`

- [ ] **Step 1: Add contract tests for descriptions and outputs**

Tests must assert each Skill frontmatter name matches its folder, descriptions have distinct trigger language, and each body names every required input and output field.

- [ ] **Step 2: Run and verify RED**

Expected: FAIL because the three Skill directories do not exist.

- [ ] **Step 3: Implement `article-visual-planner`**

Keep the entrypoint concise. It must:

1. Read plugin-level article understanding, classification, intent, emotion, visual strategy, routing and planning template references.
2. Produce one primary classification, one intent, one emotion and one core viewpoint.
3. Return one cover plus zero or more section items for `full_article`; only the requested item for `cover` or `section`.
4. Never write a final image Prompt and never advance workflow state.

- [ ] **Step 4: Implement `cover-prompt-designer`**

It must load cover rules, composition, typography, style, color, negative patterns, model language and Prompt templates; create one cover package; preserve a title-safe area; never call a provider.

- [ ] **Step 5: Implement `section-illustration-designer`**

It must load content rules, explanatory visuals, composition, visual style routing, model language and Prompt templates; explain only the selected section; never inherit cover style automatically; never call a provider.

- [ ] **Step 6: Generate `agents/openai.yaml` for all three Skills**

Each default prompt explicitly names its Skill, for example:

```yaml
interface:
  display_name: "Article Visual Planner"
  short_description: "分析文章并规划封面与正文配图位置"
  default_prompt: "使用 $article-visual-planner 分析这篇文章并规划需要的图片。"
```

- [ ] **Step 7: Validate and commit**

Run official `quick_validate.py` separately for each Skill, run contract tests, then:

```bash
git add plugins/image-prompt-generator/skills
git commit -m "feat: add visual planning and prompt design skills"
```

---

### Task 4: Create Review and Approved Generation Skills

**Files:**
- Create: `plugins/image-prompt-generator/skills/image-prompt-reviewer/SKILL.md`
- Create: `plugins/image-prompt-generator/skills/image-prompt-reviewer/agents/openai.yaml`
- Create: `plugins/image-prompt-generator/skills/approved-image-generator/SKILL.md`
- Create: `plugins/image-prompt-generator/skills/approved-image-generator/agents/openai.yaml`

**Interfaces:**
- Reviewer output: `status`, `score`, `hard_gate_results`, `dimension_scores`, `redesign_instructions`, `reviewed_prompt_package`
- Generator input: `approved_items`, `provider`, `model`, `size_or_ratio`, `approval_hashes`, `max_workers`

- [ ] **Step 1: Add failing reviewer and generator boundary tests**

Assert the reviewer contains `PASS`, `REDESIGN_REQUIRED`, hard-gate failure and score `< 9` behavior. Assert the generator requires approval hash, rejects changed execution conditions, defaults batch concurrency to three, and links only to shared generation scripts/rules.

- [ ] **Step 2: Run and verify RED**

Expected: FAIL because both Skills are missing.

- [ ] **Step 3: Implement `image-prompt-reviewer`**

The Skill must independently load quality scoring, self-check, core and negative rules. It must return `REDESIGN_REQUIRED` for any hard-gate failure or score below 9 and route redesign back to the matching designer instead of decorating the existing Prompt.

- [ ] **Step 4: Implement `approved-image-generator`**

The Skill must:

1. Configure or select a provider through plugin-level scripts.
2. Perform local preflight without claiming remote authentication success.
3. Recompute approval hashes from exact Prompt and execution conditions.
4. Refuse unapproved, changed or mismatched items.
5. Use `article_workflow.py generate --execute --max-workers 3` for article batches.
6. Preserve one paid POST, uncertain-result blocking, resume and delivery behavior.

- [ ] **Step 5: Validate and commit**

Run both official Skill validators and all generation regression tests, then:

```bash
git add plugins/image-prompt-generator/skills
git commit -m "feat: add prompt review and approved generation skills"
```

---

### Task 5: Rewrite the Total-Control Skill

**Files:**
- Rewrite: `plugins/image-prompt-generator/skills/image-prompt-generator/SKILL.md`
- Rewrite: `plugins/image-prompt-generator/skills/image-prompt-generator/agents/openai.yaml`
- Delete: `plugins/image-prompt-generator/skills/image-prompt-generator/README.md`
- Delete: `plugins/image-prompt-generator/skills/image-prompt-generator/AGENTS.md`

**Interfaces:**
- Consumes outputs from all five specialist Skills
- Produces workflow state transitions and user-facing planning/review/approval sequence

- [ ] **Step 1: Add failing orchestration tests**

Assert the total-control Skill names all five specialist Skills in order, owns `runs/<任务ID>/workflow-state.json`, stops for plan confirmation, performs per-image review, waits for all approvals, and only then invokes `$approved-image-generator`.

- [ ] **Step 2: Run and verify RED**

Expected: FAIL because the current Skill still performs every specialist responsibility itself.

- [ ] **Step 3: Rewrite the entrypoint**

The body must contain only:

- scope and two-mode boundary
- routing among single cover, single section and full article
- specialist call sequence
- workflow-state ownership
- plan confirmation and per-Prompt approval gates
- resume behavior
- shared-resource links needed by the orchestrator

Remove duplicated classification, design, scoring and provider implementation instructions now owned by specialists.

- [ ] **Step 4: Update UI metadata**

The total-control Skill remains the default full-workflow entry and its description must win for unspecified complete-article requests without overlapping explicit specialist triggers.

- [ ] **Step 5: Validate and commit**

Run official Skill validation and orchestration tests, then:

```bash
git add plugins/image-prompt-generator/skills/image-prompt-generator
git commit -m "refactor: make image prompt generator the orchestrator"
```

---

### Task 6: Rewrite Plugin-Level Product Documentation and Metadata

**Files:**
- Create: `plugins/image-prompt-generator/README.md`
- Create: `plugins/image-prompt-generator/AGENTS.md`
- Modify: `plugins/image-prompt-generator/.codex-plugin/plugin.json`
- Modify: `plugins/image-prompt-generator/.gitignore`
- Modify: `README.md`

**Interfaces:**
- Produces user-visible plugin description with six Skill names and installation/usage guidance

- [ ] **Step 1: Add failing metadata tests**

Assert plugin manifest and README describe six Skills, broad article support rather than technology-only support, one total-control entry, specialist direct invocation, shared knowledge, and review-before-generation behavior.

- [ ] **Step 2: Run and verify RED**

Expected: FAIL because metadata still describes a single technology-focused Skill.

- [ ] **Step 3: Write plugin README and AGENTS**

`README.md` is user-facing. `AGENTS.md` contains plugin-wide behavioral boundaries only and routes detailed knowledge to shared references. Neither file may contain migration history, architecture review notes, test reports or internal development wording.

- [ ] **Step 4: Update manifest**

Bump strict semver to `3.0.0`. Update description, long description and starter prompts to reflect multi-Skill workflows while keeping paths and assets valid.

- [ ] **Step 5: Update repository README and `.gitignore`**

Document GitHub marketplace installation and six available Skills. Ignore plugin-root `config.json`, `generated/`, `runs/`, Python caches and system files.

- [ ] **Step 6: Validate and commit**

Run marketplace tests and plugin validator, then:

```bash
git add README.md plugins/image-prompt-generator
git commit -m "docs: describe the multi-skill plugin"
```

---

### Task 7: Replace the Old Skill Validator with a Plugin Validator

**Files:**
- Rewrite: `plugins/image-prompt-generator/scripts/check_skill.py`
- Modify: `/Users/shinchan/Documents/Skill Development/image-prompt-generator-dev/tests/test_release_cleanliness.py`

**Interfaces:**
- Produces CLI `python3 scripts/check_skill.py` returning zero only for a clean, valid six-Skill plugin

- [ ] **Step 1: Rewrite release cleanliness tests for plugin root**

Copy the complete plugin to a temporary directory, run `scripts/check_skill.py`, and verify it rejects:

- unknown root file
- unknown nested reference
- seventh Skill
- duplicate `knowledge/` inside a Skill
- `config.json`, `generated/`, `runs/`
- API-key-like values
- `/Users/...` absolute paths
- development terms such as internal migration notes or test reports

- [ ] **Step 2: Run and verify RED**

Expected: FAIL because the old validator assumes a single Skill root.

- [ ] **Step 3: Implement plugin-level allowlist validation**

The validator must check:

1. exact six Skill folders and required `SKILL.md`/`agents/openai.yaml`
2. required plugin manifest, shared references, templates, scripts, provider adapters and data
3. no shared runtime folders inside any Skill
4. all Markdown links resolve
5. frontmatter folder/name consistency
6. distinct trigger descriptions
7. two-mode boundary and specialist contracts
8. existing 22 classifications, 100 examples, model language rules, quality threshold and provider contracts
9. release allowlist and sensitive/development-content scans

- [ ] **Step 4: Run clean and mutation tests**

Expected: clean copy PASS; each injected forbidden file or seventh Skill FAIL with a precise Chinese error.

- [ ] **Step 5: Commit**

```bash
git add plugins/image-prompt-generator/scripts/check_skill.py
git commit -m "test: validate the complete multi-skill plugin"
```

---

### Task 8: Full Verification and Clean Installation

**Files:**
- Modify only if verification exposes a confirmed defect

**Interfaces:**
- Produces release evidence for repository source, temporary copy and fresh GitHub clone

- [ ] **Step 1: Run all external regression tests**

Run:

```bash
python3 -m unittest discover \
  -s "/Users/shinchan/Documents/Image Prompt Generator Development/tests" \
  -p "test_*.py" -v
python3 -m unittest discover \
  -s "/Users/shinchan/Documents/Skill Development/image-prompt-generator-dev/tests" \
  -p "test_*.py" -v
```

Expected: all tests PASS.

- [ ] **Step 2: Run plugin and Skill validators**

Run plugin-level `scripts/check_skill.py`, official Plugin validator, and official `quick_validate.py` for all six Skills. Expected: all PASS.

- [ ] **Step 3: Validate a temporary clean copy**

Copy only repository-tracked plugin files to a temporary directory and rerun the plugin validator plus all six Skill validators. Confirm no ignored runtime or development files are present.

- [ ] **Step 4: Scan release contents**

Search the plugin tree for API keys, `/Users/`, `TODO`, `TBD`, migration logs, test reports, debug notes, `.DS_Store`, caches and unknown files. Expected: no findings.

- [ ] **Step 5: Fresh-clone marketplace verification**

Clone `https://github.com/Shinchan-crayon/image-prompt-generator` to a temporary directory after push, validate `.agents/plugins/marketplace.json`, run the official Plugin validator, and confirm all six Skill entrypoints are discoverable.

- [ ] **Step 6: Final architecture review**

Review boundaries, duplicated knowledge, path ownership, approval enforcement, trigger overlap and user-facing cleanliness. Fix only confirmed Critical or Important findings and rerun affected tests.

- [ ] **Step 7: Final commit and push**

```bash
git status --short
git push origin main
```

Expected: clean worktree and remote `main` contains the complete migration.

