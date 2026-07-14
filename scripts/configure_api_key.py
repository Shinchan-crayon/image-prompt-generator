#!/usr/bin/env python3
"""为当前 Skill 保存 ThinkAI API Key。"""

import argparse
import getpass
import json
import os
import sys
import tempfile
from pathlib import Path


DEFAULT_BASE_URL = "https://www.thinkai.tv/v1"
DEFAULT_MODEL = "gpt-image-2"


def save_config(skill_root: Path, api_key: str) -> Path:
    normalized_key = api_key.strip()
    if not normalized_key:
        raise ValueError("ThinkAI API Key 不能为空。")

    config_path = skill_root / "config.json"
    config = {
        "base_url": DEFAULT_BASE_URL,
        "model": DEFAULT_MODEL,
        "api_key": normalized_key,
    }

    skill_root.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=skill_root,
            prefix=".config.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
            os.chmod(temp_path, 0o600)
            json.dump(config, temp_file, ensure_ascii=False, indent=2)
            temp_file.write("\n")
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_path, config_path)
        os.chmod(config_path, 0o600)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()
    return config_path


def main() -> int:
    parser = argparse.ArgumentParser(description="配置当前 Image Prompt Generator 的 ThinkAI API Key。")
    parser.add_argument(
        "--api-key-stdin",
        action="store_true",
        help="从标准输入读取 API Key，避免出现在进程参数中",
    )
    args = parser.parse_args()

    skill_root = Path(__file__).resolve().parent.parent
    api_key = (
        sys.stdin.readline().rstrip("\r\n")
        if args.api_key_stdin
        else getpass.getpass("ThinkAI API Key: ")
    )
    try:
        config_path = save_config(skill_root, api_key)
    except ValueError as exc:
        parser.error(str(exc))

    print(f"ThinkAI 配置已保存：{config_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
