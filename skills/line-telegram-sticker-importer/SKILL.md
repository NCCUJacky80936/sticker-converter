---
name: line-telegram-sticker-importer
description: Use when importing LINE Sticker Shop packs into Telegram, directly assigning Unicode emoji for stickers without Gemini, validating emoji_plan.json, or creating Telegram sticker sets with a user-provided bot token and numeric Telegram user id.
---

# LINE to Telegram Sticker Importer

Use this skill for requests like "轉換這份 LINE 貼圖", "把 LINE 貼圖匯入 Telegram", "幫這包貼圖配 emoji", or any LINE Sticker Shop URL such as `https://store.line.me/stickershop/product/35753/zh-Hant?ref=Desktop`.

## Core Rules

- Work from the workspace root containing `scripts/sticker_to_telegram.py`.
- Follow the workspace RTK rule for shell calls: prefix normal commands with `rtk` to keep command output compact.
- Prefer the repo-local `.venv`; do not install global Python packages.
- Use the local importer and Telegram Bot API. Do not automate `@chiaki_sticker_bot`.
- Do not write `TELEGRAM_BOT_TOKEN` into docs, logs, skills, README, or memory. If the user explicitly asks to persist their own bot credentials for this local-only workspace, store them only in ignored `.env.local` with `chmod 600`; the CLI auto-loads it.
- If a bot token appears in chat, complete the immediate requested import if possible, then advise the user to revoke/rotate it in `@BotFather`.
- `TELEGRAM_USER_ID` must be numeric, not `@username`. If needed, tell the user to get it from `@userinfobot`.
- The user's personal Telegram credentials may already be stored in `.env.local`; if present, run imports without asking for token/user id again.
- The user must `/start` their own Telegram bot before import.
- Preserve run artifacts under `runs/<source_id>/`; copy user-facing outputs into `runs/<source_id>/output/`.
- `<source_id>` is derived deterministically from supported source URLs; do not work around it with `PYTHONHASHSEED`.
- Do not generate Gemini review/contact-sheet files by default. Use `--skip-review`.
- Keep terminal and chat output compact: do not print full `emoji_plan.json`, manifest JSON, or long file listings unless debugging requires it.

## Emoji Policy

- Assign emoji directly from the sticker images; do not ask Gemini unless the user explicitly wants that handoff.
- Use exactly one emoji per sticker unless the user asks for more. Keep `reason` in concise Traditional Chinese.
- Use real Unicode emoji only. No text labels, kaomoji, punctuation, or custom image emoji.
- Prefer emoji available in the latest Apple/iOS emoji set when the user wants iPhone-friendly output. As of 2026-06-01, that means Unicode Emoji 17.0 / Apple iOS 26.4 support. If the user asks for "latest" in a future session, recheck Unicode official emoji data and Apple/Emojipedia before assuming this is still current.
- Telegram stores Unicode emoji strings in `emoji_list`; it does not embed Apple's emoji artwork. iOS users render those strings with Apple's native emoji font.

## Setup Check

```bash
test -x .venv/bin/python || python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
test -x bin/sticker-importer || command -v sticker-importer
```

If the importer is missing, prefer a workspace-local binary at `bin/sticker-importer` instead of writing to `/usr/local/bin`.

`magick` / ImageMagick may be missing. For static LINE packs this is acceptable because the CLI can use original PNGs and normalize them to Telegram upload PNGs later.

## Default Workflow

1. Download the LINE pack, create preview images, write a fallback plan, and skip Gemini review output:

   ```bash
   .venv/bin/python scripts/sticker_to_telegram.py "<LINE_URL>" --title auto --skip-review
   ```

   The CLI classifies importer failures from stdout/stderr and has a default `STICKER_IMPORTER_TIMEOUT=120` so stuck downloads fail quickly. Preserve the logs under `runs/<source_id>/importer.stdout.log` and `runs/<source_id>/importer.stderr.log`.

2. Determine `<source_id>` from the command output. Inspect sticker images directly:

   - Prefer `runs/<source_id>/vision/*.png` for numbered preview frames.
   - Use the original files under `runs/<source_id>/stickers/` only when previews are unclear.
   - If a temporary visual grid is useful for the agent, create it only in scratch space such as `/private/tmp`; do not place `gemini_contact_sheet.png` in the run output unless the user asks.
   - Avoid printing all image paths. Count files or build one temporary contact sheet instead.

