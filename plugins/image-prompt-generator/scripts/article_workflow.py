#!/usr/bin/env python3
"""管理整篇文章的多图规划、审核、批量生成与恢复。"""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Callable, Optional

from delivery_builder import build_delivery
from generate_image import (
    GenerationUncertainError,
    approval_digest,
    generate_approved_image,
    inspect_image,
    load_config,
    resolve_provider_quality,
    resolve_provider_size,
)
from provider_preflight import verify_local
from provider_registry import FORMAL_PROVIDER_IDS
from providers import get_adapter
from workflow_state import (
    WorkflowError,
    acquire_generation_lock,
    all_active_prompts_approved,
    approve_plan,
    approve_prompt,
    canonical_hash,
    create_run,
    get_item,
    load_state,
    mark_generation_result,
    remove_item,
    release_generation_lock,
    resolve_run_file,
    save_state,
    set_plan,
    set_prompt,
    validate_approved_prompt,
)


PLUGIN_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MAX_WORKERS = 3
MAX_MAX_WORKERS = 3


def resolve_run(skill_root: Path, run_id: str) -> Path:
    normalized = str(run_id or "").strip()
    candidate = (Path(skill_root) / "runs" / normalized).resolve()
    runs_root = (Path(skill_root) / "runs").resolve()
    if candidate.parent != runs_root:
        raise WorkflowError("任务 ID 无效。")
    return candidate


def _relative_result(run_dir: Path, result: dict) -> dict:
    normalized = {}
    for key, value in result.items():
        if key.endswith("_path") and isinstance(value, str):
            path = Path(value)
            candidate = path if path.is_absolute() else run_dir / path
            try:
                normalized[key] = (
                    candidate.resolve()
                    .relative_to(run_dir.resolve())
                    .as_posix()
                )
            except ValueError:
                raise WorkflowError("生成结果路径超出当前文章任务目录。")
        else:
            normalized[key] = value
    return normalized


def batch_generate(
    skill_root: Path,
    run_dir: Path,
    execute: bool,
    generator: Callable = generate_approved_image,
    config_loader: Callable = load_config,
    preflight: Callable = verify_local,
    max_workers: int = DEFAULT_MAX_WORKERS,
) -> dict:
    if not 1 <= max_workers <= MAX_MAX_WORKERS:
        raise WorkflowError(
            f"每批图片数量与并发上限必须在 1 到 {MAX_MAX_WORKERS} 之间。"
        )
    run_dir = Path(run_dir)
    lock_descriptor = acquire_generation_lock(run_dir)
    try:
        return _batch_generate_locked(
            skill_root,
            run_dir,
            execute,
            generator,
            config_loader,
            preflight,
            max_workers,
        )
    finally:
        release_generation_lock(lock_descriptor)


