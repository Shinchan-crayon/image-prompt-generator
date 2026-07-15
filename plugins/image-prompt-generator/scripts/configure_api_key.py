#!/usr/bin/env python3
"""为当前 Skill 保存默认 ThinkAI Image 2 API Key。"""

import argparse
import getpass
import sys
from pathlib import Path

from configure_provider import save_formal_provider_config

DEFAULT_BASE_URL = "https://www.thinkai.tv/v1"
DEFAULT_MODEL = "gpt-image-2"


def save_config(skill_root: Path, api_key: str) -> Path:
    return save_formal_provider_config(
        skill_root,
        "thinkai-image2",
        api_key,
        "recommended",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="配置当前 Image Prompt Generator 的 ThinkAI Image 2 API Key。"
    )
    parser.add_argument(
        "--api-key-stdin",
        action="store_true",
        help="从标准输入读取 API Key，避免出现在进程参数中",
    )
    args = parser.parse_args()

    plugin_root = Path(__file__).resolve().parent.parent
    api_key = (
        sys.stdin.readline().rstrip("\r\n")
        if args.api_key_stdin
        else getpass.getpass("ThinkAI Image 2 API Key: ")
    )
    try:
        config_path = save_config(plugin_root, api_key)
    except ValueError as exc:
        parser.error(str(exc))

    print(f"ThinkAI Image 2 配置已保存：{config_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
