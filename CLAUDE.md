# Claude Code Instructions

This repo is an AI-agent workflow for converting a supported sticker source URL into a Telegram sticker set.

Prefer the slash command in `.claude/commands/sticker-convert.md` when the user asks to convert a sticker URL.

## Guardrails

- Keep wording generic. Do not name a specific sticker store or source platform in public docs or commits.
- Do not commit `.env.local`, API keys, Telegram bot tokens, downloaded sticker assets, generated `runs/` outputs, or local importer binaries.
- Use only numeric `TELEGRAM_USER_ID`; do not accept `@username`.
- This tool is for education, research, personal backup, and technical verification. Remind users to purchase paid or protected stickers through official channels.

## Local Workflow

1. Ensure `.venv` exists and install `requirements.txt`.
2. Confirm a compatible importer exists at `bin/sticker-importer` or on `PATH`.
3. Run `scripts/sticker_to_telegram.py "<STICKER_SOURCE_URL>" --title auto --skip-review`.
4. Inspect `runs/<source_id>/vision/`.
5. Write a complete `emoji_plan.json` with `scripts/write_emoji_plan.py`.
6. Validate plan count, fallbacks, and missing indexes.
7. Run `scripts/sticker_to_telegram.py "<STICKER_SOURCE_URL>" --title auto --skip-review --confirm`.
