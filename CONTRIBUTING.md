# Contributing / 貢獻指南

## 繁體中文

感謝你想改進這個專案。這個工具處理第三方貼圖素材與 Telegram bot credentials，因此請優先保持安全、泛化描述與可重跑。

### 開發環境

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### 提交前檢查

```bash
.venv/bin/python -m py_compile scripts/sticker_to_telegram.py scripts/write_emoji_plan.py scripts/export_review.py
```

若你修改了 Telegram 匯入流程，請至少用一個小型貼圖包跑過：

```bash
.venv/bin/python scripts/sticker_to_telegram.py "<STICKER_SOURCE_URL>" --title auto --skip-review
```

### Pull Request 原則

- 本專案僅開源工具程式碼，且僅供教學、研究與技術驗證；不要加入會暗示本專案授權第三方貼圖素材再散布的文字或功能。
- 文件與檔名應維持泛化描述，例如「貼圖來源」、「貼圖轉換」、「sticker source」，不要指名特定貼圖商店或平台。
- 若範例需要貼圖來源，請使用 URL 佔位符，不要 commit 實際下載後的素材。
- 文件中必須保留「請支持創作者並透過官方管道購買正版」的提醒。
- 不要 commit `.env.local`、token、API key、`runs/` 內容、下載後的貼圖素材，或本機 importer binary。
- 不要把使用者的 Telegram bot token 寫到 log、文件、測試 fixture 或錯誤訊息。
- 保持 CLI 可重跑。匯入進度應繼續寫入 `telegram_import.json`。
- 若新增 CLI 參數，請同步更新 `README.md`。
- 若修改 emoji plan 格式，請同步更新 `scripts/write_emoji_plan.py` 的驗證邏輯與 README 範例。

## English

Thanks for improving this project. The tool handles third-party sticker assets and Telegram bot credentials, so keep safety, generic wording, and resumability first.

### Development

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### Checks Before Submitting

```bash
.venv/bin/python -m py_compile scripts/sticker_to_telegram.py scripts/write_emoji_plan.py scripts/export_review.py
```

If you change the Telegram import flow, run at least one small pack locally:

```bash
.venv/bin/python scripts/sticker_to_telegram.py "<STICKER_SOURCE_URL>" --title auto --skip-review
```

### Pull Request Rules

- This project open-sources only the tool code and is intended only for education, research, and technical verification. Do not add text or features that imply this project licenses third-party sticker assets for redistribution.
- Keep docs and filenames generic, such as "sticker source", "sticker conversion", and "sticker source URL". Do not name a specific sticker store or source platform.
- If examples need sticker sources, use URL placeholders. Do not commit actual downloaded assets.
- Keep the reminder to support creators by purchasing official copies through authorized channels.
- Do not commit `.env.local`, tokens, API keys, `runs/` contents, downloaded sticker assets, or local importer binaries.
- Do not write Telegram bot tokens into logs, docs, fixtures, or error messages.
- Keep the CLI resumable. Import progress should keep writing to `telegram_import.json`.
- If you add CLI flags, update `README.md`.
- If you change the emoji plan format, update `scripts/write_emoji_plan.py` validation and README examples.
