#!/usr/bin/env python3
"""在用户明确批准 Prompt 后，通过 ThinkAI 生成并下载图片。"""

import argparse
import hashlib
import hmac
import http.client
import json
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import requests
except ModuleNotFoundError:
    print(
        "缺少 Python 依赖 requests。请在 Skill 根目录运行："
        "python3 -m pip install -r requirements.txt",
        file=sys.stderr,
    )
    raise SystemExit(2)


SIZE_ALIASES = {
    "1k": "1920x1088",
    "2k": "2560x1440",
}
DEFAULT_BASE_URL = "https://www.thinkai.tv/v1"
DEFAULT_MODEL = "gpt-image-2"
CONNECT_TIMEOUT_SECONDS = 30
READ_TIMEOUT_SECONDS = 900


def load_config(skill_root: Path) -> dict:
    config_path = skill_root / "config.json"
    if not config_path.is_file():
        raise RuntimeError(
            f"未找到 {config_path}。请先运行 "
            "python3 scripts/configure_api_key.py。"
        )

    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"无法读取 ThinkAI 配置：{exc}") from exc

    api_key = str(config.get("api_key", "")).strip()
    if not api_key:
        raise RuntimeError("ThinkAI API Key 为空，请重新运行配置脚本。")
    if "\r" in api_key or "\n" in api_key:
        raise RuntimeError("ThinkAI API Key 格式无效，请重新运行配置脚本。")
    if config.get("base_url") != DEFAULT_BASE_URL or config.get("model") != DEFAULT_MODEL:
        raise RuntimeError("ThinkAI 地址和模型是固定契约，请重新运行配置脚本恢复配置。")

    return {
        "base_url": DEFAULT_BASE_URL,
        "model": DEFAULT_MODEL,
        "api_key": api_key,
    }


def resolve_size(raw_size: str) -> str:
    normalized = raw_size.strip().lower()
    return SIZE_ALIASES.get(normalized, raw_size.strip())


def validate_prompt(prompt: str) -> str:
    normalized = prompt.strip()
    if not normalized:
        raise ValueError("已审核 Prompt 不能为空。")
    return normalized


def approval_digest(prompt: str) -> str:
    return hashlib.sha256(validate_prompt(prompt).encode("utf-8")).hexdigest()


def validate_approval(prompt: str, expected_digest: str) -> str:
    normalized = validate_prompt(prompt)
    if not hmac.compare_digest(approval_digest(normalized), expected_digest.strip().lower()):
        raise ValueError("当前 Prompt 与用户审核通过的版本不一致，请重新展示并审核。")
    return normalized


def build_generation_body(
    model: str,
    prompt: str,
    size: str,
    quality: str,
    n: int,
) -> dict:
    return {
        "model": model,
        "prompt": prompt,
        "n": n,
        "size": size,
        "quality": quality,
        "response_format": "url",
    }


def build_request_context(config: dict) -> tuple[str, str, dict]:
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json",
        "Accept": "*/*",
        "User-Agent": "curl/8.7.1",
    }
    return config["base_url"], config["model"], headers


def request_json(
    method: str,
    url: str,
    headers: dict,
    body: Optional[dict] = None,
) -> dict:
    try:
        response = requests.request(
            method,
            url,
            json=body,
            headers=headers,
            timeout=(CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS),
        )
        response.raise_for_status()
        payload = response.text
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        detail = exc.response.text if exc.response is not None else str(exc)
        raise RuntimeError(
            f"ThinkAI 请求失败，HTTP {status_code}：{detail}。"
            "付费生成请求不会自动重试。"
        ) from exc
    except (
        requests.ConnectionError,
        requests.Timeout,
        requests.exceptions.ChunkedEncodingError,
    ) as exc:
        raise RuntimeError(
            "ThinkAI 生成请求结果不确定，服务端可能已受理并计费。"
            "为避免重复生成，本工具不会自动重试；"
            "请先在 ThinkAI 后台确认任务记录，再决定是否重新执行。"
            f"原始错误：{exc}"
        ) from exc

    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"ThinkAI 返回了非 JSON 响应：{payload[:500]}"
        ) from exc


