#!/usr/bin/env python3
"""检查 Image Prompt Generator 的结构与关键契约。"""

from pathlib import Path
from collections import Counter
import json
import re
import sys


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "SKILL.md",
    "AGENTS.md",
    "README.md",
    "agents/openai.yaml",
    "knowledge/model_language.md",
    "knowledge/image_providers.md",
    "knowledge/article_understanding.md",
    "knowledge/article_classification.md",
    "knowledge/intent_library.md",
    "knowledge/emotion_library.md",
    "knowledge/visual_strategy.md",
    "knowledge/scene_photography.md",
    "knowledge/visual_metaphors.md",
    "knowledge/composition.md",
    "knowledge/editorial_style.md",
    "knowledge/explanatory_visuals.md",
    "knowledge/typography.md",
    "knowledge/color_language.md",
    "knowledge/negative_patterns.md",
    "knowledge/extension_guide.md",
    "rules/core_rules.md",
    "rules/knowledge_routing.md",
    "rules/cover_rules.md",
    "rules/content_rules.md",
    "rules/negative_rules.md",
    "rules/quality_scoring.md",
    "rules/self_check.md",
    "rules/generation_workflow.md",
    "rules/article_workflow.md",
    "rules/batch_generation.md",
    "templates/cover_output.md",
    "templates/content_output.md",
    "templates/prompt_templates.md",
    "templates/image_plan.md",
    "templates/batch_review.md",
    "examples/cover_example.md",
    "examples/content_example.md",
    "examples/library/index.md",
    "examples/library/cases-001-025.md",
    "examples/library/cases-026-050.md",
    "examples/library/cases-051-075.md",
    "examples/library/cases-076-100.md",
    "scripts/configure_api_key.py",
    "scripts/configure_provider.py",
    "scripts/approval_hash.py",
    "scripts/provider_preflight.py",
    "scripts/provider_registry.py",
    "scripts/generate_image.py",
    "scripts/workflow_state.py",
    "scripts/article_workflow.py",
    "scripts/delivery_builder.py",
    "scripts/providers/__init__.py",
    "scripts/providers/base.py",
    "scripts/providers/thinkai.py",
    "scripts/providers/thinkai_nano.py",
    "scripts/providers/volcengine.py",
    "scripts/providers/openai_image.py",
    "scripts/providers/google_image.py",
    "scripts/providers/custom.py",
    "data/image_providers.json",
    "data/workflow-state.schema.json",
    "requirements.txt",
    "config.example.json",
    ".gitignore",
]

ALLOWED_RELEASE_FILES = set(REQUIRED_FILES) | {
    "scripts/check_skill.py",
}

ALLOWED_RUNTIME_FILES = {
    "config.json",
}

ALLOWED_RELEASE_DIRECTORIES = {
    "agents",
    "data",
    "examples",
    "examples/library",
    "knowledge",
    "rules",
    "scripts",
    "scripts/providers",
    "templates",
}

ALLOWED_RUNTIME_DIRECTORIES = {
    "generated",
    "runs",
}

REQUIRED_SKILL_TERMS = [
    "封面模式",
    "正文配图模式",
    "只支持两种模式",
    "文章理解卡",
    "[FACT]",
    "[INFERENCE]",
    "低于 9 分",
    "案例索引",
    "用户审核",
    "ThinkAI",
    "ThinkAI Nano",
    "火山引擎",
    "OpenAI",
    "Google",
    "其他",
    "--approved",
    "--approval-hash",
    "文章级工作流",
    "全部 Prompt",
    "断点恢复",
    "统一交付",
]

REQUIRED_SKILL_LINKS = [
    "AGENTS.md",
    "rules/knowledge_routing.md",
    "knowledge/article_understanding.md",
    "rules/core_rules.md",
    "knowledge/model_language.md",
    "knowledge/image_providers.md",
    "knowledge/scene_photography.md",
    "rules/quality_scoring.md",
    "rules/negative_rules.md",
    "knowledge/composition.md",
    "rules/self_check.md",
    "rules/generation_workflow.md",
    "rules/article_workflow.md",
    "rules/batch_generation.md",
    "rules/cover_rules.md",
    "rules/content_rules.md",
    "templates/cover_output.md",
    "templates/content_output.md",
    "templates/prompt_templates.md",
    "templates/image_plan.md",
    "templates/batch_review.md",
    "examples/library/index.md",
]

REQUIRED_MODEL_TERMS = [
    "GPT Image",
    "Midjourney",
    "Flux",
    "Seedream",
    "Ideogram",
]