3. Replace `runs/<source_id>/emoji_plan.json` with compact TSV via the helper script:

   ```bash
   .venv/bin/python scripts/write_emoji_plan.py <source_id> <<'TSV'
   1	👌	0.9	OK 手勢
   2	👋	0.9	揮手
   TSV
   ```

   Requirements:

   - Include every sticker index from `1` through the manifest count.
   - One tab-separated row per sticker: `index`, `emoji`, optional `confidence`, `reason`.
   - Each row contains exactly one valid Unicode emoji.
   - The helper validates missing, duplicate, and extra indexes and removes fallback markers by replacing the file.

4. Validate the plan:

   ```bash
   .venv/bin/python -c "import json; m=json.load(open('runs/<source_id>/manifest.json')); p=json.load(open('runs/<source_id>/emoji_plan.json')); print('stickers', len(m['stickers'])); print('plan', len(p)); print('fallbacks', sum(1 for x in p if x.get('fallback'))); print('missing', sorted(set(range(1, len(m['stickers'])+1))-set(x['index'] for x in p)))"
   ```

   Expected: matching sticker/plan counts, `fallbacks 0`, and `missing []`.

5. Regenerate centralized output without Gemini files:

   ```bash
   .venv/bin/python scripts/sticker_to_telegram.py "<LINE_URL>" --title auto --skip-review
   ```

6. Import to Telegram with one-shot secrets:

   ```bash
   .venv/bin/python scripts/sticker_to_telegram.py "<LINE_URL>" --title auto --skip-review --confirm
   ```

   If `.env.local` is absent, use one-shot environment variables instead:

   ```bash
   env TELEGRAM_BOT_TOKEN="<BOT_TOKEN>" TELEGRAM_USER_ID="<NUMERIC_USER_ID>" \
     .venv/bin/python scripts/sticker_to_telegram.py "<LINE_URL>" --title auto --skip-review --confirm
   ```

   The CLI refuses `--confirm` while `emoji_plan.json` contains fallback rows, missing indexes, duplicate indexes, or extra indexes. It prints flushed per-sticker progress (`Telegram: ... n/total`) and updates `runs/<source_id>/telegram_import.json` after every step, so a long import should no longer look silent. Default Telegram timeouts are connect `30s` and read `60s`; if Telegram is slow, set `TELEGRAM_READ_TIMEOUT=120` for that single command rather than waiting on the old 180-second default.

## Telegram Import Details

- The CLI normalizes static stickers into `runs/<source_id>/telegram_upload/*.png`.
- Telegram static sticker PNGs must fit `512 x 512`; if `STICKER_PNG_DIMENSIONS` appears, ensure normalization ran and rerun.
- Avoid batching all files in `createNewStickerSet`; the working pattern is first sticker with `createNewStickerSet`, then one `addStickerToSet` call per remaining sticker.
- Telegram request exceptions are converted to single-line `ToolError` messages and should redact bot tokens. If a raw traceback ever appears, treat the token as exposed and tell the user to rotate it in `@BotFather`.
- `TELEGRAM_USER_ID` is validated before network calls and must be numeric.
- `telegram_import.json` is a progress file, not only a final report. During imports it may contain `status`, `current_index`, `added`, `added_indexes`, and `errors`.
- If `telegram_import.json` already shows a complete successful import, rerunning the command should reuse it before `getMe` instead of making any Telegram network call or trying to create the same sticker set again.
- Output success should include `runs/<source_id>/telegram_import.json`, `added` equal to sticker count, `errors: []`, and a URL like `https://t.me/addstickers/<set_name>`.

## Optional Paths

- OpenAI Vision: only use if the user accepts API billing and provides `OPENAI_API_KEY`; ChatGPT subscriptions do not make API calls free.
- Gemini handoff: only use if explicitly requested, then omit `--skip-review`.

## Failure Handling

- Missing `OPENAI_API_KEY`: use the default direct-emoji workflow instead of blocking.
- `TELEGRAM_USER_ID` is `@username`: stop and ask for the numeric id.
- LINE download fails: trust the CLI's failure classification first; preserve `importer.stdout.log` and `importer.stderr.log`; do not create a partial Telegram set.
- Telegram DNS/network failure: rerun the import command with escalation. The error should not include the bot token; if it does, advise token rotation.
- Telegram import fails mid-run: inspect `runs/<source_id>/telegram_import.json` and the command output before retrying; use `status`, `current_index`, `added`, `added_indexes`, and `errors` to decide whether retry will resume or whether the Telegram set needs manual cleanup.