def _batch_generate_locked(
    skill_root: Path,
    run_dir: Path,
    execute: bool,
    generator: Callable = generate_approved_image,
    config_loader: Callable = load_config,
    preflight: Callable = verify_local,
    max_workers: int = DEFAULT_MAX_WORKERS,
) -> dict:
    if not execute:
        raise WorkflowError("批量生图必须显式传入 --execute。")
    skill_root = Path(skill_root)
    run_dir = Path(run_dir)
    state = load_state(run_dir)
    if state["phase"] == "blocked":
        raise WorkflowError("工作流存在阻塞项，请先处理后再恢复。")
    if state["phase"] not in {"ready", "generating"}:
        raise WorkflowError("全部 Prompt 尚未批准，禁止批量生图。")
    if not all_active_prompts_approved(state):
        raise WorkflowError("全部 Prompt 尚未批准，禁止批量生图。")

    active_items = [
        item
        for item in sorted(state["items"], key=lambda value: value["order"])
        if item["status"] == "active"
    ]
    interrupted_items = [
        item
        for item in active_items
        if item["generation"]["status"] == "sending"
    ]
    if interrupted_items:
        for item in interrupted_items:
            mark_generation_result(
                run_dir,
                item["id"],
                status="uncertain",
                error="上次执行在付费请求进行中中断，无法确认渠道是否已经受理。",
            )
        interrupted_ids = "、".join(item["id"] for item in interrupted_items)
        raise WorkflowError(
            f"{interrupted_ids} 生成结果不确定，"
            "请先检查所选渠道后台。"
        )

    settings = state["settings"]
    preflight_result = preflight(skill_root, settings["provider"])
    if (
        preflight_result.get("status") != "verified-local"
        or preflight_result.get("network_request_sent") is not False
        or preflight_result.get("provider") != settings["provider"]
        or preflight_result.get("model") != settings["model"]
    ):
        raise WorkflowError("图片渠道本地预检与已审核设置不一致。")

    config = config_loader(skill_root, settings["provider"])
    if config["provider"] != settings["provider"]:
        raise WorkflowError("当前图片渠道与审核版本不一致。")
    if config["model"] != settings["model"]:
        raise WorkflowError("当前渠道模型与审核版本不一致，请重新审核全部 Prompt。")

    pending_jobs = []
    for item in active_items:
        if item["generation"]["status"] == "generated":
            continue
        prompt_data = validate_approved_prompt(run_dir, item["id"])
        size = resolve_provider_size(config["provider"], item["size"] or None)
        quality = resolve_provider_quality(
            config["provider"],
            settings["quality"],
        )
        digest = approval_digest(
            prompt_data["prompt"],
            provider=config["provider"],
            model=config["model"],
            size=size,
            quality=quality,
        )
        pending_jobs.append(
            {
                "item": item,
                "prompt": prompt_data["prompt"],
                "approval_hash": digest,
                "output_dir": run_dir / "artifacts" / item["id"],
            }
        )

    if not pending_jobs:
        return load_state(run_dir)

    def run_job(job: dict) -> dict:
        return generator(
            skill_root=skill_root,
            provider=config["provider"],
            prompt=job["prompt"],
            approval_hash=job["approval_hash"],
            size=job["item"]["size"] or None,
            quality=settings["quality"],
            output_dir=job["output_dir"],
            allowed_output_root=run_dir / "artifacts",
        )

    failures = []
    for wave_start in range(0, len(pending_jobs), max_workers):
        wave = pending_jobs[wave_start:wave_start + max_workers]
        futures = {}
        with ThreadPoolExecutor(
            max_workers=len(wave),
            thread_name_prefix="image-prompt-generator",
        ) as executor:
            for job in wave:
                mark_generation_result(
                    run_dir,
                    job["item"]["id"],
                    status="sending",
                )
                futures[executor.submit(run_job, job)] = job

            for future in as_completed(futures):
                job = futures[future]
                item_id = job["item"]["id"]
                try:
                    result = future.result()
                except GenerationUncertainError as exc:
                    mark_generation_result(
                        run_dir,
                        item_id,
                        status="uncertain",
                        error=str(exc),
                    )
                    failures.append(
                        WorkflowError(
                            f"{item_id} 生成结果不确定，批次已停止。"
                        )
                    )
                except Exception as exc:
                    mark_generation_result(
                        run_dir,
                        item_id,
                        status="failed",
                        error=str(exc),
                    )
                    failures.append(
                        WorkflowError(
                            f"{item_id} 生成失败，批次已停止：{exc}"
                        )
                    )
                else:
                    mark_generation_result(
                        run_dir,
                        item_id,
                        status="generated",
                        result=_relative_result(run_dir, result),
                    )

        if failures:
            break

    if failures:
        raise failures[0]

    return load_state(run_dir)


def retry_item(
    run_dir: Path,
    item_id: str,
    approved: bool,
    backend_checked: bool = False,
) -> dict:
    if not approved:
        raise WorkflowError("重新发送付费生成请求需要用户明确批准。")
    run_dir = Path(run_dir)
    state = load_state(run_dir)
    item = get_item(state, item_id)
    status = item["generation"]["status"]
    if status not in {"failed", "uncertain"}:
        raise WorkflowError("当前图片项目不需要重试。")
    if status == "uncertain" and not backend_checked:
        raise WorkflowError("结果不确定时必须先检查所选渠道后台。")
    artifact_root = run_dir / "artifacts"
    raw_artifact_dir = artifact_root / item_id
    if artifact_root.is_symlink() or raw_artifact_dir.is_symlink():
        raise WorkflowError("图片产物目录不能使用符号链接，不能安全重试。")
    artifact_dir = resolve_run_file(
        run_dir,
        (Path("artifacts") / item_id).as_posix(),
        "图片产物",
    )
    if artifact_dir.parent != artifact_root.resolve():
        raise WorkflowError("图片产物路径超出预期目录，不能安全重试。")
    if artifact_dir.exists():
        if not artifact_dir.is_dir():
            raise WorkflowError("图片产物路径不是目录，不能安全重试。")
        shutil.rmtree(artifact_dir)
    item["generation"] = {
        "status": "pending",
        "result": None,
        "error": None,
        "updated_at": None,
    }
    remaining_blocker = next(
        (
            current
            for current in state["items"]
            if current["status"] == "active"
            and current["generation"]["status"] in {"failed", "uncertain"}
        ),
        None,
    )
    if remaining_blocker:
        state["phase"] = "blocked"
        state["last_error"] = {
            "item_id": remaining_blocker["id"],
            "status": remaining_blocker["generation"]["status"],
            "message": remaining_blocker["generation"]["error"] or "",
        }
    else:
        state["last_error"] = None
        state["phase"] = (
            "ready"
            if all_active_prompts_approved(state)
            else "prompt_review"
        )
    return save_state(run_dir, state)


