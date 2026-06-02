#!/usr/bin/env python3
"""Write a validated emoji_plan.json from compact tab-separated input."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from sticker_to_telegram import is_valid_single_emoji


ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = ROOT / "runs"


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def parse_plan(text: str, default_confidence: float) -> list[dict[str, Any]]:
    plans: list[dict[str, Any]] = []
    for row_no, raw_row in enumerate(text.splitlines(), start=1):
        row = raw_row.strip()
        if not row or row.startswith("#"):
            continue
        parts = row.split("\t")
        if len(parts) == 3:
            index_text, emoji_text, reason = parts
            confidence = default_confidence
        elif len(parts) == 4:
            index_text, emoji_text, confidence_text, reason = parts
            try:
                confidence = float(confidence_text)
            except ValueError as exc:
                raise ValueError(f"row {row_no}: invalid confidence {confidence_text!r}") from exc
        else:
            raise ValueError(f"row {row_no}: expected 3 or 4 tab-separated fields")

        try:
            index = int(index_text)
        except ValueError as exc:
            raise ValueError(f"row {row_no}: invalid index {index_text!r}") from exc

        emoji_text = emoji_text.strip()
        if not is_valid_single_emoji(emoji_text):
            raise ValueError(f"row {row_no}: {emoji_text!r} is not a single Unicode emoji")

        plans.append(
            {
                "index": index,
                "emoji_list": [emoji_text],
                "confidence": max(0.0, min(1.0, confidence)),
                "reason": reason.strip()[:240],
            }
        )
    return plans


def validate_complete(run_dir: Path, plans: list[dict[str, Any]]) -> None:
    manifest = read_json(run_dir / "manifest.json")
    stickers = manifest.get("stickers") or []
    expected = set(range(1, len(stickers) + 1))
    actual = [int(plan["index"]) for plan in plans]
    actual_set = set(actual)
    duplicates = sorted({index for index in actual if actual.count(index) > 1})
    missing = sorted(expected - actual_set)
    extra = sorted(actual_set - expected)
    if duplicates or missing or extra:
        raise ValueError(f"incomplete plan: duplicates={duplicates} missing={missing} extra={extra}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write runs/<source_id>/emoji_plan.json from TSV: index<TAB>emoji<TAB>confidence<TAB>reason"
    )
    parser.add_argument("source_id", help="Run id under runs/, e.g. 31511378")
    parser.add_argument("--default-confidence", type=float, default=0.85)
    parser.add_argument("--no-output-copy", action="store_true", help="Do not copy emoji_plan.json into output/")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_dir = RUNS_DIR / args.source_id
    if not (run_dir / "manifest.json").exists():
        raise SystemExit(f"manifest not found: {run_dir / 'manifest.json'}")

    try:
        plans = parse_plan(sys.stdin.read(), args.default_confidence)
        validate_complete(run_dir, plans)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    plan_path = run_dir / "emoji_plan.json"
    write_json(plan_path, plans)
    if not args.no_output_copy:
        output_path = run_dir / "output" / "emoji_plan.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(plan_path, output_path)

    print(f"wrote {len(plans)} emoji plans: {plan_path}")
    print("fallbacks 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
