#!/usr/bin/env python3
"""文章级图片工作流的状态模型与原子持久化。"""

import hashlib
import json
import os
import re
import tempfile
import fcntl
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


SCHEMA_VERSION = 1
RUN_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
ITEM_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
PROMPT_FIELDS = (
    "image_goal",
    "core_viewpoint",
    "visual_metaphor",
    "composition",
    "style",
    "prompt",
    "negative_prompt",
)
WORKFLOW_PHASES = {
    "planning",
    "plan_review",
    "prompt_review",
    "ready",
    "generating",
    "blocked",
    "complete",
}


class WorkflowError(RuntimeError):
    """工作流状态或操作不符合约束。"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _require_text(value: Any, label: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise WorkflowError(f"{label}不能为空。")
    return normalized


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def atomic_write_json(path: Path, value: dict) -> None:
    _atomic_write_text(
        path,
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
    )


def state_path(run_dir: Path) -> Path:
    return Path(run_dir) / "workflow-state.json"


def resolve_run_file(run_dir: Path, relative_path: str, label: str) -> Path:
    raw_path = Path(str(relative_path or "").strip())
    if not raw_path.parts or raw_path.is_absolute():
        raise WorkflowError(f"{label}路径无效。")
    root = Path(run_dir).resolve()
    candidate = (root / raw_path).resolve()
    if candidate == root or root not in candidate.parents:
        raise WorkflowError(f"{label}路径超出任务目录。")
    return candidate


def create_run(
    skill_root: Path,
    article_text: str,
    title: str,
    settings: dict,
    run_id: Optional[str] = None,
) -> Path:
    normalized_article = _require_text(article_text, "文章")
    normalized_title = _require_text(title, "文章标题")
    normalized_settings = {
        "provider": _require_text(settings.get("provider"), "图片渠道"),
        "model": _require_text(settings.get("model"), "渠道模型"),
        "target_model": _require_text(settings.get("target_model"), "目标模型"),
        "quality": _require_text(settings.get("quality", "hd"), "图片质量"),
    }
    selected_run_id = run_id or datetime.now().strftime("%Y%m%d-%H%M%S")
    if not RUN_ID_PATTERN.fullmatch(selected_run_id):
        raise WorkflowError("任务 ID 只能包含小写字母、数字和连字符。")

    run_dir = Path(skill_root) / "runs" / selected_run_id
    if run_dir.exists():
        raise WorkflowError(f"任务已存在：{selected_run_id}")
    run_dir.mkdir(parents=True)
    _atomic_write_text(run_dir / "article.md", normalized_article.rstrip() + "\n")

    timestamp = utc_now()
    state = {
        "schema_version": SCHEMA_VERSION,
        "run_id": selected_run_id,
        "title": normalized_title,
        "phase": "planning",
        "created_at": timestamp,
        "updated_at": timestamp,
        "article": {
            "path": "article.md",
            "sha256": hashlib.sha256(
                normalized_article.encode("utf-8")
            ).hexdigest(),
        },
        "settings": normalized_settings,
        "plan": {
            "path": None,
            "hash": None,
            "approved": False,
            "approved_at": None,
        },
        "items": [],
        "last_error": None,
    }
    atomic_write_json(state_path(run_dir), state)
    return run_dir


def _validate_state(state: dict) -> None:
    if not isinstance(state, dict):
        raise WorkflowError("工作流状态必须是 JSON 对象。")
    if state.get("schema_version") != SCHEMA_VERSION:
        raise WorkflowError("工作流状态版本不受支持。")
    if not RUN_ID_PATTERN.fullmatch(str(state.get("run_id", ""))):
        raise WorkflowError("工作流任务 ID 无效。")
    if state.get("phase") not in WORKFLOW_PHASES:
        raise WorkflowError("工作流阶段无效。")
    if not isinstance(state.get("items"), list):
        raise WorkflowError("工作流项目列表无效。")


def load_state(run_dir: Path) -> dict:
    path = state_path(Path(run_dir))
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise WorkflowError(f"未找到工作流状态：{path}") from exc
    except json.JSONDecodeError as exc:
        raise WorkflowError(f"工作流状态 JSON 无效：{exc}") from exc
    _validate_state(state)
    if Path(run_dir).name != state["run_id"]:
        raise WorkflowError("工作流状态与任务目录不匹配。")
    return state


def save_state(run_dir: Path, state: dict) -> dict:
    state["updated_at"] = utc_now()
    _validate_state(state)
    atomic_write_json(state_path(Path(run_dir)), state)
    return state


def acquire_generation_lock(run_dir: Path) -> int:
    lock_path = Path(run_dir) / ".generation.lock"
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(lock_path, flags, 0o600)
    except OSError as exc:
        raise WorkflowError("无法创建文章生成任务锁。") from exc
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        os.close(descriptor)
        raise WorkflowError("当前文章任务正在生成，请勿重复执行。") from exc
    except OSError:
        os.close(descriptor)
        raise
    return descriptor


def release_generation_lock(descriptor: int) -> None:
    try:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
    finally:
        os.close(descriptor)


def _normalize_plan(plan: dict) -> dict:
    if not isinstance(plan, dict):
        raise WorkflowError("图片规划必须是 JSON 对象。")
    summary = _require_text(plan.get("summary"), "规划摘要")
    raw_items = plan.get("items")
    if not isinstance(raw_items, list) or len(raw_items) < 2:
        raise WorkflowError("文章图片规划至少需要一张封面和一张正文配图。")

    normalized_items = []
    seen_ids = set()
    cover_count = 0
    for order, raw_item in enumerate(raw_items):
        if not isinstance(raw_item, dict):
            raise WorkflowError("图片规划项目必须是 JSON 对象。")
        item_id = _require_text(raw_item.get("id"), "图片项目 ID")
        if not ITEM_ID_PATTERN.fullmatch(item_id):
            raise WorkflowError(f"图片项目 ID 格式无效：{item_id}")
        if item_id in seen_ids:
            raise WorkflowError(f"图片项目 ID 重复：{item_id}")
        seen_ids.add(item_id)

        mode = _require_text(raw_item.get("mode"), "图片模式")
        if mode not in {"cover", "content"}:
            raise WorkflowError(f"图片模式无效：{mode}")
        if mode == "cover":
            cover_count += 1

        normalized_items.append(
            {
                "id": item_id,
                "order": order,
                "mode": mode,
                "heading": _require_text(raw_item.get("heading"), "对应标题"),
                "source": _require_text(raw_item.get("source"), "内容范围"),
                "purpose": _require_text(raw_item.get("purpose"), "图片作用"),
                "ratio": _require_text(raw_item.get("ratio"), "图片比例"),
                "size": str(raw_item.get("size") or "").strip(),
                "style": _require_text(raw_item.get("style"), "画面风格"),
            }
        )
    if cover_count != 1:
        raise WorkflowError("文章图片规划必须且只能包含一张封面。")
    normalized_items.sort(key=lambda item: item["mode"] != "cover")
    for order, item in enumerate(normalized_items):
        item["order"] = order
    return {"summary": summary, "items": normalized_items}


def set_plan(run_dir: Path, plan: dict) -> dict:
    run_dir = Path(run_dir)
    state = load_state(run_dir)
    if state["phase"] in {"generating", "blocked", "complete"}:
        raise WorkflowError("当前阶段不能替换图片规划。")

    normalized = _normalize_plan(plan)
    plan_path = run_dir / "image-plan.json"
    atomic_write_json(plan_path, normalized)
    state["plan"] = {
        "path": "image-plan.json",
        "hash": canonical_hash(normalized),
        "approved": False,
        "approved_at": None,
    }
    state["items"] = [
        {
            **item,
            "status": "active",
            "prompt_path": None,
            "prompt_version": 0,
            "prompt_hash": None,
            "prompt_status": "not_started",
            "approved_at": None,
            "generation": {
                "status": "pending",
                "result": None,
                "error": None,
                "updated_at": None,
            },
        }
        for item in normalized["items"]
    ]
    state["phase"] = "plan_review"
    state["last_error"] = None
    return save_state(run_dir, state)


def approve_plan(run_dir: Path, approved: bool) -> dict:
    run_dir = Path(run_dir)
    if not approved:
        raise WorkflowError("必须确认用户已经明确批准图片规划。")
    state = load_state(run_dir)
    if state["phase"] != "plan_review" or not state["plan"]["path"]:
        raise WorkflowError("当前没有等待审核的图片规划。")
    plan = json.loads(
        resolve_run_file(
            run_dir,
            state["plan"]["path"],
            "图片规划",
        ).read_text(encoding="utf-8")
    )
    current_hash = canonical_hash(plan)
    if current_hash != state["plan"]["hash"]:
        raise WorkflowError("图片规划已发生变化，请重新保存并展示。")
    state["plan"]["approved"] = True
    state["plan"]["approved_at"] = utc_now()
    state["phase"] = "prompt_review"
    return save_state(run_dir, state)


def _find_item(state: dict, item_id: str) -> dict:
    for item in state["items"]:
        if item["id"] == item_id:
            return item
    raise WorkflowError(f"图片项目不存在：{item_id}")


def get_item(state: dict, item_id: str) -> dict:
    return _find_item(state, item_id)


def _normalize_prompt(prompt_data: dict) -> dict:
    if not isinstance(prompt_data, dict):
        raise WorkflowError("Prompt 文件必须是 JSON 对象。")
    return {
        field: _require_text(prompt_data.get(field), f"Prompt 字段 {field}")
        for field in PROMPT_FIELDS
    }


def _prompt_approval_payload(state: dict, item: dict, prompt_data: dict) -> dict:
    return {
        "prompt_data": prompt_data,
        "item": {
            key: item[key]
            for key in ("id", "mode", "ratio", "size", "style", "purpose")
        },
        "generation": state["settings"],
    }


def set_prompt(run_dir: Path, item_id: str, prompt_data: dict) -> dict:
    run_dir = Path(run_dir)
    state = load_state(run_dir)
    if not state["plan"]["approved"]:
        raise WorkflowError("图片规划尚未批准，不能保存 Prompt。")
    if state["phase"] == "blocked":
        raise WorkflowError("工作流存在阻塞项，请先处理后再修改 Prompt。")
    if state["phase"] in {"generating", "complete"}:
        raise WorkflowError("生成开始后不能修改 Prompt。")
    item = _find_item(state, item_id)
    if item["status"] == "removed":
        raise WorkflowError("已删除的图片项目不能保存 Prompt。")
    if item["generation"]["status"] == "generated":
        raise WorkflowError("已生成的图片项目不能修改 Prompt。")

    normalized = _normalize_prompt(prompt_data)
    prompt_path = Path("prompts") / f"{item_id}.json"
    atomic_write_json(run_dir / prompt_path, normalized)
    item["prompt_path"] = prompt_path.as_posix()
    item["prompt_version"] += 1
    item["prompt_hash"] = canonical_hash(
        _prompt_approval_payload(state, item, normalized)
    )
    item["prompt_status"] = "awaiting_review"
    item["approved_at"] = None
    item["generation"] = {
        "status": "pending",
        "result": None,
        "error": None,
        "updated_at": None,
    }
    state["phase"] = "prompt_review"
    state["last_error"] = None
    return save_state(run_dir, state)


def _all_active_prompts_approved(state: dict) -> bool:
    active_items = [item for item in state["items"] if item["status"] == "active"]
    return bool(active_items) and all(
        item["prompt_status"] == "approved" for item in active_items
    )


def all_active_prompts_approved(state: dict) -> bool:
    return _all_active_prompts_approved(state)


def validate_approved_prompt(run_dir: Path, item_id: str) -> dict:
    run_dir = Path(run_dir)
    state = load_state(run_dir)
    item = _find_item(state, item_id)
    if item["status"] != "active" or item["prompt_status"] != "approved":
        raise WorkflowError(f"图片项目尚未批准：{item_id}")
    if not item["prompt_path"] or not item["prompt_hash"]:
        raise WorkflowError(f"图片项目缺少已审核 Prompt：{item_id}")
    try:
        prompt_data = json.loads(
            resolve_run_file(
                run_dir,
                item["prompt_path"],
                "Prompt",
            ).read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkflowError(f"无法读取已审核 Prompt：{item_id}") from exc
    current_hash = canonical_hash(
        _prompt_approval_payload(state, item, prompt_data)
    )
    if current_hash != item["prompt_hash"]:
        raise WorkflowError(f"图片项目审核版本已变化：{item_id}")
    return prompt_data


def approve_prompt(run_dir: Path, item_id: str, approved: bool) -> dict:
    run_dir = Path(run_dir)
    if not approved:
        raise WorkflowError("必须确认用户已经明确批准当前 Prompt。")
    state = load_state(run_dir)
    item = _find_item(state, item_id)
    if item["status"] == "removed":
        raise WorkflowError("已删除的图片项目不能批准。")
    if item["prompt_status"] != "awaiting_review" or not item["prompt_path"]:
        raise WorkflowError("当前图片没有等待审核的 Prompt。")
    prompt_data = json.loads(
        resolve_run_file(
            run_dir,
            item["prompt_path"],
            "Prompt",
        ).read_text(encoding="utf-8")
    )
    current_hash = canonical_hash(
        _prompt_approval_payload(state, item, prompt_data)
    )
    if current_hash != item["prompt_hash"]:
        raise WorkflowError("当前 Prompt 或生成设置已变化，请重新展示并审核。")

    item["prompt_status"] = "approved"
    item["approved_at"] = utc_now()
    state["phase"] = (
        "ready" if _all_active_prompts_approved(state) else "prompt_review"
    )
    return save_state(run_dir, state)


def remove_item(run_dir: Path, item_id: str, approved: bool) -> dict:
    run_dir = Path(run_dir)
    if not approved:
        raise WorkflowError("删除图片项目需要用户明确批准。")
    state = load_state(run_dir)
    if state["phase"] in {"generating", "blocked", "complete"}:
        raise WorkflowError("当前阶段不能删除图片项目。")
    item = _find_item(state, item_id)
    if item["mode"] == "cover":
        raise WorkflowError("封面项目不能从文章工作流中删除。")
    item["status"] = "removed"
    item["prompt_status"] = "removed"
    item["prompt_hash"] = None
    item["approved_at"] = None
    state["phase"] = (
        "ready" if _all_active_prompts_approved(state) else "prompt_review"
    )
    return save_state(run_dir, state)


def mark_generation_result(
    run_dir: Path,
    item_id: str,
    status: str,
    result: Optional[dict] = None,
    error: Optional[str] = None,
) -> dict:
    if status not in {"pending", "sending", "generated", "failed", "uncertain"}:
        raise WorkflowError(f"生成状态无效：{status}")
    run_dir = Path(run_dir)
    state = load_state(run_dir)
    item = _find_item(state, item_id)
    if item["status"] != "active":
        raise WorkflowError("已删除的图片项目不能记录生成结果。")
    item["generation"] = {
        "status": status,
        "result": result,
        "error": str(error or "") or None,
        "updated_at": utc_now(),
    }
    if status in {"failed", "uncertain"}:
        state["phase"] = "blocked"
        state["last_error"] = {
            "item_id": item_id,
            "status": status,
            "message": str(error or ""),
        }
    else:
        active_items = [
            current for current in state["items"] if current["status"] == "active"
        ]
        state["phase"] = (
            "complete"
            if active_items
            and all(
                current["generation"]["status"] == "generated"
                for current in active_items
            )
            else "generating"
        )
        state["last_error"] = None
    return save_state(run_dir, state)