REQUIRED_OUTPUT_HEADINGS = [
    "# 图片目标",
    "# 核心观点",
    "# 视觉隐喻",
    "# 构图",
    "# 风格",
    "# Prompt",
    "# Negative Prompt",
    "# 自检",
]

CHINESE_PROMPT_RANGE = (50, 60)
ENGLISH_PROMPT_RANGE = (35, 45)
MINIMUM_CASE_COUNT = 100
EXPECTED_CASE_IDS = list(range(1, 101))
CASE_FIELDS = [
    "文章摘要",
    "模式与目标模型",
    "文章理解",
    "视觉策略",
    "最终 Prompt",
]

REQUIRED_CLASSIFICATIONS = [
    "AI 模型",
    "AI Agent",
    "机器人",
    "芯片",
    "GPU",
    "创业",
    "融资",
    "商业",
    "安全",
    "教程",
    "工作流",
    "赚钱",
    "产品测评",
    "行业分析",
    "公司分析",
    "政策",
    "自动驾驶",
    "医疗 AI",
    "教育 AI",
    "设计 AI",
    "办公 AI",
    "未来趋势",
]

REQUIRED_INTENTS = [
    "新闻",
    "观点",
    "分析",
    "揭秘",
    "教程",
    "案例",
    "采访",
    "评测",
    "预测",
    "商业",
    "营销",
    "产品发布",
    "行业观察",
]

REQUIRED_EMOTIONS = [
    "突破",
    "革命",
    "震惊",
    "竞争",
    "未来",
    "速度",
    "财富",
    "危机",
    "悬疑",
    "教育",
    "风险",
    "安全",
    "合作",
    "成长",
]

ALLOWED_MODES = ["封面模式", "正文配图模式"]

EXPECTED_DEFAULT_SUBJECT_PATHS = {
    "芯片": "实物/过程优先",
    "GPU": "实物/过程优先",
    "政策": "实物/过程优先",
}


def fail(message: str) -> None:
    print(f"[FAIL] {message}")


def extract_inline_prompt(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"最终 Prompt：\s*\n\s*`([^`]+)`", text)
    return match.group(1).strip() if match else ""


def count_chinese_characters(text: str) -> int:
    return len(re.findall(r"[\u3400-\u9fff]", text))


def count_english_words(text: str) -> int:
    prompt_without_parameters = re.sub(r"\s--[a-z-]+\s+\S+", "", text)
    return len(
        re.findall(
            r"[A-Za-z]+(?:[-'][A-Za-z]+)*|\d+",
            prompt_without_parameters,
        )
    )


def require_terms(path: Path, terms: list[str], label: str) -> int:
    if not path.is_file():
        return 0
    text = path.read_text(encoding="utf-8")
    errors = 0
    for term in terms:
        if term not in text:
            fail(f"{label} 缺少条目：{term}")
            errors += 1
    return errors


def parse_cases() -> list[dict[str, str]]:
    cases = []
    for case_file in sorted((ROOT / "examples" / "library").glob("cases-*.md")):
        text = case_file.read_text(encoding="utf-8")
        blocks = re.split(r"(?=^## CASE-\d{3}\b)", text, flags=re.MULTILINE)
        for block in blocks:
            header = re.match(r"^## CASE-(\d{3})\s*$", block, flags=re.MULTILINE)
            if not header:
                continue
            fields = {"id": header.group(1), "file": str(case_file.relative_to(ROOT))}
            for field in CASE_FIELDS:
                match = re.search(
                    rf"^- {re.escape(field)}：(.+)$",
                    block,
                    flags=re.MULTILINE,
                )
                fields[field] = match.group(1).strip() if match else ""
            cases.append(fields)
    return cases


