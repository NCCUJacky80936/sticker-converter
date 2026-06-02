#!/usr/bin/env python3
"""Export sticker review files that keep the actual images for model or manual review."""

from __future__ import annotations

import argparse
import base64
import html
import json
import mimetypes
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageSequence


ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = ROOT / "runs"


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size)
            except OSError:
                pass
    return ImageFont.load_default()


def first_frame(path: Path, size: int) -> Image.Image:
    with Image.open(path) as image:
        frame = next(ImageSequence.Iterator(image)).convert("RGBA")
        frame.thumbnail((size, size), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (size, size), (255, 255, 255, 255))
        x = (size - frame.width) // 2
        y = (size - frame.height) // 2
        canvas.alpha_composite(frame, (x, y))
        return canvas.convert("RGB")


def image_data_url(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def export_contact_sheet(
    run_dir: Path, output_dir: Path, stickers: list[dict[str, Any]], columns: int
) -> tuple[Path, Path]:
    cell = 260
    label_h = 42
    padding = 18
    rows = (len(stickers) + columns - 1) // columns
    width = columns * cell + (columns + 1) * padding
    height = rows * (cell + label_h) + (rows + 1) * padding
    sheet = Image.new("RGB", (width, height), (246, 247, 249))
    draw = ImageDraw.Draw(sheet)
    label_font = load_font(28)

    for i, sticker in enumerate(stickers):
        row = i // columns
        col = i % columns
        x = padding + col * (cell + padding)
        y = padding + row * (cell + label_h + padding)
        draw.rounded_rectangle(
            (x, y, x + cell, y + cell + label_h),
            radius=10,
            fill=(255, 255, 255),
            outline=(210, 216, 224),
            width=2,
        )
        image = first_frame(run_dir / sticker["file"], cell - 24)
        sheet.paste(image, (x + 12, y + 12))
        label = f"#{int(sticker['index']):03d}"
        bbox = draw.textbbox((0, 0), label, font=label_font)
        tx = x + (cell - (bbox[2] - bbox[0])) // 2
        draw.text((tx, y + cell + 6), label, fill=(32, 36, 42), font=label_font)

    output_dir.mkdir(parents=True, exist_ok=True)
    png_path = output_dir / "review_contact_sheet.png"
    pdf_path = output_dir / "review_contact_sheet.pdf"
    sheet.save(png_path, "PNG")
    sheet.save(pdf_path, "PDF", resolution=150.0)
    return png_path, pdf_path


def export_embedded_html(
    run_dir: Path, output_dir: Path, manifest: dict[str, Any], stickers: list[dict[str, Any]]
) -> Path:
    cards = []
    for sticker in stickers:
        src = image_data_url(run_dir / sticker["file"])
        cards.append(
            f"""
            <article>
              <img src="{src}" alt="Sticker #{int(sticker['index']):03d}">
              <strong>#{int(sticker['index']):03d}</strong>
            </article>
            """
        )

    title = html.escape(str(manifest.get("title") or f"Sticker pack {manifest.get('source_id', '')}"))
    page = f"""<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} sticker review</title>
  <style>
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f6f7f9; color: #20242a; }}
    header {{ padding: 18px 24px; background: #fff; border-bottom: 1px solid #d9dee5; }}
    h1 {{ margin: 0; font-size: 22px; }}
    main {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 14px; padding: 18px; }}
    article {{ display: grid; gap: 8px; justify-items: center; padding: 12px; background: #fff; border: 1px solid #d9dee5; border-radius: 8px; }}
    img {{ width: 160px; height: 160px; object-fit: contain; }}
    strong {{ font-size: 18px; }}
  </style>
</head>
<body>
  <header><h1>{title}</h1></header>
  <main>{''.join(cards)}</main>
</body>
</html>
"""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "review.html"
    path.write_text(page, encoding="utf-8")
    return path


def export_review_package(run_dir: Path, columns: int = 5) -> dict[str, Path]:
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest not found: {manifest_path}")
    manifest = read_json(manifest_path)
    stickers = manifest.get("stickers") or []
    if not stickers:
        raise ValueError(f"no stickers in manifest: {manifest_path}")

    output_dir = run_dir / "review"
    png_path, pdf_path = export_contact_sheet(run_dir, output_dir, stickers, max(1, columns))
    html_path = export_embedded_html(run_dir, output_dir, manifest, stickers)
    return {
        "output_dir": output_dir,
        "png": png_path,
        "pdf": pdf_path,
        "html": html_path,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export sticker images for emoji review.")
    parser.add_argument("run_id", help="Run id under runs/, e.g. 1465")
    parser.add_argument("--columns", type=int, default=5)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_dir = RUNS_DIR / args.run_id
    try:
        paths = export_review_package(run_dir, args.columns)
    except (FileNotFoundError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    print(f"folder: {paths['output_dir']}")
    print(f"png: {paths['png']}")
    print(f"pdf: {paths['pdf']}")
    print(f"html: {paths['html']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
