"""Seedream 5.0 Pro API 薄封装（复用 scripts/seedream_generate.py 的核心逻辑）。"""
import base64
import json
import mimetypes
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import List, Optional

SKILL_DIR = Path(__file__).resolve().parent.parent
ASSETS_CONFIG = SKILL_DIR / "assets" / "api_config.json"

DEFAULT_CONFIG = {
    "api_base": "https://ark.cn-beijing.volces.com/api/v3",
    "endpoint": "/images/generations",
    "model": "doubao-seedream-5-0-pro-260628",
    "default_size": "1024x1536",
    "response_format": "url",
    "watermark": True,
    "timeout": 180,
    "download_timeout": 120,
}


def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    if ASSETS_CONFIG.exists():
        try:
            file_cfg = json.loads(ASSETS_CONFIG.read_text(encoding="utf-8"))
            cfg.update({k: v for k, v in file_cfg.items() if v is not None})
        except Exception:
            pass
    cfg["api_key"] = os.environ.get("ARK_API_KEY") or cfg.get("api_key")
    if not cfg.get("api_key"):
        raise RuntimeError("ARK_API_KEY 未设置")
    return cfg


def to_data_url(image_path: str) -> str:
    p = Path(image_path)
    if not p.exists():
        raise FileNotFoundError(f"参考图不存在: {image_path}")
    mime, _ = mimetypes.guess_type(str(p))
    mime = mime or "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(p.read_bytes()).decode('ascii')}"


def call_api(cfg: dict, prompt: str, reference_images: List[str], size: Optional[str] = None) -> dict:
    """调用 Seedream API，返回响应 JSON。"""
    url = cfg["api_base"].rstrip("/") + cfg["endpoint"]
    body = {
        "model": cfg["model"],
        "prompt": prompt,
        "size": size or cfg["default_size"],
        "response_format": cfg["response_format"],
        "watermark": cfg["watermark"],
    }
    if reference_images:
        body["image"] = [to_data_url(i) if not i.startswith(("http://", "https://")) else i
                         for i in reference_images]
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"Authorization": f"Bearer {cfg['api_key']}",
                 "Content-Type": "application/json",
                 "User-Agent": "WorkBuddy/ProPhotoSkill/1.0"},
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=cfg["timeout"]) as resp:
            payload = resp.read().decode("utf-8")
            print(f"[seedream] API 返回 {time.time()-t0:.1f}s")
            return json.loads(payload)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"HTTP {e.code}: {err_body[:300]}")


def download(url: str, dst: Path, timeout: int = 120) -> Path:
    dst.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "WorkBuddy/ProPhotoSkill/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        dst.write_bytes(resp.read())
    return dst


def save_response(resp: dict, dst: Path, timeout: int = 120) -> Path:
    if "data" in resp and resp["data"]:
        item = resp["data"][0]
        if item.get("url"):
            return download(item["url"], dst, timeout)
        if item.get("b64_json"):
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(base64.b64decode(item["b64_json"]))
            return dst
    if "url" in resp:
        return download(resp["url"], dst, timeout)
    raise RuntimeError("未识别的响应格式")


def generate(prompt: str, reference_images: List[str], output: Path,
             size: Optional[str] = None) -> dict:
    """生成图片并保存。返回包含 prompt 的字典。"""
    cfg = load_config()
    resp = call_api(cfg, prompt, reference_images, size)
    save_response(resp, output, timeout=cfg.get("download_timeout", 120))
    return {
        "prompt": prompt,
        "size": size or cfg["default_size"],
        "output": str(output),
        "usage": resp.get("usage", {}),
    }
