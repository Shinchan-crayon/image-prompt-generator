#!/usr/bin/env python3
"""为已完成的文章图片任务生成统一交付包。"""

import hashlib
import json
import os
import shutil
import stat
import tempfile
from pathlib import Path

from workflow_state import (
    WorkflowError,
    load_state,
    resolve_run_file,
    utc_now,
    validate_approved_prompt,
)


def _source_image(run_dir: Path, result: dict) -> Path:
    raw_path = str(result.get("image_path") or "").strip()
    if not raw_path:
        raise WorkflowError("生成结果缺少图片路径。")
    path = Path(raw_path)
    if path.is_absolute():
        try:
            path = path.resolve().relative_to(run_dir.resolve())
        except ValueError as exc:
            raise WorkflowError("生成图片路径超出当前文章任务目录。") from exc
    path = resolve_run_file(run_dir, path.as_posix(), "生成图片")
    if not path.is_file():
        raise WorkflowError(f"生成图片不存在：{path}")
    return path


def _copy_verified_image(source: Path, destination: Path, expected_hash: str) -> None:
    normalized_hash = str(expected_hash or "").strip().lower()
    if len(normalized_hash) != 64 or any(
        character not in "0123456789abcdef" for character in normalized_hash
    ):
        raise WorkflowError("生成结果缺少有效的图片内容哈希。")

    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        source_fd = os.open(source, flags)
    except OSError as exc:
        raise WorkflowError("无法安全读取生成图片。") from exc
    digest = hashlib.sha256()
    try:
        if not stat.S_ISREG(os.fstat(source_fd).st_mode):
            raise WorkflowError("生成图片不是普通文件。")
        with os.fdopen(source_fd, "rb") as source_handle:
            source_fd = None
            with destination.open("xb") as destination_handle:
                while True:
                    chunk = source_handle.read(1024 * 1024)
                    if not chunk:
                        break
                    digest.update(chunk)
                    destination_handle.write(chunk)
    finally:
        if source_fd is not None:
            os.close(source_fd)

    if digest.hexdigest() != normalized_hash:
        destination.unlink(missing_ok=True)
        raise WorkflowError("生成后的图片内容已发生变化，不能创建正式交付包。")


def build_delivery(run_dir: Path) -> dict:
    run_dir = Path(run_dir)
    state = load_state(run_dir)
    active_items = [
        item
        for item in sorted(state["items"], key=lambda value: value["order"])
        if item["status"] == "active"
    ]
    if state["phase"] != "complete" or not active_items or not all(
        item["generation"]["status"] == "generated" for item in active_items
    ):
        raise WorkflowError("全部图片尚未生成成功，不能创建正式交付包。")

    temp_dir = Path(tempfile.mkdtemp(prefix=".delivery-", dir=run_dir))
    manifest_items = []
    map_lines = [
        "# 图片与文章段落映射",
        "",
        f"- 文章：{state['title']}",
        f"- 任务：{state['run_id']}",
        "",
    ]
    prompt_lines = [
        "# 最终审核 Prompt",
        "",
        f"- 文章：{state['title']}",
        "",
    ]

    try:
        content_index = 1
        for item in active_items:
            result = item["generation"]["result"] or {}
            source = _source_image(run_dir, result)
            suffix = source.suffix.lower() or ".png"
            if item["mode"] == "cover":
                filename = f"00-cover{suffix}"
            else:
                filename = f"{content_index:02d}-{item['id']}{suffix}"
                content_index += 1
            _copy_verified_image(
                source,
                temp_dir / filename,
                result.get("image_sha256"),
            )

            prompt_data = validate_approved_prompt(run_dir, item["id"])
            map_lines.extend(
                [
                    f"## {filename}",
                    "",
                    f"- 类型：{'封面' if item['mode'] == 'cover' else '正文配图'}",
                    f"- 对应位置：{item['source']}",
                    f"- 对应标题：{item['heading']}",
                    f"- 图片作用：{item['purpose']}",
                    "",
                ]
            )
            prompt_lines.extend(
                [
                    f"## {filename}",
                    "",
                    f"**Prompt**：{prompt_data['prompt']}",
                    "",
                    f"**Negative Prompt**：{prompt_data['negative_prompt']}",
                    "",
                ]
            )
            manifest_items.append(
                {
                    "id": item["id"],
                    "mode": item["mode"],
                    "heading": item["heading"],
                    "source": item["source"],
                    "purpose": item["purpose"],
                    "ratio": item["ratio"],
                    "size": item["size"],
                    "style": item["style"],
                    "image": filename,
                    "image_sha256": result.get("image_sha256"),
                    "actual_size": result.get("actual_size"),
                    "prompt_version": item["prompt_version"],
                    "prompt_hash": item["prompt_hash"],
                }
            )

        (temp_dir / "image-map.md").write_text(
            "\n".join(map_lines).rstrip() + "\n",
            encoding="utf-8",
        )
        (temp_dir / "prompts.md").write_text(
            "\n".join(prompt_lines).rstrip() + "\n",
            encoding="utf-8",
        )
        manifest = {
            "schema_version": 1,
            "run_id": state["run_id"],
            "title": state["title"],
            "created_at": utc_now(),
            "provider": state["settings"]["provider"],
            "model": state["settings"]["model"],
            "target_model": state["settings"]["target_model"],
            "quality": state["settings"]["quality"],
            "items": manifest_items,
        }
        (temp_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        delivery_dir = run_dir / "delivery"
        if delivery_dir.exists():
            shutil.rmtree(delivery_dir)
        os.replace(temp_dir, delivery_dir)
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    return {
        "run_id": state["run_id"],
        "delivery_dir": str(delivery_dir),
        "image_count": len(manifest_items),
        "manifest_path": str(delivery_dir / "manifest.json"),
    }
