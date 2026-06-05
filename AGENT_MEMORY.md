# Project Memory

## Sticker Import Workflow

- Use `scripts/sticker_to_telegram.py` as the canonical CLI entrypoint for supported sticker source URLs; older `line_to_telegram.py` references are stale.
- `source_id_from_url()` must stay deterministic. Supported source URLs should resolve to their source product id when possible; fallback ids should use a stable digest, never Python's process-randomized `hash()`.
- The safe import sequence is: preview download with `--skip-review`, inspect `runs/<source_id>/vision/*.png`, write `emoji_plan.json` via `scripts/write_emoji_plan.py`, validate `fallbacks 0` and `missing []`, then run `--confirm`.
- `--confirm` should block before Telegram API calls if `emoji_plan.json` has fallback rows, missing indexes, duplicate indexes, or extra indexes. Do not rely on post-upload emoji repair except for recovering older already-created sets.
- After a successful `--confirm`, delete `runs/<source_id>/` by default so sticker assets and generated run outputs are not retained locally. Keep files only with `--keep-run-files` for debugging; failed or preview-only runs should remain for inspection.
- For animated/video sticker outputs, review tooling should use manifest `preview_file` frames when available; opening `.webm` stickers directly with Pillow is expected to fail.

## Validation Checklist

- Run `.venv/bin/python -m py_compile scripts/sticker_to_telegram.py scripts/write_emoji_plan.py scripts/export_review.py`.
- For a candidate run, validate `stickers == plan`, `fallbacks 0`, and `missing []` before `--confirm`.
- Keep downloaded assets, generated runs, `.env.local`, tokens, API keys, and local importer binaries out of commits and memories.