def validate_case_library(cases: list[dict[str, str]]) -> int:
    errors = 0
    case_ids = [int(case["id"]) for case in cases]
    if case_ids != EXPECTED_CASE_IDS:
        fail("案例编号必须从 CASE-001 到 CASE-100 连续且不重复")
        errors += 1

    mode_counts: Counter[str] = Counter()
    model_counts: Counter[str] = Counter()

    for case in cases:
        label = f"CASE-{case['id']}"
        for field in CASE_FIELDS:
            if not case[field]:
                fail(f"{label} 缺少字段：{field}")
                errors += 1

        metadata = case["模式与目标模型"]
        parts = [part.strip() for part in metadata.split("｜")]
        if len(parts) < 2:
            fail(f"{label} 的模式与目标模型格式无效")
            errors += 1
            continue

        mode, model = parts[0], parts[1]
        mode_counts[mode] += 1
        model_counts[model] += 1

        prompt = case["最终 Prompt"].strip("`")
        if model in {"GPT Image", "Seedream"}:
            length = count_chinese_characters(prompt)
            if not CHINESE_PROMPT_RANGE[0] <= length <= CHINESE_PROMPT_RANGE[1]:
                fail(
                    f"{label} 中文 Prompt 应为 "
                    f"{CHINESE_PROMPT_RANGE[0]}–{CHINESE_PROMPT_RANGE[1]} 个汉字，"
                    f"当前为 {length} 个"
                )
                errors += 1
        elif model in {"Midjourney", "Flux", "Ideogram"}:
            length = count_english_words(prompt)
            if not ENGLISH_PROMPT_RANGE[0] <= length <= ENGLISH_PROMPT_RANGE[1]:
                fail(
                    f"{label} 英文 Prompt 应为 "
                    f"{ENGLISH_PROMPT_RANGE[0]}–{ENGLISH_PROMPT_RANGE[1]} 个单词，"
                    f"当前为 {length} 个"
                )
                errors += 1

    if mode_counts != Counter({"封面模式": 50, "正文配图模式": 50}):
        fail(f"案例模式分布应为封面 50、正文 50，当前为 {dict(mode_counts)}")
        errors += 1

    expected_models = Counter({model: 20 for model in REQUIRED_MODEL_TERMS})
    if model_counts != expected_models:
        fail(f"五类模型应各有 20 个案例，当前为 {dict(model_counts)}")
        errors += 1

    return errors


def validate_markdown_links() -> int:
    errors = 0
    link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    for markdown_path in ROOT.rglob("*.md"):
        text = markdown_path.read_text(encoding="utf-8")
        for target in link_pattern.findall(text):
            clean_target = target.split("#", 1)[0].strip()
            if (
                not clean_target
                or clean_target.startswith(("http://", "https://", "mailto:"))
            ):
                continue
            resolved = (markdown_path.parent / clean_target).resolve()
            if not resolved.exists():
                fail(
                    "Markdown 内部链接无效："
                    f"{markdown_path.relative_to(ROOT)} -> {target}"
                )
                errors += 1
    return errors


def validate_knowledge_entrypoints() -> int:
    errors = 0
    for knowledge_path in sorted((ROOT / "knowledge").glob("*.md")):
        text = knowledge_path.read_text(encoding="utf-8")
        if "## 何时读取" not in text:
            fail(f"知识文件缺少渐进加载入口：{knowledge_path.relative_to(ROOT)}")
            errors += 1
    return errors


def validate_structured_knowledge() -> int:
    errors = 0
    contracts = [
        (
            ROOT / "knowledge" / "article_classification.md",
            r"^## \d{2}\. ",
            ["分类说明", "推荐视觉方向", "推荐构图", "推荐风格", "推荐色彩", "常见错误"],
            22,
            "文章分类",
        ),
        (
            ROOT / "knowledge" / "intent_library.md",
            r"^## \d{2}\. ",
            ["判断线索", "视觉任务", "主体与动作", "构图选择", "应避免的误读"],
            13,
            "写作意图",
        ),
        (
            ROOT / "knowledge" / "emotion_library.md",
            r"^## \d{2}\. ",
            ["语义边界", "可执行视觉选择", "光线与色彩", "强度控制", "禁止套路"],
            14,
            "情绪",
        ),
    ]

    for path, heading_pattern, fields, expected_count, label in contracts:
        text = path.read_text(encoding="utf-8")
        blocks = re.split(rf"(?={heading_pattern})", text, flags=re.MULTILINE)
        entries = [
            block
            for block in blocks
            if re.match(heading_pattern, block, flags=re.MULTILINE)
        ]
        if len(entries) != expected_count:
            fail(f"{label}条目应为 {expected_count} 个，当前为 {len(entries)} 个")
            errors += 1
        for entry in entries:
            heading = entry.splitlines()[0]
            for field in fields:
                if f"**{field}**" not in entry:
                    fail(f"{heading} 缺少固定字段：{field}")
                    errors += 1
    return errors


