#!/usr/bin/env python3
"""在用户明确批准 Prompt 后，通过选定渠道生成并下载图片。"""

import argparse
import base64
import binascii
import hashlib
import hmac
import http.client
import json
import subprocess
import sys
import urllib.error
import urllib.request
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlsplit, urlunsplit

try:
    import requests
except ModuleNotFoundError:
    print(
        "缺少 Python 依赖 requests。请在 Skill 根目录运行："
        "python3 -m pip install -r requirements.txt",
        file=sys.stderr,
    )
    raise SystemExit(2)

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from provider_registry import (
    FORMAL_PROVIDER_IDS,
    get_provider,
    normalize_provider_id,
)
from providers import get_adapter


SIZE_ALIASES = {
    "1k": "1920x1088",
    "2k": "2560x1440",
}
DEFAULT_BASE_URL = "https://www.thinkai.tv/v1"
DEFAULT_MODEL = "gpt-image-2"
CONNECT_TIMEOUT_SECONDS = 30
READ_TIMEOUT_SECONDS = 900
SENSITIVE_HEADER_NAMES = {
    "authorization",
    "x-api-key",
    "api-key",
    "x-goog-api-key",
}


def load_raw_config(skill_root: Path) -> dict:
    config_path = skill_root / "config.json"
    if not config_path.is_file():
        raise RuntimeError(
            f"未找到 {config_path}。请先运行 "
            "python3 scripts/configure_api_key.py。"
        )

    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"无法读取图片渠道配置：{exc}") from exc
    if not isinstance(config, dict):
        raise RuntimeError("config.json 必须是 JSON 对象。")
    return config


def load_config(skill_root: Path, provider: str = "thinkai-image2") -> dict:
    config = load_raw_config(skill_root)
    normalized_provider = normalize_provider_id(provider)
    if normalized_provider in FORMAL_PROVIDER_IDS:
        spec = get_provider(normalized_provider)
        return get_adapter(normalized_provider).load_config(config, spec)
    providers = config.get("providers")
    if isinstance(providers, dict) and normalized_provider in providers:
        return get_adapter("custom").load_config(config, normalized_provider)
    raise RuntimeError(f"不支持或未配置的图片渠道：{provider}")


def resolve_size(raw_size: str) -> str:
    normalized = raw_size.strip().lower()
    return SIZE_ALIASES.get(normalized, raw_size.strip())


def resolve_provider_size(provider: str, raw_size: Optional[str]) -> str:
    normalized_provider = normalize_provider_id(provider)
    if normalized_provider in FORMAL_PROVIDER_IDS:
        spec = get_provider(normalized_provider)
        return get_adapter(normalized_provider).normalize_size(raw_size, spec)
    return get_adapter("custom").normalize_size(raw_size, None)


def resolve_provider_quality(provider: str, raw_quality: Optional[str]) -> str:
    normalized_provider = normalize_provider_id(provider)
    quality = str(raw_quality or "").strip().lower()
    if normalized_provider == "volcengine":
        return ""
    if normalized_provider == "google":
        return ""
    if normalized_provider == "thinkai-nano":
        return ""
    if normalized_provider == "openai":
        quality = "high" if quality == "hd" else quality
        if quality not in {"low", "medium", "high", "auto"}:
            raise ValueError(f"OpenAI 不支持图片质量：{raw_quality}。")
        return quality
    if normalized_provider == "thinkai-image2":
        if quality not in {"standard", "hd"}:
            raise ValueError(f"ThinkAI Image 2 不支持图片质量：{raw_quality}。")
        return quality
    return quality or "hd"


def validate_prompt(prompt: str) -> str:
    normalized = prompt.strip()
    if not normalized:
        raise ValueError("已审核 Prompt 不能为空。")
    return normalized


