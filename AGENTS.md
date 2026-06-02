# Agent Instructions

This repository provides an AI-agent workflow for converting a supported sticker source URL into a Telegram sticker set.

## Use This Workflow When

- The user provides a sticker source URL and asks to convert it.
- The user asks to assign emoji to every sticker.
- The user asks to create a Telegram sticker set from local sticker outputs.

## Required Safety Rules

- Keep public wording generic. Do not name a specific sticker store or source platform.
- Do not commit downloaded sticker assets, generated run outputs, `.env.local`, tokens, API keys, or local importer binaries.
- This project is for education, research, personal backup, and technical verification. Remind users to support creators by purchasing paid or protected stickers through official channels.
- Never write `TELEGRAM_BOT_TOKEN` into docs, logs, commits, memories, or command files.
- `TELEGRAM_USER_ID` must be numeric, not `@username`.

## Default Commands

Install dependencies:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Download and prepare previews without creating a Telegram sticker set:

```bash
.venv/bin/python scripts/sticker_to_telegram.py "<STICKER_SOURCE_URL>" --title auto --skip-review
```

Write a validated emoji plan:

```bash
.venv/bin/python scripts/write_emoji_plan.py <source_id> <<'TSV'
1	👌	0.9	OK gesture
2	👋	0.9	wave
TSV
```

Create the Telegram sticker set after `emoji_plan.json` is complete:

```bash
.venv/bin/python scripts/sticker_to_telegram.py "<STICKER_SOURCE_URL>" --title auto --skip-review --confirm
```

## Validation

```bash
.venv/bin/python -m py_compile scripts/sticker_to_telegram.py scripts/write_emoji_plan.py scripts/export_review.py
```

Validate `emoji_plan.json`:

```bash
.venv/bin/python -c "import json; m=json.load(open('runs/<source_id>/manifest.json')); p=json.load(open('runs/<source_id>/emoji_plan.json')); print('stickers', len(m['stickers'])); print('plan', len(p)); print('fallbacks', sum(1 for x in p if x.get('fallback'))); print('missing', sorted(set(range(1, len(m['stickers'])+1))-set(x['index'] for x in p)))"
```

Expected: matching sticker and plan counts, `fallbacks 0`, and `missing []`.