def resolve_item(
    run_dir: Path,
    item_id: str,
    approved: bool,
    backend_checked: bool,
) -> dict:
    if not approved or not backend_checked:
        raise WorkflowError(
            "接纳不确定结果前，必须检查渠道后台并获得用户明确批准。"
        )
    run_dir = Path(run_dir)
    state = load_state(run_dir)
    item = get_item(state, item_id)
    if item["generation"]["status"] != "uncertain":
        raise WorkflowError("只有结果不确定的图片项目可以接纳现有产物。")

    raw_artifact_dir = run_dir / "artifacts" / item_id
    if raw_artifact_dir.is_symlink():
        raise WorkflowError("图片产物目录不能使用符号链接。")
    artifact_dir = resolve_run_file(
        run_dir,
        (Path("artifacts") / item_id).as_posix(),
        "图片产物",
    )
    images = [
        path
        for path in artifact_dir.iterdir()
        if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    ] if artifact_dir.is_dir() else []
    if len(images) != 1:
        raise WorkflowError("现有产物必须包含且只能包含一张可识别图片。")
    request_path = artifact_dir / "request.json"
    response_path = artifact_dir / "response.json"
    artifact_files = [request_path, response_path, images[0]]
    if any(path.is_symlink() for path in artifact_files):
        raise WorkflowError("图片产物必须位于当前任务目录，不能使用符号链接。")
    try:
        request_snapshot = json.loads(request_path.read_text(encoding="utf-8"))
        json.loads(response_path.read_text(encoding="utf-8"))
        _, width, height = inspect_image(images[0].read_bytes())
    except (OSError, json.JSONDecodeError, ValueError, RuntimeError) as exc:
        raise WorkflowError("现有产物不完整或无法验证，不能接纳。") from exc

    prompt_data = validate_approved_prompt(run_dir, item_id)
    settings = state["settings"]
    skill_root = run_dir.parent.parent
    config = load_config(skill_root, settings["provider"])
    if (
        config["provider"] != settings["provider"]
        or config["model"] != settings["model"]
    ):
        raise WorkflowError("当前图片渠道与审核版本不一致，不能接纳现有产物。")
    size = resolve_provider_size(config["provider"], item["size"] or None)
    quality = resolve_provider_quality(config["provider"], settings["quality"])
    adapter_id = (
        config["provider"]
        if config["provider"] in FORMAL_PROVIDER_IDS
        else "custom"
    )
    expected_request = get_adapter(adapter_id).build_request(
        config,
        prompt_data["prompt"],
        size,
        quality,
    )
    if (
        not isinstance(request_snapshot, dict)
        or canonical_hash(request_snapshot)
        != canonical_hash(expected_request["body"])
    ):
        raise WorkflowError("现有产物与当前 Prompt 审核版本不一致，不能接纳。")

    result = {
        "image_path": images[0].relative_to(run_dir.resolve()).as_posix(),
        "request_path": request_path.relative_to(run_dir.resolve()).as_posix(),
        "response_path": response_path.relative_to(run_dir.resolve()).as_posix(),
        "image_sha256": hashlib.sha256(images[0].read_bytes()).hexdigest(),
        "actual_size": f"{width}x{height}",
        "image_source": "recovered-local",
    }
    return mark_generation_result(
        run_dir,
        item_id,
        status="generated",
        result=result,
    )


def initialize_run(
    skill_root: Path,
    article_text: str,
    title: str,
    provider: str,
    target_model: Optional[str],
    quality: str,
    run_id: Optional[str],
) -> Path:
    config = load_config(Path(skill_root), provider)
    return create_run(
        Path(skill_root),
        article_text,
        title,
        {
            "provider": config["provider"],
            "model": config["model"],
            "target_model": target_model or config["model"],
            "quality": quality,
        },
        run_id,
    )


def _read_json(path: str) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkflowError(f"无法读取 JSON 文件：{path}：{exc}") from exc


