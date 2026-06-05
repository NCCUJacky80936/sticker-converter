---
name: sticker-telegram-importer
description: Use when converting a sticker source URL into a Telegram sticker set, assigning Unicode emoji for stickers, validating emoji_plan.json, or creating Telegram sticker sets with a user-provided bot token and numeric Telegram user id.
---

# Sticker to Telegram Importer

Use this skill for requests like "轉換這份貼圖", "把貼圖匯入 Telegram", "幫這包貼圖配 emoji", or any supported sticker source URL.

## Core Rules

- Work from the workspace root containing `scripts/sticker_to_telegram.py`.
- Prefer the repo-local `.venv`; do not install global Python packages.
- Use the local importer and Telegram Bot API.
- Do not write `TELEGRAM_BOT_TOKEN` into docs, logs, skills, README, or memory. If the user explicitly asks to persist their own bot credentials for this local-only workspace, store them only in ignored `.env.local` with `chmod 600`; the CLI auto-loads it.
- If a bot token appears in chat, complete the immediate requested import if possible, then advise the user to revoke or rotate it.
- `TELEGRAM_USER_ID` must be numeric, not `@username`. If needed, tell the user to get it from `@userinfobot`.
- The user's personal Telegram credentials may already be stored in `.env.local`; if present, run imports without asking for token/user id again.
- The user must `/start` their own Telegram bot before import.
- Preserve run artifacts under `runs/<source_id>/` while preparing previews and emoji, then let successful `--confirm` delete the run directory by default.
- `<source_id>` is derived deterministically from supported source URLs; do not work around it with `PYTHONHASHSEED`.
- Do not generate review contact-sheet files by default. Use `--skip-review`.
- Keep terminal and chat output compact: do not print full `emoji_plan.json`, manifest JSON, or long file listings unless debugging requires it.
- Keep public docs and filenames generic. Do not name a specific sticker store or source platform.

## Emoji Policy

- Assign emoji directly from the sticker images by inspecting `runs/<source_id>/vision/*.png`.
- Use exactly one emoji per sticker unless the user asks for more. Keep `reason` concise.
- Use real Unicode emoji only. No text labels, kaomoji, punctuation, or custom image emoji.
- Telegram stores Unicode emoji strings in `emoji_list`; it does not embed any specific platform emoji artwork.

## Setup Check

```bash
test -x .venv/bin/python || python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
test -x bin/sticker-importer || command -v sticker-importer
```

If the importer binary is missing, prefer a workspace-local binary at `bin/sticker-importer` instead of writing to a system directory.

## Default Workflow

1. Download the sticker pack, create preview images, write a fallback plan, and skip review output:

   ```bash
   .venv/bin/python scripts/sticker_to_telegram.py "<STICKER_SOURCE_URL>" --title auto --skip-review
   ```

2. Determine `<source_id>` from the command output. Inspect sticker images directly:

   - Prefer `runs/<source_id>/vision/*.png` for numbered preview frames.
   - Use the original files under `runs/<source_id>/stickers/` only when previews are unclear.
   - If a temporary visual grid is useful for the agent, create it only in scratch space such as `/private/tmp`.

3. Replace `runs/<source_id>/emoji_plan.json` with compact TSV via the helper script:

   ```bash
   .venv/bin/python scripts/write_emoji_plan.py <source_id> <<'TSV'
   1	👌	0.9	OK 手勢
   2	👋	0.9	揮手
   TSV
   ```

4. Validate the plan:

   ```bash
   .venv/bin/python -c "import json; m=json.load(open('runs/<source_id>/manifest.json')); p=json.load(open('runs/<source_id>/emoji_plan.json')); print('stickers', len(m['stickers'])); print('plan', len(p)); print('fallbacks', sum(1 for x in p if x.get('fallback'))); print('missing', sorted(set(range(1, len(m['stickers'])+1))-set(x['index'] for x in p)))"
   ```

   Expected: matching sticker/plan counts, `fallbacks 0`, and `missing []`.

5. Regenerate centralized output without review files:

   ```bash
   .venv/bin/python scripts/sticker_to_telegram.py "<STICKER_SOURCE_URL>" --title auto --skip-review
   ```

6. Import to Telegram:

   ```bash
   .venv/bin/python scripts/sticker_to_telegram.py "<STICKER_SOURCE_URL>" --title auto --skip-review --confirm
   ```

   The CLI refuses `--confirm` while `emoji_plan.json` contains fallback rows, missing indexes, duplicate indexes, or extra indexes. If it stops there, write the plan with `scripts/write_emoji_plan.py` and rerun the exact same command.
   After a successful import, it deletes `runs/<source_id>/` so generated sticker assets are not retained locally. Add `--keep-run-files` only when debugging.

   If `.env.local` is absent, use one-shot environment variables instead:

   ```bash
   env TELEGRAM_BOT_TOKEN="<BOT_TOKEN>" TELEGRAM_USER_ID="<NUMERIC_USER_ID>" \
     .venv/bin/python scripts/sticker_to_telegram.py "<STICKER_SOURCE_URL>" --title auto --skip-review --confirm
   ```

## Telegram Import Details

- The CLI normalizes static stickers into `runs/<source_id>/telegram_upload/*.png`.
- Telegram static sticker PNGs must fit `512 x 512`.
- Avoid batching all files in `createNewStickerSet`; the working pattern is first sticker with `createNewStickerSet`, then one `addStickerToSet` call per remaining sticker.
- Telegram request exceptions are converted to single-line `ToolError` messages and should redact bot tokens.
- Do not manually repair fallback emoji after upload unless recovering an older set; the normal flow should block before creating a set with fallback emoji.
- `TELEGRAM_USER_ID` is validated before network calls and must be numeric.
- `telegram_import.json` is a progress file, not only a final report. It remains only for incomplete/failed imports or when `--keep-run-files` is used.
- Output success should include a URL like `https://t.me/addstickers/<set_name>` and a cleanup line showing `runs/<source_id>/` was deleted.

## Failure Handling

- `TELEGRAM_USER_ID` is `@username`: stop and ask for the numeric id.
- Source download fails: trust the CLI's failure classification first; preserve importer logs; do not create a partial Telegram set.
- Telegram DNS/network failure: rerun the import command with escalation.
- Telegram import fails mid-run: inspect `runs/<source_id>/telegram_import.json` and the command output before retrying.