def validate_mode_boundary(skill: str) -> int:
    errors = 0
    declared_modes = re.findall(
        r"^\d+\.\s+\*\*([^*]+模式)\*\*：",
        skill,
        flags=re.MULTILINE,
    )
    if declared_modes != ALLOWED_MODES:
        fail(f"支持范围必须且只能声明两种模式：{ALLOWED_MODES}，当前为 {declared_modes}")
        errors += 1

    mode_headings = re.findall(
        r"^#{1,6}\s+([^#\n]*模式)\s*$",
        skill,
        flags=re.MULTILINE,
    )
    unexpected_headings = [
        heading
        for heading in mode_headings
        if heading not in {"模式判断"}
    ]
    if unexpected_headings:
        fail(f"SKILL.md 出现额外运行模式标题：{unexpected_headings}")
        errors += 1
    if re.search(r"^#{1,6}\s+批量模式\s*$", skill, flags=re.MULTILINE):
        fail("文章工作流不得声明为批量模式")
        errors += 1

    return errors


def validate_article_workflow() -> int:
    errors = 0
    article_path = ROOT / "rules" / "article_workflow.md"
    batch_path = ROOT / "rules" / "batch_generation.md"
    workflow_script_path = ROOT / "scripts" / "article_workflow.py"
    state_script_path = ROOT / "scripts" / "workflow_state.py"
    delivery_script_path = ROOT / "scripts" / "delivery_builder.py"
    schema_path = ROOT / "data" / "workflow-state.schema.json"
    gitignore_path = ROOT / ".gitignore"

    contracts = [
        (
            article_path,
            (
                "不是第三种视觉模式",
                "图片规划",
                "逐张批准",
                "断点恢复",
                "替换完整规划",
                "批准状态失效",
            ),
            "article_workflow.md",
        ),
        (
            batch_path,
            (
                "全量批准门禁",
                "按规划顺序逐张执行",
                "跳过所有已经成功的图片",
                "结果不确定",
                "不得自动",
                "一个生成执行器",
                "SHA-256",
                "全部未删除项目均生成成功",
            ),
            "batch_generation.md",
        ),
        (
            workflow_script_path,
            (
                "all_active_prompts_approved",
                "verify_local",
                "verified-local",
                "GenerationUncertainError",
                "acquire_generation_lock",
                "resolve_item",
                "inspect_image",
                "image_sha256",
                'status="uncertain"',
                'status="generated"',
                "build_delivery",
            ),
            "article_workflow.py",
        ),
        (
            state_script_path,
            (
                "os.replace",
                "canonical_hash",
                "acquire_generation_lock",
                "prompt_version",
                '"phase": "planning"',
                '"complete"',
            ),
            "workflow_state.py",
        ),
        (
            delivery_script_path,
            (
                '"image-map.md"',
                '"prompts.md"',
                '"manifest.json"',
                "_copy_verified_image",
                "image_sha256",
                'state["phase"] != "complete"',
            ),
            "delivery_builder.py",
        ),
    ]
    for path, terms, label in contracts:
        if path.is_file():
            errors += require_terms(path, list(terms), label)

    if schema_path.is_file():
        try:
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            fail(f"workflow-state.schema.json 不是有效 JSON：{exc}")
            errors += 1
        else:
            phases = (
                schema.get("properties", {})
                .get("phase", {})
                .get("enum", [])
            )
            expected_phases = [
                "planning",
                "plan_review",
                "prompt_review",
                "ready",
                "generating",
                "blocked",
                "complete",
            ]
            if phases != expected_phases:
                fail("文章工作流阶段定义不完整或顺序异常")
                errors += 1

    if gitignore_path.is_file():
        ignored = {
            line.strip()
            for line in gitignore_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        }
        if "runs/" not in ignored:
            fail(".gitignore 必须忽略：runs/")
            errors += 1

    return errors