def _summary(state: dict) -> dict:
    return {
        "run_id": state["run_id"],
        "title": state["title"],
        "phase": state["phase"],
        "plan_approved": state["plan"]["approved"],
        "items": [
            {
                "id": item["id"],
                "mode": item["mode"],
                "heading": item["heading"],
                "status": item["status"],
                "prompt_status": item["prompt_status"],
                "generation_status": item["generation"]["status"],
            }
            for item in state["items"]
        ],
        "last_error": state["last_error"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Image Prompt Generator 文章级工作流",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="创建文章任务")
    article_group = init_parser.add_mutually_exclusive_group(required=True)
    article_group.add_argument("--article-file")
    article_group.add_argument("--article-stdin", action="store_true")
    init_parser.add_argument("--title", required=True)
    init_parser.add_argument("--provider", default="thinkai-image2")
    init_parser.add_argument("--target-model")
    init_parser.add_argument("--quality", default="hd")
    init_parser.add_argument("--run-id")

    for command in ("set-plan", "approve-plan", "status", "generate", "deliver"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument("--run", required=True)
        if command == "set-plan":
            command_parser.add_argument("--plan-file", required=True)
        elif command == "approve-plan":
            command_parser.add_argument("--approved", action="store_true", required=True)
        elif command == "generate":
            command_parser.add_argument("--execute", action="store_true", required=True)
            command_parser.add_argument(
                "--max-workers",
                type=int,
                default=DEFAULT_MAX_WORKERS,
                help=(
                    "每批图片数量与并发上限，"
                    f"默认 {DEFAULT_MAX_WORKERS}，范围 1-{MAX_MAX_WORKERS}"
                ),
            )

    prompt_parser = subparsers.add_parser("set-prompt")
    prompt_parser.add_argument("--run", required=True)
    prompt_parser.add_argument("--item", required=True)
    prompt_parser.add_argument("--prompt-file", required=True)

    approve_parser = subparsers.add_parser("approve-prompt")
    approve_parser.add_argument("--run", required=True)
    approve_parser.add_argument("--item", required=True)
    approve_parser.add_argument("--approved", action="store_true", required=True)

    remove_parser = subparsers.add_parser("remove-item")
    remove_parser.add_argument("--run", required=True)
    remove_parser.add_argument("--item", required=True)
    remove_parser.add_argument("--approved", action="store_true", required=True)

    retry_parser = subparsers.add_parser("retry-item")
    retry_parser.add_argument("--run", required=True)
    retry_parser.add_argument("--item", required=True)
    retry_parser.add_argument("--approved", action="store_true", required=True)
    retry_parser.add_argument("--backend-checked", action="store_true")

    resolve_parser = subparsers.add_parser("resolve-item")
    resolve_parser.add_argument("--run", required=True)
    resolve_parser.add_argument("--item", required=True)
    resolve_parser.add_argument("--approved", action="store_true", required=True)
    resolve_parser.add_argument("--backend-checked", action="store_true", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "init":
            article_text = (
                sys.stdin.read()
                if args.article_stdin
                else Path(args.article_file).read_text(encoding="utf-8")
            )
            run_dir = initialize_run(
                PLUGIN_ROOT,
                article_text,
                args.title,
                args.provider,
                args.target_model,
                args.quality,
                args.run_id,
            )
            result = {"run_id": run_dir.name, "run_dir": str(run_dir)}
        else:
            run_dir = resolve_run(PLUGIN_ROOT, args.run)
            if args.command == "set-plan":
                state = set_plan(run_dir, _read_json(args.plan_file))
            elif args.command == "approve-plan":
                state = approve_plan(run_dir, args.approved)
            elif args.command == "set-prompt":
                state = set_prompt(
                    run_dir,
                    args.item,
                    _read_json(args.prompt_file),
                )
            elif args.command == "approve-prompt":
                state = approve_prompt(run_dir, args.item, args.approved)
            elif args.command == "remove-item":
                state = remove_item(run_dir, args.item, args.approved)
            elif args.command == "retry-item":
                state = retry_item(
                    run_dir,
                    args.item,
                    args.approved,
                    args.backend_checked,
                )
            elif args.command == "resolve-item":
                state = resolve_item(
                    run_dir,
                    args.item,
                    args.approved,
                    args.backend_checked,
                )
            elif args.command == "generate":
                state = batch_generate(
                    PLUGIN_ROOT,
                    run_dir,
                    args.execute,
                    max_workers=args.max_workers,
                )
            elif args.command == "deliver":
                result = build_delivery(run_dir)
                print(json.dumps(result, ensure_ascii=False, indent=2))
                return 0
            else:
                state = load_state(run_dir)
            result = _summary(state)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