def approval_digest(
    prompt: str,
    provider: str = "thinkai-image2",
    model: Optional[str] = None,
    size: Optional[str] = None,
    quality: Optional[str] = None,
) -> str:
    normalized_prompt = validate_prompt(prompt)
    if normalize_provider_id(provider) == "thinkai-image2":
        payload = normalized_prompt
    else:
        payload = json.dumps(
            {
                "prompt": normalized_prompt,
                "provider": provider,
                "model": str(model or "").strip(),
                "size": str(size or "").strip(),
                "quality": str(quality or "").strip(),
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_approval(
    prompt: str,
    expected_digest: str,
    provider: str = "thinkai-image2",
    model: Optional[str] = None,
    size: Optional[str] = None,
    quality: Optional[str] = None,
) -> str:
    normalized = validate_prompt(prompt)
    actual_digest = approval_digest(normalized, provider, model, size, quality)
    if not hmac.compare_digest(actual_digest, expected_digest.strip().lower()):
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


def sanitize_error_detail(detail: object, headers: dict) -> str:
    """移除服务端错误正文中可能回显的鉴权信息。"""

    sanitized = str(detail)
    sensitive_values = set()
    for key, value in headers.items():
        if str(key).lower() not in SENSITIVE_HEADER_NAMES:
            continue
        normalized = str(value).strip()
        if not normalized:
            continue
        sensitive_values.add(normalized)
        if normalized.lower().startswith("bearer "):
            sensitive_values.add(normalized[7:].strip())

    for secret in sorted(sensitive_values, key=len, reverse=True):
        if secret:
            sanitized = sanitized.replace(secret, "<redacted>")
    return sanitized


def request_json(
    method: str,
    url: str,
    headers: dict,
    body: Optional[dict] = None,
    service_name: str = "ThinkAI",
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
        detail = sanitize_error_detail(detail, headers)
        raise RuntimeError(
            f"{service_name} 请求失败，HTTP {status_code}：{detail}。"
            "付费生成请求不会自动重试。"
        ) from exc
    except (
        requests.ConnectionError,
        requests.Timeout,
        requests.exceptions.ChunkedEncodingError,
    ) as exc:
        raise RuntimeError(
            f"{service_name} 生成请求结果不确定，服务端可能已受理并计费。"
            "为避免重复生成，本工具不会自动重试；"
            f"请先在 {service_name} 后台确认任务记录，再决定是否重新执行。"
            f"原始错误：{exc}"
        ) from exc

    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        payload = sanitize_error_detail(payload, headers)
        raise RuntimeError(
            f"{service_name} 返回了非 JSON 响应：{payload[:500]}"
        ) from exc


def extract_adapter_source(adapter, response_json: dict, config: dict):
    if config["provider"] in FORMAL_PROVIDER_IDS:
        return adapter.extract_image_source(response_json)
    return adapter.extract_image_source(response_json, config)


def request_generation(config: dict, request: dict, adapter=None) -> dict:
    if adapter is None:
        adapter = get_adapter(
            config["provider"]
            if config["provider"] in FORMAL_PROVIDER_IDS
            else "custom"
        )
    data = request_json(
        "POST",
        request["url"],
        request["headers"],
        request["body"],
        service_name=config.get("provider_name", config["provider"]),
    )
    extract_adapter_source(adapter, data, config)
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


def get_jpeg_dimensions(image_bytes: bytes) -> Tuple[int, int]:
    position = 2
    sof_markers = {
        0xC0,
        0xC1,
        0xC2,
        0xC3,
        0xC5,
        0xC6,
        0xC7,
        0xC9,
        0xCA,
        0xCB,
        0xCD,
        0xCE,
        0xCF,
    }
    while position + 3 < len(image_bytes):
        if image_bytes[position] != 0xFF:
            position += 1
            continue
        while position < len(image_bytes) and image_bytes[position] == 0xFF:
            position += 1
        if position >= len(image_bytes):
            break
        marker = image_bytes[position]
        position += 1
        if marker in {0xD8, 0xD9}:
            continue
        if position + 1 >= len(image_bytes):
            break
        segment_length = int.from_bytes(image_bytes[position : position + 2], "big")
        if segment_length < 2 or position + segment_length > len(image_bytes):
            break
        if marker in sof_markers and segment_length >= 7:
            height = int.from_bytes(image_bytes[position + 3 : position + 5], "big")
            width = int.from_bytes(image_bytes[position + 5 : position + 7], "big")
            if width and height:
                return width, height
        position += segment_length
    raise RuntimeError("返回的 JPEG 无法读取尺寸。")


def inspect_image(image_bytes: bytes) -> Tuple[str, int, int]:
    if image_bytes[:8] == b"\x89PNG\r\n\x1a\n" and len(image_bytes) >= 24:
        width = int.from_bytes(image_bytes[16:20], "big")
        height = int.from_bytes(image_bytes[20:24], "big")
        return "png", width, height
    if image_bytes[:2] == b"\xff\xd8":
        width, height = get_jpeg_dimensions(image_bytes)
        return "jpg", width, height
    if image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        chunk = image_bytes[12:16]
        if chunk == b"VP8X" and len(image_bytes) >= 30:
            width = 1 + int.from_bytes(image_bytes[24:27], "little")
            height = 1 + int.from_bytes(image_bytes[27:30], "little")
            return "webp", width, height
        if chunk == b"VP8L" and len(image_bytes) >= 25:
            bits = int.from_bytes(image_bytes[21:25], "little")
            width = (bits & 0x3FFF) + 1
            height = ((bits >> 14) & 0x3FFF) + 1
            return "webp", width, height
        raise RuntimeError("返回的 WebP 无法读取尺寸。")
    raise RuntimeError("图片不是支持的 PNG、JPEG 或 WebP 格式。")


def decode_data_url(value: str) -> bytes:
    header, separator, encoded = value.partition(",")
    if not separator or not header.startswith("data:image/") or ";base64" not in header:
        raise RuntimeError("图片 Data URL 格式无效。")
    try:
        return base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise RuntimeError("图片 Data URL 数据无效。") from exc


def extract_image_bytes(config: dict, response_json: dict) -> Tuple[bytes, str, str]:
    provider = config["provider"]
    adapter_id = provider if provider in FORMAL_PROVIDER_IDS else "custom"
    adapter = get_adapter(adapter_id)
    source_type, source_value = extract_adapter_source(adapter, response_json, config)

    if source_type == "base64":
        try:
            return base64.b64decode(source_value, validate=True), source_type, ""
        except (ValueError, binascii.Error) as exc:
            raise RuntimeError("图片 Base64 数据无效。") from exc
    if source_value.startswith("data:image/"):
        return decode_data_url(source_value), "data_url", ""

    return download_image(source_value), source_type, source_value


def redact_url(value: str) -> str:
    try:
        parts = urlsplit(value)
    except ValueError:
        return value
    if parts.scheme not in {"http", "https"}:
        return value
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def redact_snapshot(value, omitted_values=None):
    omitted_values = omitted_values or set()
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if lowered in {"api_key", "authorization", "x-goog-api-key"}:
                result[key] = "<redacted>"
            elif lowered in {"b64_json", "data"} and isinstance(item, str) and len(item) > 256:
                result[key] = "<base64 omitted>"
            else:
                result[key] = redact_snapshot(item, omitted_values)
        return result
    if isinstance(value, list):
        return [redact_snapshot(item, omitted_values) for item in value]
    if isinstance(value, str) and value in omitted_values:
        return "<base64 omitted>"
    if isinstance(value, str) and value.startswith(("https://", "http://")):
        return redact_url(value)
    return value


def write_artifacts(
    skill_root: Path,
    config: dict,
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

    adapter_id = (
        config["provider"]
        if config["provider"] in FORMAL_PROVIDER_IDS
        else "custom"
    )
    adapter = get_adapter(adapter_id)
    source_type, source_value = extract_adapter_source(
        adapter,
        response_json,
        config,
    )
    omitted_values = (
        {source_value}
        if source_type == "base64" or source_value.startswith("data:image/")
        else set()
    )

    request_path = target_dir / "request.json"
    response_path = target_dir / "response.json"
    request_path.write_text(
        json.dumps(request_body, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    response_path.write_text(
        json.dumps(
            redact_snapshot(deepcopy(response_json), omitted_values),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    image_bytes, source_type, image_url = extract_image_bytes(config, response_json)
    image_format, width, height = inspect_image(image_bytes)
    image_path = target_dir / f"image.{image_format}"
    image_path.write_bytes(image_bytes)
    is_remote_url = image_url.startswith(("https://", "http://"))

    artifacts = {
        "image_path": str(image_path),
        "request_path": str(request_path),
        "response_path": str(response_path),
        "image_url": redact_url(image_url) if is_remote_url else None,
        "image_source": (
            "base64"
            if source_type == "base64"
            else ("data_url" if source_type == "data_url" else "remote_url")
        ),
        "actual_size": f"{width}x{height}",
    }
    return artifacts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="通过选定渠道生成已审核通过的图片。",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--provider",
        default="thinkai-image2",
        help="图片生成渠道 ID（默认: thinkai-image2；旧别名 thinkai 可用）",
    )
    parser.add_argument("--approved", action="store_true", required=True, help="确认用户已明确批准 Prompt")
    parser.add_argument("--approval-hash", required=True, help="用户批准的精确 Prompt SHA-256")
    parser.add_argument("--prompt", required=True, help="已审核通过的最终 Prompt")
    parser.add_argument(
        "--size",
        default=None,
        help=(
            "尺寸；ThinkAI Image 2 可用 1k/2k，"
            "ThinkAI Nano 使用 16:9@2K 等格式"
        ),
    )
    parser.add_argument(
        "--quality",
        default="hd",
        choices=["standard", "hd", "low", "medium", "high", "auto"],
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    skill_root = Path(__file__).resolve().parent.parent

    try:
        config = load_config(skill_root, args.provider)
        size = resolve_provider_size(config["provider"], args.size)
        approval_quality = resolve_provider_quality(config["provider"], args.quality)
        approved_prompt = validate_approval(
            args.prompt,
            args.approval_hash,
            config["provider"],
            config["model"],
            size,
            approval_quality,
        )
        adapter_id = config["provider"] if config["provider"] in FORMAL_PROVIDER_IDS else "custom"
        adapter = get_adapter(adapter_id)
        request = adapter.build_request(
            config,
            approved_prompt,
            size,
            approval_quality,
        )
        body = request["body"]
        response_json = request_generation(config, request, adapter)
        artifacts = write_artifacts(
            skill_root,
            config,
            body,
            response_json,
            None,
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    summary = {
        "provider": config["provider"],
        "base_url": config.get("base_url", config.get("endpoint")),
        "model": config["model"],
        "requested_size": size,
        "actual_size": artifacts["actual_size"],
        **artifacts,
    }
    if approval_quality:
        summary["quality"] = approval_quality
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
