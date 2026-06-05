#!/usr/bin/env python3
"""Convert sticker source URLs into Telegram sticker sets."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import emoji
import requests
from PIL import Image, ImageSequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
RUNS_DIR = ROOT / "runs"
LOCAL_ENV_PATH = ROOT / ".env.local"
FALLBACK_EMOJI = "⭐"
IMAGE_EXTENSIONS = {".png", ".webp", ".jpg", ".jpeg", ".gif"}
VIDEO_EXTENSIONS = {".webm", ".mp4", ".mov", ".m4v"}
ANIMATED_EXTENSIONS = {".tgs"}
STICKER_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS | ANIMATED_EXTENSIONS
DEFAULT_IMPORTER_TIMEOUT = 120.0
DEFAULT_TELEGRAM_CONNECT_TIMEOUT = 30.0
DEFAULT_TELEGRAM_READ_TIMEOUT = 60.0


class ToolError(RuntimeError):
    pass


@dataclass
class StickerItem:
    index: int
    file: Path
    format: str
    preview_file: Path | None = None

    def to_json(self, run_dir: Path) -> dict[str, Any]:
        data = {
            "index": self.index,
            "file": relpath(self.file, run_dir),
            "format": self.format,
        }
        if self.preview_file:
            data["preview_file"] = relpath(self.preview_file, run_dir)
        return data


def relpath(path: Path, base: Path) -> str:
    return path.resolve().relative_to(base.resolve()).as_posix()


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def status(message: str) -> None:
    print(message, flush=True)


def redacted(value: str) -> str:
    secrets = [
        os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
    ]
    safe = value
    for secret in secrets:
        if secret:
            safe = safe.replace(secret, "[REDACTED]")
    safe = re.sub(r"/bot[^/\s]+/", "/bot[REDACTED]/", safe)
    return safe


def env_float(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise ToolError(f"{name} 必須是秒數數字，目前是 {raw!r}") from exc
    if value <= 0:
        raise ToolError(f"{name} 必須大於 0，目前是 {raw!r}")
    return value


def load_local_env(path: Path = LOCAL_ENV_PATH) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key):
            continue
        value = value.strip().strip("\"'")
        os.environ.setdefault(key, value)


def source_id_from_url(url: str) -> str:
    cleaned_url = url.strip()
    for pattern in (r"/stickershop/product/([^/?#]+)", r"/S/sticker/([^/?#]+)", r"/sticker/([^/?#]+)"):
        match = re.search(pattern, cleaned_url)
        if match:
            return sanitize_name(match.group(1))
    digest = hashlib.sha256(cleaned_url.encode("utf-8")).hexdigest()
    return sanitize_name(digest[:10])


def sanitize_name(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_")
    return value or "stickers"


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ToolError(f"缺少必要環境變數：{name}")
    return value


def require_numeric_env(name: str) -> str:
    value = require_env(name)
    if not value.isdigit():
        raise ToolError(f"{name} 必須是純數字 ID，不能使用 @username。")
    return value


def require_executable(name: str) -> str:
    path = shutil.which(name)
    if path:
        return path
    local_path = ROOT / "bin" / name
    if local_path.exists() and os.access(local_path, os.X_OK):
        return str(local_path)
    if not path:
        raise ToolError(f"找不到 `{name}`。請依 README 準備相容的貼圖下載器。")
    return path


def require_importer_executable() -> str:
    configured = os.getenv("STICKER_IMPORTER_BINARY", "").strip()
    if configured:
        path = Path(configured)
        if path.exists() and os.access(path, os.X_OK):
            return str(path)
        raise ToolError("STICKER_IMPORTER_BINARY 指向的貼圖下載器不存在或不可執行。")
    try:
        return require_executable("sticker-importer")
    except ToolError:
        pass
    raise ToolError("找不到貼圖下載器。請把相容 binary 放在 bin/sticker-importer。")


def sticker_format(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".tgs":
        return "animated"
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    return "static"


def find_sticker_files(stickers_dir: Path) -> list[Path]:
    files = [
        p
        for p in stickers_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in STICKER_EXTENSIONS and is_likely_sticker_file(p)
    ]
    return sorted(files, key=lambda p: natural_key(p.relative_to(stickers_dir).as_posix()))


def is_likely_sticker_file(path: Path) -> bool:
    name = path.name.lower()
    if "_key" in name or name.startswith("tab_") or name in {"line.zip", "source.zip"}:
        return False
    return True


def sticker_files_from_importer(data: Any, root: Path) -> list[Path]:
    if not isinstance(data, dict) or not isinstance(data.get("Files"), list):
        return []
    files = []
    for item in data["Files"]:
        if not isinstance(item, dict):
            continue
        raw_path = item.get("ConvertedFile") or item.get("OriginalFile")
        if not isinstance(raw_path, str) or not raw_path.strip():
            continue
        path = Path(raw_path)
        if not path.is_absolute():
            path = root / path
        if path.exists() and path.suffix.lower() in STICKER_EXTENSIONS and is_likely_sticker_file(path):
            files.append(path)
    return files


def natural_key(value: str) -> list[Any]:
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", value)]


def extract_json_blob(text: str) -> Any | None:
    stripped = text.strip()
    if not stripped:
        return None
    for candidate in (stripped, stripped[stripped.find("{") : stripped.rfind("}") + 1]):
        if not candidate:
            continue
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    return None


def guess_title_from_msb(data: Any, fallback: str) -> str:
    if isinstance(data, dict):
        for key in ("title_zh_hant", "titleZhHant", "title", "name", "package_title"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return clean_display_title(value, fallback)[:64]
        package = data.get("package") or data.get("stickerPackage")
        if isinstance(package, dict):
            return guess_title_from_msb(package, fallback)
    return fallback


def clean_display_title(title: str, fallback: str) -> str:
    title = html.unescape(re.sub(r"\s+", " ", title)).strip()
    title = re.sub(r"\s*(?:[-–|｜]\s*)+(?:貼圖|Sticker|Store|Shop|STORE|SHOP).*$", "", title).strip()
    title = re.sub(r"\s*(?:[-–|｜]\s*)+.*(?:貼圖|Sticker|Store|Shop|STORE|SHOP).*$", "", title).strip()
    return title[:64] if title else fallback[:64]


def fetch_source_title(url: str, fallback: str) -> str:
    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
    except requests.RequestException:
        return fallback
    text = response.text
    for pattern in (
        r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']+)["\']',
        r"<title>(.*?)</title>",
    ):
        match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            title = clean_display_title(match.group(1), fallback)
            if title:
                return title[:64]
    return fallback


def classify_importer_failure(stdout: str, stderr: str) -> str:
    text = f"{stdout}\n{stderr}".lower()
    if any(marker in text for marker in ("no such host", "lookup ", "name resolution", "dns")):
        return "DNS/網路解析失敗；在 Codex 沙盒內請用同一命令重新執行並允許網路權限。"
    if any(marker in text for marker in ("connection refused", "connection reset", "i/o timeout", "timeout")):
        return "網路連線逾時或被中斷；請確認網路後重跑，沙盒環境需允許網路權限。"
    if any(marker in text for marker in ("404", "not found", "403", "forbidden", "invalid link")):
        return "貼圖來源頁面不可用或網址無法被下載器讀取；請確認貼圖網址仍可開啟。"
    if "json" in text or "parse" in text:
        return "貼圖下載器解析輸出失敗；請查看 importer stdout/stderr log。"
    return "原因未分類；請查看 importer stdout/stderr log。"


def importer_timeout() -> float:
    return env_float("STICKER_IMPORT_TIMEOUT", DEFAULT_IMPORTER_TIMEOUT)


def run_importer(url: str, run_dir: Path, force: bool) -> dict[str, Any]:
    stickers_dir = run_dir / "stickers"
    manifest_path = run_dir / "manifest.json"
    if manifest_path.exists() and stickers_dir.exists() and not force:
        return read_json(manifest_path)

    importer = require_importer_executable()
    stickers_dir.mkdir(parents=True, exist_ok=True)
    command = [importer, "--link", url, "--convert", "--json", "--dir", str(stickers_dir)]
    started = time.time()
    try:
        proc = subprocess.run(command, text=True, capture_output=True, cwd=ROOT, timeout=importer_timeout())
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        (run_dir / "importer.stdout.log").write_text(stdout, encoding="utf-8")
        (run_dir / "importer.stderr.log").write_text(stderr, encoding="utf-8")
        raise ToolError(
            f"貼圖下載器超過 {importer_timeout():g} 秒仍未完成；可設定 STICKER_IMPORT_TIMEOUT 或確認網路後重跑。"
        ) from exc
    (run_dir / "importer.stdout.log").write_text(proc.stdout, encoding="utf-8")
    (run_dir / "importer.stderr.log").write_text(proc.stderr, encoding="utf-8")
    if proc.returncode != 0:
        reason = classify_importer_failure(proc.stdout, proc.stderr)
        raise ToolError(
            f"貼圖下載器下載或轉換失敗：{reason} log 已保留在 {run_dir}"
        )

    parsed = extract_json_blob(proc.stdout)
    files = sticker_files_from_importer(parsed, ROOT) or find_sticker_files(stickers_dir)
    if not files:
        raise ToolError(f"貼圖下載器成功結束，但在 {stickers_dir} 找不到可用貼圖檔。")

    items = [StickerItem(index=i + 1, file=file, format=sticker_format(file)) for i, file in enumerate(files)]
    title = guess_title_from_msb(parsed, f"Sticker pack {run_dir.name}")
    manifest = {
        "source_url": url,
        "source_id": run_dir.name,
        "title": title,
        "generated_at": int(time.time()),
        "importer_seconds": round(time.time() - started, 2),
        "importer_json": parsed,
        "stickers": [item.to_json(run_dir) for item in items],
    }
    write_json(manifest_path, manifest)
    return manifest


def load_manifest_items(run_dir: Path, manifest: dict[str, Any]) -> list[StickerItem]:
    items = []
    for raw in manifest.get("stickers", []):
        file = run_dir / raw["file"]
        preview = run_dir / raw["preview_file"] if raw.get("preview_file") else None
        items.append(StickerItem(index=int(raw["index"]), file=file, format=raw["format"], preview_file=preview))
    return items


def make_preview_image(item: StickerItem, run_dir: Path, force: bool) -> Path | None:
    vision_dir = run_dir / "vision"
    vision_dir.mkdir(parents=True, exist_ok=True)
    output = vision_dir / f"{item.index:03d}.png"
    if output.exists() and not force:
        return output

    suffix = item.file.suffix.lower()
    try:
        if suffix in IMAGE_EXTENSIONS:
            with Image.open(item.file) as image:
                frame = next(ImageSequence.Iterator(image)).convert("RGBA")
                frame.thumbnail((768, 768), Image.Resampling.LANCZOS)
                frame.save(output, "PNG")
            return output
        if suffix in VIDEO_EXTENSIONS:
            ffmpeg = shutil.which("ffmpeg")
            if not ffmpeg:
                return None
            command = [
                ffmpeg,
                "-y",
                "-i",
                str(item.file),
                "-frames:v",
                "1",
                "-vf",
                "scale='min(768,iw)':-2",
                str(output),
            ]
            proc = subprocess.run(command, capture_output=True, text=True)
            if proc.returncode == 0 and output.exists():
                return output
    except Exception:
        return None
    return None


def ensure_preview_images(run_dir: Path, manifest: dict[str, Any], force: bool) -> list[StickerItem]:
    items = load_manifest_items(run_dir, manifest)
    updated = False
    for item in items:
        preview = make_preview_image(item, run_dir, force)
        if preview:
            item.preview_file = preview
            updated = True
    if updated:
        manifest["stickers"] = [item.to_json(run_dir) for item in items]
        write_json(run_dir / "manifest.json", manifest)
    return items


def fallback_plan(index: int, reason: str) -> dict[str, Any]:
    return {
        "index": index,
        "emoji_list": [FALLBACK_EMOJI],
        "confidence": 0.0,
        "reason": reason,
        "fallback": True,
    }


def normalize_plan(plan: dict[str, Any]) -> dict[str, Any]:
    emojis = plan.get("emoji_list")
    if isinstance(emojis, str):
        emojis = [emojis]
    if not isinstance(emojis, list):
        emojis = []
    cleaned = []
    for value in emojis:
        if not isinstance(value, str):
            continue
        value = value.strip()
        if is_valid_single_emoji(value) and value not in cleaned:
            cleaned.append(value)
    if not 1 <= len(cleaned) <= 20:
        return fallback_plan(int(plan.get("index", 0)), "emoji_list 無效。")
    try:
        confidence = float(plan.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    normalized = {
        "index": int(plan.get("index", 0)),
        "emoji_list": cleaned[:20],
        "confidence": max(0.0, min(1.0, confidence)),
        "reason": str(plan.get("reason", ""))[:240],
    }
    if plan.get("fallback"):
        normalized["fallback"] = True
    return normalized


def is_valid_single_emoji(value: str) -> bool:
    found = emoji.emoji_list(value)
    if not found:
        return False
    spans = "".join(item["emoji"] for item in found)
    return spans == value


def build_emoji_plan(run_dir: Path, items: list[StickerItem]) -> list[dict[str, Any]]:
    plan_path = run_dir / "emoji_plan.json"
    if plan_path.exists():
        data = read_json(plan_path)
        if isinstance(data, list) and data:
            return [normalize_plan(item) for item in data]

    plans = [fallback_plan(item.index, "待 agent 依預覽圖指派 emoji。") for item in items]
    write_json(plan_path, plans)
    return plans


def validate_emoji_plan_ready(items: list[StickerItem], plans: list[dict[str, Any]]) -> None:
    expected = {item.index for item in items}
    actual = [int(plan.get("index", 0)) for plan in plans]
    actual_set = set(actual)
    duplicates = sorted({index for index in actual if actual.count(index) > 1})
    missing = sorted(expected - actual_set)
    extra = sorted(actual_set - expected)
    fallbacks = sorted(int(plan.get("index", 0)) for plan in plans if plan.get("fallback"))
    if duplicates or missing or extra or fallbacks:
        raise ToolError(
            "emoji_plan.json 尚未完成，拒絕建立 Telegram 貼圖包："
            f"duplicates={duplicates} missing={missing} extra={extra} fallbacks={fallbacks}。"
            " 請先用 scripts/write_emoji_plan.py 寫入每張貼圖的 emoji。"
        )


def make_telegram_upload_file(item: StickerItem, run_dir: Path) -> Path:
    if item.format != "static":
        return item.file
    upload_dir = run_dir / "telegram_upload"
    upload_dir.mkdir(parents=True, exist_ok=True)
    output = upload_dir / f"{item.index:03d}.png"
    source_mtime = item.file.stat().st_mtime
    if output.exists() and output.stat().st_mtime >= source_mtime:
        return output

    with Image.open(item.file) as image:
        frame = next(ImageSequence.Iterator(image)).convert("RGBA")
        frame.thumbnail((512, 512), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
        x = (512 - frame.width) // 2
        y = (512 - frame.height) // 2
        canvas.alpha_composite(frame, (x, y))
        canvas.save(output, "PNG", optimize=True)
    return output


def telegram_upload_files(run_dir: Path, items: list[StickerItem]) -> list[Path]:
    return [make_telegram_upload_file(item, run_dir) for item in items]


def telegram_timeout() -> tuple[float, float]:
    return (
        env_float("TELEGRAM_CONNECT_TIMEOUT", DEFAULT_TELEGRAM_CONNECT_TIMEOUT),
        env_float("TELEGRAM_READ_TIMEOUT", DEFAULT_TELEGRAM_READ_TIMEOUT),
    )


def classify_telegram_failure(text: str) -> str:
    lowered = text.lower()
    if any(marker in lowered for marker in ("no such host", "name resolution", "failed to resolve", "nodename nor servname")):
        return "DNS/網路解析失敗；在 Codex 沙盒內請用同一命令重新執行並允許網路權限。"
    if any(marker in lowered for marker in ("read timed out", "connect timeout", "timed out", "timeout")):
        return "Telegram API 回應逾時；可臨時提高 TELEGRAM_READ_TIMEOUT 後重跑。"
    if "forbidden" in lowered or "bot was blocked" in lowered:
        return "Telegram bot 無法傳送或建立貼圖；請確認使用者已對 bot 按過 /start。"
    if "unauthorized" in lowered:
        return "Telegram bot token 無效；請到 @BotFather 檢查或重新產生 token。"
    return ""


def telegram_call(token: str, method: str, data: dict[str, Any], files: dict[str, Any] | None = None) -> Any:
    url = f"https://api.telegram.org/bot{token}/{method}"
    try:
        response = requests.post(url, data=data, files=files, timeout=telegram_timeout())
    except requests.RequestException as exc:
        detail = redacted(str(exc))
        reason = classify_telegram_failure(detail)
        message = f"{reason} " if reason else ""
        raise ToolError(f"Telegram API {method} 連線失敗：{message}{detail}") from exc
    try:
        payload = response.json()
    except ValueError as exc:
        raise ToolError(f"Telegram API 回傳非 JSON：HTTP {response.status_code}") from exc
    if not payload.get("ok"):
        detail = redacted(str(payload.get("description", payload)))
        reason = classify_telegram_failure(detail)
        message = f"{reason} " if reason else ""
        raise ToolError(f"Telegram API {method} 失敗：{message}{detail}")
    return payload.get("result")


def get_bot_username(token: str) -> str:
    try:
        response = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=telegram_timeout())
    except requests.RequestException as exc:
        detail = redacted(str(exc))
        reason = classify_telegram_failure(detail)
        message = f"{reason} " if reason else ""
        raise ToolError(f"Telegram getMe 連線失敗：{message}{detail}") from exc
    try:
        payload = response.json()
    except ValueError as exc:
        raise ToolError(f"Telegram getMe 回傳非 JSON：HTTP {response.status_code}") from exc
    if not payload.get("ok"):
        detail = redacted(str(payload.get("description", payload)))
        reason = classify_telegram_failure(detail)
        message = f"{reason} " if reason else ""
        raise ToolError(f"Telegram getMe 失敗：{message}{detail}")
    username = payload["result"].get("username")
    if not username:
        raise ToolError("Telegram bot 沒有 username，無法建立符合規則的貼圖包名稱。")
    return username


def sticker_set_name(source_id: str, bot_username: str) -> str:
    prefix = sanitize_name(f"stickers_{source_id}").lower()
    suffix = f"_by_{bot_username.lower()}"
    max_prefix = 64 - len(suffix)
    prefix = prefix[:max_prefix].strip("_") or "stickers"
    if not re.match(r"^[A-Za-z]", prefix):
        prefix = f"stickers_{prefix}"
    prefix = re.sub(r"_+", "_", prefix).strip("_")
    return f"{prefix}{suffix}"


def open_file_handles(files: list[Path]) -> dict[str, Any]:
    handles = {}
    for i, path in enumerate(files):
        handles[f"file{i}"] = (path.name, path.open("rb"), mimetypes.guess_type(path.name)[0] or "application/octet-stream")
    return handles


def close_file_handles(files: dict[str, Any]) -> None:
    for value in files.values():
        value[1].close()


def load_existing_telegram_result(run_dir: Path) -> dict[str, Any] | None:
    path = run_dir / "telegram_import.json"
    if not path.exists():
        return None
    try:
        data = read_json(path)
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def save_telegram_result(run_dir: Path, result: dict[str, Any]) -> None:
    result["updated_at"] = int(time.time())
    write_json(run_dir / "telegram_import.json", result)


def telegram_import(
    run_dir: Path,
    manifest: dict[str, Any],
    items: list[StickerItem],
    plans: list[dict[str, Any]],
    title_arg: str,
) -> dict[str, Any]:
    existing = load_existing_telegram_result(run_dir)
    if (
        existing
        and existing.get("created")
        and int(existing.get("added") or 0) >= len(items)
        and not existing.get("errors")
        and existing.get("url")
    ):
        existing["status"] = "complete"
        save_telegram_result(run_dir, existing)
        status(f"Telegram: existing complete set reused {existing['added']}/{len(items)}")
        return existing

    token = require_env("TELEGRAM_BOT_TOKEN")
    user_id = require_numeric_env("TELEGRAM_USER_ID")
    source_id = str(manifest.get("source_id") or run_dir.name)
    result: dict[str, Any] = {
        "source_id": source_id,
        "title": str(manifest.get("title") or f"Sticker pack {source_id}")[:64],
        "status": "resolving_bot",
        "created": False,
        "added": 0,
        "added_indexes": [],
        "errors": [],
        "started_at": int(time.time()),
    }
    if not existing:
        save_telegram_result(run_dir, result)

    status("Telegram: getMe")
    try:
        bot_username = get_bot_username(token)
    except ToolError as exc:
        result["status"] = "failed"
        result["errors"].append({"method": "getMe", "error": str(exc)})
        if not existing:
            save_telegram_result(run_dir, result)
        raise
    name = sticker_set_name(source_id, bot_username)
    title = manifest.get("title") or f"Sticker pack {source_id}"
    if title_arg != "auto":
        title = title_arg
    title = str(title)[:64]
    by_index = {int(plan["index"]): plan for plan in plans}
    upload_files = telegram_upload_files(run_dir, items)

    stickers = []
    for file_index, item in enumerate(items):
        plan = by_index.get(item.index, fallback_plan(item.index, "缺少 emoji plan。"))
        stickers.append(
            {
                "sticker": f"attach://file{file_index}",
                "format": item.format,
                "emoji_list": plan["emoji_list"],
            }
        )

    if existing and existing.get("name") == name and existing.get("created"):
        result.update(existing)
        result["errors"] = []
        result["status"] = "resuming"
    else:
        result.update(
            {
                "name": name,
                "title": title,
                "bot_username": bot_username,
                "created": False,
                "added": 0,
                "added_indexes": [],
                "errors": [],
            }
        )
    result["url"] = f"https://t.me/addstickers/{name}"
    save_telegram_result(run_dir, result)

    if not result.get("created"):
        first_batch = stickers[:1]
        first_files = upload_files[:1]
        file_handles = open_file_handles(first_files)
        try:
            result["status"] = "creating"
            result["current_index"] = items[0].index
            save_telegram_result(run_dir, result)
            status(f"Telegram: createNewStickerSet 1/{len(stickers)}")
            telegram_call(
                token,
                "createNewStickerSet",
                {
                    "user_id": user_id,
                    "name": name,
                    "title": title,
                    "sticker_type": "regular",
                    "stickers": json.dumps(first_batch, ensure_ascii=False),
                },
                files=file_handles,
            )
            result["created"] = True
            result["added"] = len(first_batch)
            result["added_indexes"] = [items[0].index]
            result["status"] = "created"
            result.pop("current_index", None)
            save_telegram_result(run_dir, result)
        except ToolError as exc:
            result["status"] = "failed"
            result["errors"].append({"index": items[0].index, "method": "createNewStickerSet", "error": str(exc)})
            save_telegram_result(run_dir, result)
            raise
        finally:
            close_file_handles(file_handles)

    start_offset = max(1, int(result.get("added") or 0))
    for offset, sticker in enumerate(stickers[start_offset:], start=start_offset):
        item = items[offset]
        file_handles = open_file_handles([upload_files[offset]])
        single = dict(sticker)
        single["sticker"] = "attach://file0"
        try:
            result["status"] = "adding"
            result["current_index"] = item.index
            save_telegram_result(run_dir, result)
            status(f"Telegram: addStickerToSet {offset + 1}/{len(stickers)}")
            telegram_call(
                token,
                "addStickerToSet",
                {
                    "user_id": user_id,
                    "name": name,
                    "sticker": json.dumps(single, ensure_ascii=False),
                },
                files=file_handles,
            )
            result["added"] += 1
            result.setdefault("added_indexes", []).append(item.index)
            result.pop("current_index", None)
            save_telegram_result(run_dir, result)
        except ToolError as exc:
            result["status"] = "failed"
            result["errors"].append({"index": item.index, "method": "addStickerToSet", "error": str(exc)})
            save_telegram_result(run_dir, result)
            raise
        finally:
            close_file_handles(file_handles)

    result["status"] = "complete"
    result.pop("current_index", None)
    save_telegram_result(run_dir, result)
    return result


def copy_if_exists(source: Path, output_dir: Path) -> Path | None:
    if not source.exists():
        return None
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / source.name
    shutil.copy2(source, target)
    return target


def collect_user_outputs(run_dir: Path, extra_paths: list[Path] | None = None) -> Path:
    output_dir = run_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    for source in (
        run_dir / "manifest.json",
        run_dir / "emoji_plan.json",
        run_dir / "telegram_import.json",
    ):
        copy_if_exists(source, output_dir)
    for source in extra_paths or []:
        copy_if_exists(source, output_dir)
    return output_dir


def export_review_outputs(run_dir: Path) -> dict[str, Path]:
    from scripts.export_review import export_review_package

    return export_review_package(run_dir)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert a sticker source URL to a Telegram sticker set.")
    parser.add_argument("source_url", help="Sticker source URL")
    parser.add_argument("--title", default="auto", help='Telegram sticker set title, or "auto" for source title')
    parser.add_argument("--confirm", action="store_true", help="Actually create the Telegram sticker set")
    parser.add_argument("--force-download", action="store_true", help="Run importer again even if manifest exists")
    parser.add_argument("--skip-review", action="store_true", help="Do not export review/contact sheet files")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    load_local_env()
    args = parse_args(argv)
    source_id = source_id_from_url(args.source_url)
    run_dir = RUNS_DIR / source_id
    run_dir.mkdir(parents=True, exist_ok=True)

    try:
        if args.confirm:
            require_env("TELEGRAM_BOT_TOKEN")
            require_env("TELEGRAM_USER_ID")
        if not (run_dir / "manifest.json").exists() or args.force_download:
            require_importer_executable()

        manifest = run_importer(args.source_url, run_dir, args.force_download)
        if args.title == "auto":
            manifest["title"] = fetch_source_title(args.source_url, manifest.get("title", f"Sticker pack {source_id}"))
            write_json(run_dir / "manifest.json", manifest)
        items = ensure_preview_images(run_dir, manifest, args.force_download)
        plans = build_emoji_plan(run_dir, items)
        write_json(run_dir / "emoji_plan.json", plans)
        if args.confirm:
            validate_emoji_plan_ready(items, plans)
        extra_paths: list[Path] = []
        if not args.skip_review:
            review_paths = export_review_outputs(run_dir)
            extra_paths = [review_paths["png"], review_paths["pdf"], review_paths["html"]]
        output_dir = collect_user_outputs(run_dir, extra_paths)

        status(f"manifest: {run_dir / 'manifest.json'}")
        status(f"emoji_plan: {run_dir / 'emoji_plan.json'}")
        if args.skip_review:
            status("review_contact_sheet: skipped")
        else:
            status(f"review_contact_sheet: {review_paths['png']}")
        status(f"output_folder: {output_dir}")

        if not args.confirm:
            if args.skip_review:
                status("未加 --confirm，因此只產生本地貼圖素材與 emoji_plan，不建立 Telegram 貼圖包。")
            else:
                status("未加 --confirm，因此只產生 review contact sheet，不建立 Telegram 貼圖包。")
            return 0

        result = telegram_import(run_dir, manifest, items, plans, args.title)
        output_dir = collect_user_outputs(run_dir)
        status(f"telegram_import: {run_dir / 'telegram_import.json'}")
        status(f"output_folder: {output_dir}")
        status(f"sticker_set: {result['url']}")
        return 0
    except ToolError as exc:
        print(f"ERROR: {redacted(str(exc))}", file=sys.stderr, flush=True)
        return 2
    except Exception as exc:
        print(f"ERROR: unexpected failure: {redacted(str(exc))}", file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