def validate_category_subject_routing() -> int:
    errors = 0
    routing_path = ROOT / "rules" / "knowledge_routing.md"
    skill_path = ROOT / "SKILL.md"
    strategy_path = ROOT / "knowledge" / "visual_strategy.md"
    scene_path = ROOT / "knowledge" / "scene_photography.md"

    if not routing_path.is_file():
        return errors

    routing = routing_path.read_text(encoding="utf-8")
    section_match = re.search(
        r"## 分类主体路径\s*(.*?)(?=\n## |\Z)",
        routing,
        flags=re.DOTALL,
    )
    if not section_match:
        fail("knowledge_routing.md 缺少分类主体路径")
        return errors + 1

    rows = []
    for line in section_match.group(1).splitlines():
        cells = [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]
        if len(cells) != 3 or cells[0] in {"分类", "---"}:
            continue
        if set(cells[0]) == {"-"}:
            continue
        rows.append((cells[0], cells[1], cells[2]))

    categories = [row[0] for row in rows]
    if len(categories) != len(REQUIRED_CLASSIFICATIONS):
        fail(
            "分类主体路径必须覆盖全部 "
            f"{len(REQUIRED_CLASSIFICATIONS)} 类，当前为 {len(categories)} 类"
        )
        errors += 1
    if set(categories) != set(REQUIRED_CLASSIFICATIONS):
        missing = sorted(set(REQUIRED_CLASSIFICATIONS) - set(categories))
        extra = sorted(set(categories) - set(REQUIRED_CLASSIFICATIONS))
        fail(f"分类主体路径集合不匹配，缺少 {missing}，多出 {extra}")
        errors += 1
    if len(categories) != len(set(categories)):
        fail("分类主体路径存在重复分类")
        errors += 1

    allowed_paths = {"人物行动优先", "实物/过程优先", "界面/机制优先"}
    for category, path, override_condition in rows:
        if path not in allowed_paths:
            fail(f"{category} 使用未知主体路径：{path}")
            errors += 1
        if not override_condition:
            fail(f"{category} 缺少主体路径覆盖条件")
            errors += 1

    routes = {category: path for category, path, _ in rows}
    for category, expected_path in EXPECTED_DEFAULT_SUBJECT_PATHS.items():
        if routes.get(category) != expected_path:
            fail(f"{category} 默认应为 {expected_path}，当前为 {routes.get(category)}")
            errors += 1

    section = section_match.group(1)
    if "核心观点可以覆盖分类默认值" not in section:
        fail("分类主体路径必须允许核心观点覆盖分类默认值")
        errors += 1
    if "禁止人物" in section:
        fail("分类主体路径不得把无人物默认写成绝对禁止人物")
        errors += 1

    if skill_path.is_file():
        skill = skill_path.read_text(encoding="utf-8")
        if "优先现实人物与真实场景" in skill:
            fail("SKILL.md 不得保留全局人物优先规则")
            errors += 1

    if strategy_path.is_file():
        strategy = strategy_path.read_text(encoding="utf-8")
        if "按以下顺序选择载体" in strategy:
            fail("visual_strategy.md 不得把三条主体路径写成固定降级顺序")
            errors += 1

    if scene_path.is_file():
        scene = scene_path.read_text(encoding="utf-8")
        for term in ("物体自身的状态变化", "不强制出现人物或手"):
            if term not in scene:
                fail(f"scene_photography.md 缺少无人场景契约：{term}")
                errors += 1

    return errors


