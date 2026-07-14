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
    "templates/cover_output.md",
    "templates/content_output.md",
    "templates/prompt_templates.md",
    "examples/cover_example.md",
    "examples/content_example.md",
    "examples/library/index.md",
    "examples/library/cases-001-025.md",
    "examples/library/cases-026-050.md",
    "examples/library/cases-051-075.md",
    "examples/library/cases-076-100.md",
    "scripts/configure_api_key.py",
    "scripts/generate_image.py",
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
    "examples",
    "examples/library",
    "knowledge",
    "rules",
    "scripts",
    "templates",
}

ALLOWED_RUNTIME_DIRECTORIES = {
    "generated",
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
    "--approved",
    "--approval-hash",
]

REQUIRED_SKILL_LINKS = [
    "AGENTS.md",
    "rules/knowledge_routing.md",
    "knowledge/article_understanding.md",
    "rules/core_rules.md",
    "knowledge/model_language.md",
    "knowledge/scene_photography.md",
    "rules/quality_scoring.md",
    "rules/negative_rules.md",
    "knowledge/composition.md",
    "rules/self_check.md",
    "rules/generation_workflow.md",
    "rules/cover_rules.md",
    "rules/content_rules.md",
    "templates/cover_output.md",
    "templates/content_output.md",
    "templates/prompt_templates.md",
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


def validate_thinkai_connector() -> int:
    errors = 0
    requirements_path = ROOT / "requirements.txt"
    readme_path = ROOT / "README.md"
    config_example_path = ROOT / "config.example.json"
    configure_path = ROOT / "scripts" / "configure_api_key.py"
    generate_path = ROOT / "scripts" / "generate_image.py"
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
            expected = {
                "base_url": "https://www.thinkai.tv/v1",
                "model": "gpt-image-2",
                "api_key": "",
            }
            if config_example != expected:
                fail(f"ThinkAI 配置示例不符合固定契约：{config_example}")
                errors += 1

    if configure_path.is_file():
        configure_script = configure_path.read_text(encoding="utf-8")
        for term in (
            "config.json",
            "0o600",
            "api_key",
            "gpt-image-2",
            "NamedTemporaryFile",
            "os.replace",
            "--api-key-stdin",
            "getpass.getpass",
        ):
            if term not in configure_script:
                fail(f"configure_api_key.py 缺少安全配置契约：{term}")
                errors += 1
        if re.search(r'add_argument\(\s*["\']--api-key["\']', configure_script):
            fail("configure_api_key.py 不得通过命令参数接收 API Key")
            errors += 1

    if generate_path.is_file():
        generate_script = generate_path.read_text(encoding="utf-8")
        for term in (
            "--approved",
            "--approval-hash",
            "approval_digest",
            "compare_digest",
            "/images/generations",
            '"response_format": "url"',
            "1920x1088",
            "2560x1440",
            "request.json",
            "response.json",
            "requests.request",
            "MAX_REQUEST_ATTEMPTS",
            "RETRYABLE_HTTP_STATUS_CODES",
            "curl_download",
            "urllib.request",
            "IncompleteRead",
            '"curl", "-L"',
        ):
            if term not in generate_script:
                fail(f"generate_image.py 缺少 ThinkAI 执行契约：{term}")
                errors += 1
        if 'add_argument("--output-dir"' in generate_script:
            fail("generate_image.py 不得向命令行开放任意输出目录")
            errors += 1

    if workflow_path.is_file():
        workflow = workflow_path.read_text(encoding="utf-8")
        for term in (
            "Prompt 已展示",
            "明确批准",
            "--approved",
            "--approval-hash",
            "--api-key-stdin",
            "最多尝试三次",
            "Python URL 读取器",
            "系统 `curl`",
            "实际计费以 ThinkAI 后台为准",
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
        for item in ("config.json", "generated/"):
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
    errors += validate_thinkai_connector()
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
    print("[OK] ThinkAI 独立配置、审核门、请求契约和产物留档均已声明。")
    print("[OK] 发布包仅包含允许名单内的产品文件和本地运行数据。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
