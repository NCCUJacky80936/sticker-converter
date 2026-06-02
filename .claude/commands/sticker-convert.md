# Sticker Convert

Convert a supported sticker source URL into a Telegram sticker set.

## Inputs

- Sticker source URL from the user.
- Telegram bot token and numeric Telegram user ID, usually stored in `.env.local`.
- Compatible importer binary at `bin/sticker-importer` or on `PATH`.

## Steps

1. Run setup if needed:

   ```bash
   test -x .venv/bin/python || python3 -m venv .venv
   .venv/bin/python -m pip install -r requirements.txt
   ```

2. Download and generate previews without importing:

   ```bash
   .venv/bin/python scripts/sticker_to_telegram.py "<STICKER_SOURCE_URL>" --title auto --skip-review
   ```

3. Inspect `runs/<source_id>/vision/*.png` and assign exactly one Unicode emoji per sticker.

4. Write the emoji plan:

   ```bash
   .venv/bin/python scripts/write_emoji_plan.py <source_id> <<'TSV'
   1	👌	0.9	OK gesture
   2	👋	0.9	wave
   TSV
   ```

5. Validate:

   ```bash
   .venv/bin/python -c "import json; m=json.load(open('runs/<source_id>/manifest.json')); p=json.load(open('runs/<source_id>/emoji_plan.json')); print('stickers', len(m['stickers'])); print('plan', len(p)); print('fallbacks', sum(1 for x in p if x.get('fallback'))); print('missing', sorted(set(range(1, len(m['stickers'])+1))-set(x['index'] for x in p)))"
   ```

6. Import:

   ```bash
   .venv/bin/python scripts/sticker_to_telegram.py "<STICKER_SOURCE_URL>" --title auto --skip-review --confirm
   ```

## Rules

- Keep public wording generic; do not name a specific sticker store or source platform.
- Do not expose or commit secrets.
- Do not commit downloaded sticker assets or generated run outputs.
- Remind users that paid or protected stickers should be purchased through official channels.