def validate_image_connectors() -> int:
    errors = 0
    requirements_path = ROOT / "requirements.txt"
    readme_path = ROOT / "README.md"
    config_example_path = ROOT / "config.example.json"
    registry_path = ROOT / "data" / "image_providers.json"
    configure_path = ROOT / "scripts" / "configure_api_key.py"
    configure_provider_path = ROOT / "scripts" / "configure_provider.py"
    approval_hash_path = ROOT / "scripts" / "approval_hash.py"
    preflight_path = ROOT / "scripts" / "provider_preflight.py"
    generate_path = ROOT / "scripts" / "generate_image.py"
    provider_paths = {
        "thinkai-image2": ROOT / "scripts" / "providers" / "thinkai.py",
        "thinkai-nano": ROOT / "scripts" / "providers" / "thinkai_nano.py",
        "volcengine": ROOT / "scripts" / "providers" / "volcengine.py",
        "openai": ROOT / "scripts" / "providers" / "openai_image.py",
        "google": ROOT / "scripts" / "providers" / "google_image.py",
        "custom": ROOT / "scripts" / "providers" / "custom.py",
    }
    workflow_path = ROOT / "rules" / "generation_workflow.md"
    gitignore_path = ROOT / ".gitignore"

    if not requirements_path.is_file():
        fail("缺少 Python 依赖清单：requirements.txt")
        errors += 1
    else:
        requirements = {
            line.strip()
            for line in requirements_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        }
        if "requests>=2.31,<3" not in requirements:
            fail("requirements.txt 必须声明 requests>=2.31,<3")
            errors += 1

    if readme_path.is_file():
        readme = readme_path.read_text(encoding="utf-8")
        if "python3 -m pip install -r requirements.txt" not in readme:
            fail("README.md 缺少 Python 依赖安装命令")
            errors += 1

    if config_example_path.is_file():
        try:
            config_example = json.loads(config_example_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            fail(f"config.example.json 不是有效 JSON：{exc}")
            errors += 1
        else:
            if config_example.get("base_url") != "https://www.thinkai.tv/v1":
                fail("config.example.json 未保留 ThinkAI 旧版地址")
                errors += 1
            if config_example.get("model") != "gpt-image-2":
                fail("config.example.json 未保留 ThinkAI 旧版模型")
                errors += 1
            if config_example.get("default_provider") != "thinkai-image2":
                fail("config.example.json 默认渠道必须是 thinkai-image2")
                errors += 1
            providers = config_example.get("providers")
            if not isinstance(providers, dict):
                fail("config.example.json 缺少 providers")
                errors += 1
            else:
                for provider_id in (
                    "thinkai-nano",
                    "volcengine",
                    "openai",
                    "google",
                ):
                    value = providers.get(provider_id)
                    if not isinstance(value, dict):
                        fail(f"config.example.json 缺少正式渠道：{provider_id}")
                        errors += 1
                    elif set(value) != {"api_key", "model_alias"}:
                        fail(f"正式渠道示例不得要求 URL 或模型 ID：{provider_id}")
                        errors += 1

    if registry_path.is_file():
        try:
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            fail(f"图片渠道注册表不是有效 JSON：{exc}")
            errors += 1
        else:
            expected_choices = [
                "thinkai-image2",
                "thinkai-nano",
                "volcengine",
                "openai",
                "google",
                "custom",
            ]
            if registry.get("choices") != expected_choices:
                fail("图片渠道菜单必须严格为六项且顺序固定")
                errors += 1
            providers = registry.get("providers")
            if not isinstance(providers, dict) or list(providers) != expected_choices[:5]:
                fail("正式图片渠道注册表集合无效")
                errors += 1
            elif (
                providers.get("thinkai-nano", {})
                .get("models", {})
                .get("recommended")
                != "nano-banana-2"
            ):
                fail("ThinkAI Nano 推荐模型必须由注册表固定为 nano-banana-2")
                errors += 1
            if re.search(r'"api_key"\s*:\s*"[^"]+"', registry_path.read_text(encoding="utf-8")):
                fail("图片渠道注册表不得包含 API Key")
                errors += 1

    if configure_path.is_file():
        configure_script = configure_path.read_text(encoding="utf-8")
        for term in (
            "save_formal_provider_config",
            '"thinkai-image2"',
            "--api-key-stdin",
            "getpass.getpass",
        ):
            if term not in configure_script:
                fail(f"configure_api_key.py 缺少安全配置契约：{term}")
                errors += 1
        if re.search(r'add_argument\(\s*["\']--api-key["\']', configure_script):
            fail("configure_api_key.py 不得通过命令参数接收 API Key")
            errors += 1

    if configure_provider_path.is_file():
        configure_provider = configure_provider_path.read_text(encoding="utf-8")
        for term in (
            "thinkai-image2",
            "thinkai-nano",
            "volcengine",
            "openai",
            "google",
            "custom",
            "providers",
            "0o600",
            "NamedTemporaryFile",
            "os.replace",
            "--api-key-stdin",
            "getpass.getpass",
        ):
            if term not in configure_provider:
                fail(f"configure_provider.py 缺少渠道配置契约：{term}")
                errors += 1
        if re.search(r'add_argument\(\s*["\']--api-key["\']', configure_provider):
            fail("configure_provider.py 不得通过命令参数接收 API Key")
            errors += 1
        for term in ("DEFAULT_PROVIDER = \"thinkai-image2\"", '"status": "configured"'):
            if term not in configure_provider:
                fail(f"configure_provider.py 缺少默认兼容契约：{term}")
                errors += 1

    if approval_hash_path.is_file():
        approval_hash_script = approval_hash_path.read_text(encoding="utf-8")
        for term in (
            "approval_digest",
            "--provider",
            "resolve_provider_size",
            "resolve_provider_quality",
            "不调用图片生成 API",
        ):
            if term not in approval_hash_script:
                fail(f"approval_hash.py 缺少审核哈希契约：{term}")
                errors += 1

    if preflight_path.is_file():
        preflight = preflight_path.read_text(encoding="utf-8")
        for term in (
            "verified-local",
            '"network_request_sent": False',
            '"api_key": "<configured>"',
            "本地检查图片渠道配置",
        ):
            if term not in preflight:
                fail(f"provider_preflight.py 缺少非付费预检契约：{term}")
                errors += 1
        for forbidden in ("requests.", "urllib.request", "subprocess"):
            if forbidden in preflight:
                fail(f"provider_preflight.py 不得发送网络请求：{forbidden}")
                errors += 1

    if generate_path.is_file():
        generate_script = generate_path.read_text(encoding="utf-8")
        for term in (
            "--approved",
            "--approval-hash",
            "--provider",
            'default="thinkai-image2"',
            "approval_digest",
            "compare_digest",
            "request.json",
            "response.json",
            "requests.request",
            "不会自动重试",
            "curl_download",
            "urllib.request",
            "IncompleteRead",
            '"curl", "-L"',
            "inspect_image",
            "extract_adapter_source",
            "redact_snapshot",
            "omitted_values",
            "sanitize_error_detail",
        ):
            if term not in generate_script:
                fail(f"generate_image.py 缺少统一执行契约：{term}")
                errors += 1
        for forbidden in ("MAX_REQUEST_ATTEMPTS", "RETRYABLE_HTTP_STATUS_CODES"):
            if forbidden in generate_script:
                fail(f"付费生成 POST 不得保留自动重试机制：{forbidden}")
                errors += 1
        if 'add_argument("--output-dir"' in generate_script:
            fail("generate_image.py 不得向命令行开放任意输出目录")
            errors += 1

    adapter_terms = {
        "thinkai-image2": (
            "1920x1088",
            "2560x1440",
            '"response_format": "url"',
        ),
        "thinkai-nano": (
            "resolve_model",
            ":generateContent",
            "x-goog-api-key",
            "inlineData",
        ),
        "volcengine": ('"watermark": False', "b64_json", "resolve_model"),
        "openai": ("/images/generations", "b64_json", "SUPPORTED_QUALITIES"),
        "google": ("/interactions", "x-goog-api-key", "model_output"),
        "custom": ("openai-image-compatible", "generic-sync-json-image", "validate_endpoint"),
    }
    for provider_id, path in provider_paths.items():
        if not path.is_file():
            continue
        script = path.read_text(encoding="utf-8")
        for term in adapter_terms[provider_id]:
            if term not in script:
                fail(f"{path.name} 缺少适配器契约：{term}")
                errors += 1

    if workflow_path.is_file():
        workflow = workflow_path.read_text(encoding="utf-8")
        for term in (
            "Prompt 已展示",
            "明确批准",
            "--approved",
            "--approval-hash",
            "--api-key-stdin",
            "生成 POST 只发送一次",
            "不会自动重试",
            "后台没有成功任务",
            "Python URL 读取器",
            "系统 `curl`",
            "实际计费以渠道后台为准",
            "scripts/provider_preflight.py",
            "scripts/approval_hash.py",
            "Google Nano Banana",
            "ThinkAI Nano",
            "其他",
        ):
            if term not in workflow:
                fail(f"generation_workflow.md 缺少审核契约：{term}")
                errors += 1

    if gitignore_path.is_file():
        ignored = {
            line.strip()
            for line in gitignore_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        }
        for item in ("config.json", "generated/", "runs/"):
            if item not in ignored:
                fail(f".gitignore 必须忽略：{item}")
                errors += 1

    return errors


def validate_public_package() -> int:
    errors = 0

    allowed_directories = ALLOWED_RELEASE_DIRECTORIES | ALLOWED_RUNTIME_DIRECTORIES
    allowed_files = ALLOWED_RELEASE_FILES | ALLOWED_RUNTIME_FILES
    for path in sorted(ROOT.rglob("*")):
        relative_path = path.relative_to(ROOT)
        relative = relative_path.as_posix()

        if relative_path.parts[0] == ".git":
            continue

        if relative_path.parts[0] in ALLOWED_RUNTIME_DIRECTORIES:
            continue

        if path.is_dir():
            if relative not in allowed_directories:
                fail(f"发布包包含未授权目录：{relative}")
                errors += 1
            continue

        if relative not in allowed_files:
            fail(f"发布包包含未授权文件：{relative}")
            errors += 1

    return errors


def main() -> int:
    errors = 0

    for relative_path in REQUIRED_FILES:
        if not (ROOT / relative_path).is_file():
            fail(f"缺少文件：{relative_path}")
            errors += 1

    skill_path = ROOT / "SKILL.md"
    if skill_path.is_file():
        skill = skill_path.read_text(encoding="utf-8")
        for term in REQUIRED_SKILL_TERMS:
            if term not in skill:
                fail(f"SKILL.md 缺少关键契约：{term}")
                errors += 1
        for target in REQUIRED_SKILL_LINKS:
            if f"]({target})" not in skill:
                fail(f"SKILL.md 未显式路由资源：{target}")
                errors += 1
        errors += validate_mode_boundary(skill)

    model_path = ROOT / "knowledge" / "model_language.md"
    if model_path.is_file():
        model_knowledge = model_path.read_text(encoding="utf-8")
        for term in REQUIRED_MODEL_TERMS:
            if term not in model_knowledge:
                fail(f"model_language.md 缺少目标模型：{term}")
                errors += 1

    errors += require_terms(
        ROOT / "knowledge" / "article_classification.md",
        REQUIRED_CLASSIFICATIONS,
        "文章分类知识库",
    )
    errors += require_terms(
        ROOT / "knowledge" / "intent_library.md",
        REQUIRED_INTENTS,
        "写作意图知识库",
    )
    errors += require_terms(
        ROOT / "knowledge" / "emotion_library.md",
        REQUIRED_EMOTIONS,
        "情绪知识库",
    )

    cases = parse_cases()
    case_count = len(cases)
    if case_count < MINIMUM_CASE_COUNT:
        fail(f"案例库至少需要 {MINIMUM_CASE_COUNT} 个案例，当前为 {case_count} 个")
        errors += 1
    else:
        errors += validate_case_library(cases)

    scoring_path = ROOT / "rules" / "quality_scoring.md"
    if scoring_path.is_file():
        scoring = scoring_path.read_text(encoding="utf-8")
        for term in ("硬门槛", "10 分", "低于 9 分", "重新设计", "场景或隐喻", "评分锚点"):
            if term not in scoring:
                fail(f"质量评分规则缺少契约：{term}")
                errors += 1

    for template_name in ("cover_output.md", "content_output.md"):
        template_path = ROOT / "templates" / template_name
        if not template_path.is_file():
            continue
        template = template_path.read_text(encoding="utf-8")
        for heading in REQUIRED_OUTPUT_HEADINGS:
            if heading not in template:
                fail(f"{template_name} 缺少输出标题：{heading}")
                errors += 1

    cover_prompt = extract_inline_prompt(ROOT / "examples" / "cover_example.md")
    cover_words = count_english_words(cover_prompt)
    if not ENGLISH_PROMPT_RANGE[0] <= cover_words <= ENGLISH_PROMPT_RANGE[1]:
        fail(
            "封面英文案例应控制在 "
            f"{ENGLISH_PROMPT_RANGE[0]}–{ENGLISH_PROMPT_RANGE[1]} 词，当前为 {cover_words} 词"
        )
        errors += 1
    if "Realistic" not in cover_prompt or "light" not in cover_prompt.lower():
        fail("封面案例必须明确真实摄影风格与光线")
        errors += 1

    content_prompt = extract_inline_prompt(ROOT / "examples" / "content_example.md")
    content_characters = count_chinese_characters(content_prompt)
    if not CHINESE_PROMPT_RANGE[0] <= content_characters <= CHINESE_PROMPT_RANGE[1]:
        fail(
            "正文中文案例应控制在 "
            f"{CHINESE_PROMPT_RANGE[0]}–{CHINESE_PROMPT_RANGE[1]} 个汉字，"
            f"当前为 {content_characters} 个"
        )
        errors += 1
    if "真实摄影" not in content_prompt or "光" not in content_prompt:
        fail("正文案例必须明确真实摄影风格与光线")
        errors += 1

    errors += validate_markdown_links()
    errors += validate_knowledge_entrypoints()
    errors += validate_structured_knowledge()
    errors += validate_category_subject_routing()
    errors += validate_image_connectors()
    errors += validate_article_workflow()
    errors += validate_public_package()

    if errors:
        print(f"\n检查失败：{errors} 个问题。")
        return 1

    print(f"[OK] 结构完整：{len(REQUIRED_FILES)} 个必需文件。")
    print("[OK] 两种运行模式、五类模型适配和统一输出结构均已声明。")
    print("[OK] 100 个案例编号连续、字段完整、模式与模型分布符合契约。")
    print("[OK] SKILL.md 已接入知识路由、文章理解、质量评分和案例索引。")
    print("[OK] Markdown 内部链接有效。")
    print("[OK] 所有知识文件均声明何时读取。")
    print("[OK] 分类、意图与情绪条目字段完整。")
    print("[OK] 22 类主体路径完整，芯片、GPU 与政策默认不强制人物。")
    print("[OK] ThinkAI Image 2 与 ThinkAI Nano 配置、审核门和请求契约均已声明。")
    print("[OK] 文章级工作流具备规划确认、全量审核、顺序生成、恢复与统一交付门禁。")
    print("[OK] 发布包仅包含允许名单内的产品文件和本地运行数据。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