def request_generation(config: dict, body: dict) -> dict:
    base_url, _, headers = build_request_context(config)
    data = request_json(
        "POST",
        f"{base_url}/images/generations",
        headers,
        body,
    )
    if "data" not in data or not data["data"] or "url" not in data["data"][0]:
        raise RuntimeError(
            f"ThinkAI 返回结构异常：{json.dumps(data, ensure_ascii=False)}"
        )
    return data


def curl_download(image_url: str) -> bytes:
    curl = subprocess.run(
        ["curl", "-L", "--fail", "--silent", "--show-error", image_url],
        capture_output=True,
        check=False,
        timeout=600,
    )
    if curl.returncode == 0 and curl.stdout:
        return curl.stdout
    stderr = curl.stderr.decode("utf-8", errors="replace").strip()
    if stderr:
        raise RuntimeError(f"curl 图片下载失败：{stderr}")
    raise RuntimeError(f"curl 图片下载失败，退出码 {curl.returncode}")


def download_image(image_url: str) -> bytes:
    req = urllib.request.Request(
        image_url,
        headers={
            "Accept": "*/*",
            "User-Agent": "curl/8.7.1",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"图片下载失败，HTTP {exc.code}：{detail}") from exc
    except http.client.IncompleteRead as exc:
        try:
            return curl_download(image_url)
        except RuntimeError as curl_exc:
            raise RuntimeError(f"图片下载不完整：{exc}；{curl_exc}") from exc
    except urllib.error.URLError as exc:
        try:
            return curl_download(image_url)
        except RuntimeError as curl_exc:
            raise RuntimeError(f"图片下载失败：{exc}；{curl_exc}") from exc


def get_png_dimensions(png_bytes: bytes) -> tuple[int, int]:
    if png_bytes[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError("ThinkAI 返回的图片不是有效 PNG。")
    width = int.from_bytes(png_bytes[16:20], "big")
    height = int.from_bytes(png_bytes[20:24], "big")
    return width, height


def write_artifacts(
    skill_root: Path,
    request_body: dict,
    response_json: dict,
    output_dir: Optional[str],
) -> dict:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target_dir = (
        Path(output_dir).expanduser().resolve()
        if output_dir
        else skill_root / "generated" / stamp
    )
    target_dir.mkdir(parents=True, exist_ok=True)

    image_url = response_json["data"][0]["url"]
    image_path = target_dir / "image.png"
    request_path = target_dir / "request.json"
    response_path = target_dir / "response.json"
    request_path.write_text(
        json.dumps(request_body, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    response_path.write_text(
        json.dumps(response_json, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    image_bytes = download_image(image_url)
    width, height = get_png_dimensions(image_bytes)
    image_path.write_bytes(image_bytes)
    is_remote_url = image_url.startswith(("https://", "http://"))

    artifacts = {
        "image_path": str(image_path),
        "request_path": str(request_path),
        "response_path": str(response_path),
        "image_url": image_url if is_remote_url else None,
        "image_source": "remote_url" if is_remote_url else "data_url",
        "actual_size": f"{width}x{height}",
    }
    return artifacts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="通过 ThinkAI 生成已审核通过的图片。")
    parser.add_argument("--approved", action="store_true", required=True, help="确认用户已明确批准 Prompt")
    parser.add_argument("--approval-hash", required=True, help="用户批准的精确 Prompt SHA-256")
    parser.add_argument("--prompt", required=True, help="已审核通过的最终 Prompt")
    parser.add_argument("--size", default="1k", help="1k、2k 或明确尺寸")
    parser.add_argument("--quality", default="hd", choices=["standard", "hd"])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    skill_root = Path(__file__).resolve().parent.parent

    try:
        config = load_config(skill_root)
        size = resolve_size(args.size)
        body = build_generation_body(
            config["model"],
            validate_approval(args.prompt, args.approval_hash),
            size,
            args.quality,
            1,
        )
        response_json = request_generation(config, body)
        artifacts = write_artifacts(skill_root, body, response_json, None)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    summary = {
        "base_url": config["base_url"],
        "model": config["model"],
        "requested_size": size,
        "actual_size": artifacts["actual_size"],
        "quality": args.quality,
        **artifacts,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
