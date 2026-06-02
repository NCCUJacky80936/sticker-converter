# Sticker Converter

繁體中文 | [English](#english)

給 Codex、Claude Code 等 AI agent 使用的貼圖轉換 skill / workflow。把這個 repository 下載到本機後，agent 可以依照內建指令，把支援的貼圖來源網址轉成 Telegram 貼圖包。

貼上支援的貼圖網址後，workflow 會下載貼圖、產生本地預覽、建立或套用逐張 emoji 對應，最後透過 Telegram Bot API 建立貼圖包。你也可以直接把 `scripts/` 當成本地 CLI 使用。

> 這個專案只提供轉換工具與流程，不包含任何貼圖素材、Telegram token、API key，或任何下載後的輸出檔。

## 著作權與用途警示

本 open-source 專案僅適用於教學、研究、個人備份與技術驗證。專案授權只涵蓋本工具的原始碼，不授權、不轉授權、也不主張取得任何貼圖、角色、圖像、文字、商標或其他第三方內容的權利。

若你要使用任何付費或受保護的貼圖，請透過官方商店、官方平台或授權管道支持原作者並購買正版。請不要將下載後的貼圖素材、轉換後的圖檔或 Telegram 貼圖包作為公開散布、商業使用、再上架、轉售或規避購買的用途。使用者需自行確認其行為符合來源平台、Telegram、創作者授權條款與所在地法律。

## 功能

- 提供 Codex-style skill：`skills/sticker-telegram-importer/SKILL.md`。
- 提供通用 agent 指令：`AGENTS.md`。
- 提供 Claude Code 指令與 slash command：`CLAUDE.md`、`.claude/commands/sticker-convert.md`。
- 一個貼圖來源 URL 產生一個 `runs/<source_id>/` 工作目錄。
- 使用相容的本地貼圖下載器取得素材。
- 為靜態貼圖產生 Telegram 可上傳的 `512 x 512` PNG。
- 支援 AI agent 依預覽圖指派 emoji，並用 TSV helper 寫入驗證過的 emoji plan。
- 驗證每張貼圖都有對應的單一 Unicode emoji。
- 使用 Telegram Bot API 建立貼圖包，並在中途失敗時留下可重跑的 `telegram_import.json`。
- 預設不輸出 review contact sheet；需要時可另外匯出。

## 系統需求

- Python 3.11 或更新版本。
- 相容的貼圖下載器 binary，放在 `bin/sticker-importer`，或已安裝在 `PATH`。
- Telegram bot token 與數字 user ID。
- - 選用：`ffmpeg`，只有在需要從影片貼圖抽預覽幀時需要。

## AI Agent 使用

詳細安裝與使用方式見 [docs/AI_AGENT_SETUP.md](docs/AI_AGENT_SETUP.md)。

Codex：

```bash
git clone https://github.com/NCCUJacky80936/sticker-converter.git
cd sticker-converter
```

也可以把 skill 複製到 Codex skills 目錄：

```bash
mkdir -p ~/.codex/skills
cp -R skills/sticker-telegram-importer ~/.codex/skills/
```

Claude Code：

```bash
git clone https://github.com/NCCUJacky80936/sticker-converter.git
cd sticker-converter
claude
```

Claude Code 可讀取 `CLAUDE.md`，並使用 `.claude/commands/sticker-convert.md` 的流程。

## 安裝

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

準備相容的貼圖下載器，並放在：

```bash
bin/sticker-importer
```

若你要公開 fork，不要把本機 binary commit 進 repo。

## 設定 Telegram

複製範例環境檔：

```bash
cp .env.example .env.local
chmod 600 .env.local
```

填入：

```bash
TELEGRAM_BOT_TOKEN="123456:..."
TELEGRAM_USER_ID="123456789"
```

`TELEGRAM_USER_ID` 必須是純數字，不是 `@username`。可以向 `@userinfobot` 查詢。使用前請先私訊自己的 Telegram bot 並送出 `/start`。

## 基本流程

先下載貼圖、產生預覽與 fallback emoji plan，不建立 Telegram 貼圖包：

```bash
.venv/bin/python scripts/sticker_to_telegram.py "<STICKER_SOURCE_URL>" --title auto --skip-review
```

檢查 `runs/<source_id>/vision/` 的預覽圖後，用 TSV 覆寫逐張 emoji：

```bash
.venv/bin/python scripts/write_emoji_plan.py <source_id> <<'TSV'
1	🛒	0.86	購物與食物
2	👍	0.88	稱讚
TSV
```

TSV 欄位是：

```text
index<TAB>emoji<TAB>confidence<TAB>reason
```

每張貼圖都必須有一列，而且 `emoji` 必須是單一 Unicode emoji。

驗證 plan：

```bash
.venv/bin/python -c "import json; m=json.load(open('runs/<source_id>/manifest.json')); p=json.load(open('runs/<source_id>/emoji_plan.json')); print('stickers', len(m['stickers'])); print('plan', len(p)); print('fallbacks', sum(1 for x in p if x.get('fallback'))); print('missing', sorted(set(range(1, len(m['stickers'])+1))-set(x['index'] for x in p)))"
```

預期結果：

```text
stickers 40
plan 40
fallbacks 0
missing []
```

確認後建立 Telegram 貼圖包：

```bash
.venv/bin/python scripts/sticker_to_telegram.py "<STICKER_SOURCE_URL>" --title auto --skip-review --confirm
```

成功時會輸出：

```text
sticker_set: https://t.me/addstickers/<set_name>
```

## 由 AI agent 依預覽圖產生 emoji

Codex、Claude Code 等 multimodal agent 會直接檢查 `runs/<source_id>/vision/` 的預覽圖，然後用 `scripts/write_emoji_plan.py` 寫入逐張 emoji。CLI 本身不呼叫額外圖像辨識 API。

```bash
.venv/bin/python scripts/write_emoji_plan.py <source_id> <<'TSV'
1	👌	0.9	OK gesture
2	👋	0.9	wave
TSV
```

如果已經有 `emoji_plan.json`，工具會沿用既有 plan。需要重配 emoji 時，請重新執行 `scripts/write_emoji_plan.py` 覆寫整份 plan。

## 選用：review 匯出

預設流程使用 `--skip-review`，不產生 contact sheet。若需要把預覽圖交給其他模型或人工審查：

```bash
.venv/bin/python scripts/export_review.py <source_id>
```

輸出會在 `runs/<source_id>/review/`。

## 常見輸出

- `runs/<source_id>/manifest.json`：下載來源、貼圖清單與 metadata。
- `runs/<source_id>/emoji_plan.json`：每張貼圖的 emoji、信心分數與理由。
- `runs/<source_id>/vision/`：給人或模型檢查的預覽圖。
- `runs/<source_id>/telegram_upload/`：Telegram 規格化上傳圖。
- `runs/<source_id>/telegram_import.json`：Telegram 建包進度與結果。
- `runs/<source_id>/output/`：集中複製常用 JSON 結果。

`runs/` 是本機輸出資料，不應 commit。

## 疑難排解

- `找不到貼圖下載器`：確認 `bin/sticker-importer` 可執行，或相容下載器在 `PATH`。
- `DNS/網路解析失敗`：確認目前環境允許連到貼圖來源或 Telegram。
- `TELEGRAM_USER_ID 必須是純數字`：不要使用 `@username`。
- `bot was blocked` 或 `forbidden`：先對你的 Telegram bot 送出 `/start`。
- `STICKER_PNG_DIMENSIONS`：確認工具已產生 `telegram_upload/`，再重跑 `--confirm`。
- 中途失敗：先看 `runs/<source_id>/telegram_import.json`，工具會記錄已新增張數與錯誤，重跑通常會從既有進度恢復。

## 授權與使用界線

本專案以 MIT License 發佈，授權範圍僅限本 repository 內的工具原始碼。MIT License 不涵蓋任何透過本工具下載、讀取、轉換或上傳的貼圖素材。

本工具僅供教學研究與技術驗證使用。若你要使用付費或受保護的貼圖，請支持創作者並透過官方管道購買正版。請自行確認你下載與轉換貼圖的使用方式符合來源平台、Telegram、創作者授權與所在地法律規範。不要把下載後的貼圖素材、轉換後的圖檔或第三方授權 binary commit 到公開 repo。

## English

Sticker conversion skill / workflow for AI agents such as Codex and Claude Code. Clone this repository locally, then let the agent follow the bundled instructions to convert supported sticker source URLs into Telegram sticker sets.

After a supported sticker URL is provided, the workflow downloads the stickers, generates local previews, creates or applies per-sticker emoji mappings, and creates a Telegram sticker set through the Telegram Bot API. You can also use `scripts/` directly as a local CLI.

> This repository ships the tool and workflow only. It does not include sticker assets, Telegram tokens, or generated run outputs.

## Copyright and Usage Notice

This open-source project is intended only for education, research, personal backup, and technical verification. The project license covers only this tool's source code. It does not license, sublicense, or claim rights to any stickers, characters, images, text, trademarks, or other third-party content.

If you want to use paid or protected stickers, support the original creators by purchasing them through official stores, official platforms, or authorized channels. Do not use downloaded sticker assets, converted image files, or generated Telegram sticker sets for public redistribution, commercial use, re-listing, resale, or purchase circumvention. Users are responsible for complying with the source platform, Telegram, creator licenses, and applicable law.

## Features

- Provides a Codex-style skill: `skills/sticker-telegram-importer/SKILL.md`.
- Provides generic agent instructions: `AGENTS.md`.
- Provides Claude Code instructions and a slash command: `CLAUDE.md`, `.claude/commands/sticker-convert.md`.
- Creates one `runs/<source_id>/` workspace per sticker source URL.
- Downloads sticker assets with a compatible local importer.
- Normalizes static stickers into Telegram-ready `512 x 512` PNG files.
- Uses AI-agent visual inspection plus a TSV helper for validated emoji planning.
- Validates that every sticker has exactly one Unicode emoji.
- Creates Telegram sticker sets through the Telegram Bot API and stores resumable progress in `telegram_import.json`.
- Skips review contact sheets by default; exports them only when requested.

## Requirements

- Python 3.11 or newer.
- A compatible sticker importer binary at `bin/sticker-importer` or on your `PATH`.
- Telegram bot token and numeric Telegram user ID.
- Optional: `ffmpeg`, only for extracting preview frames from video stickers.

## AI Agent Usage

See [docs/AI_AGENT_SETUP.md](docs/AI_AGENT_SETUP.md) for detailed setup.

Codex:

```bash
git clone https://github.com/NCCUJacky80936/sticker-converter.git
cd sticker-converter
```

You can also copy the skill into your Codex skills directory:

```bash
mkdir -p ~/.codex/skills
cp -R skills/sticker-telegram-importer ~/.codex/skills/
```

Claude Code:

```bash
git clone https://github.com/NCCUJacky80936/sticker-converter.git
cd sticker-converter
claude
```

Claude Code can read `CLAUDE.md` and use the workflow in `.claude/commands/sticker-convert.md`.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Prepare a compatible sticker importer binary and place it at:

```bash
bin/sticker-importer
```

Do not commit local binaries to public forks.

## Telegram Setup

Copy the example environment file:

```bash
cp .env.example .env.local
chmod 600 .env.local
```

Fill in:

```bash
TELEGRAM_BOT_TOKEN="123456:..."
TELEGRAM_USER_ID="123456789"
```

`TELEGRAM_USER_ID` must be numeric, not `@username`. You can get it from `@userinfobot`. Before importing, open a chat with your bot and send `/start`.

## Basic Workflow

Download the pack, generate previews, and write a fallback emoji plan without creating a Telegram sticker set:

```bash
.venv/bin/python scripts/sticker_to_telegram.py "<STICKER_SOURCE_URL>" --title auto --skip-review
```

Inspect `runs/<source_id>/vision/`, then replace the emoji plan with TSV:

```bash
.venv/bin/python scripts/write_emoji_plan.py <source_id> <<'TSV'
1	🛒	0.86	shopping and food
2	👍	0.88	approval
TSV
```

TSV fields:

```text
index<TAB>emoji<TAB>confidence<TAB>reason
```

Every sticker must have one row, and `emoji` must be a single Unicode emoji.

Validate the plan:

```bash
.venv/bin/python -c "import json; m=json.load(open('runs/<source_id>/manifest.json')); p=json.load(open('runs/<source_id>/emoji_plan.json')); print('stickers', len(m['stickers'])); print('plan', len(p)); print('fallbacks', sum(1 for x in p if x.get('fallback'))); print('missing', sorted(set(range(1, len(m['stickers'])+1))-set(x['index'] for x in p)))"
```

Expected:

```text
stickers 40
plan 40
fallbacks 0
missing []
```

Create the Telegram sticker set:

```bash
.venv/bin/python scripts/sticker_to_telegram.py "<STICKER_SOURCE_URL>" --title auto --skip-review --confirm
```

On success:

```text
sticker_set: https://t.me/addstickers/<set_name>
```

## AI-Agent Emoji Planning

Codex, Claude Code, or another multimodal agent should inspect `runs/<source_id>/vision/` previews, then write per-sticker emoji with `scripts/write_emoji_plan.py`. The CLI itself does not call an extra image-recognition API.

```bash
.venv/bin/python scripts/write_emoji_plan.py <source_id> <<'TSV'
1	👌	0.9	OK gesture
2	👋	0.9	wave
TSV
```

If `emoji_plan.json` already exists, the tool reuses it. To regenerate emoji assignments, rerun `scripts/write_emoji_plan.py` and replace the whole plan.

## Optional Review Export

The default workflow uses `--skip-review`. To export a review package for another model or manual checking:

```bash
.venv/bin/python scripts/export_review.py <source_id>
```

Files are written to `runs/<source_id>/review/`.

## Outputs

- `runs/<source_id>/manifest.json`: source URL, sticker list, and metadata.
- `runs/<source_id>/emoji_plan.json`: emoji, confidence, and reason per sticker.
- `runs/<source_id>/vision/`: preview images for review.
- `runs/<source_id>/telegram_upload/`: Telegram-normalized upload files.
- `runs/<source_id>/telegram_import.json`: Telegram import progress and result.
- `runs/<source_id>/output/`: copied user-facing JSON outputs.

`runs/` is local generated data and should not be committed.

## Troubleshooting

- `sticker importer not found`: make sure `bin/sticker-importer` is executable or a compatible importer is on `PATH`.
- `DNS/name resolution failed`: make sure the environment can reach the sticker source or Telegram.
- `TELEGRAM_USER_ID must be numeric`: do not use `@username`.
- `bot was blocked` or `forbidden`: send `/start` to your Telegram bot first.
- `STICKER_PNG_DIMENSIONS`: make sure `telegram_upload/` was generated, then rerun with `--confirm`.
- Partial failure: inspect `runs/<source_id>/telegram_import.json`; the importer records progress and usually resumes on rerun.

## License and Usage Boundaries

This project is released under the MIT License, but that license applies only to the tool source code in this repository. It does not cover any sticker assets downloaded, read, converted, or uploaded with this tool.

This tool is intended only for education, research, and technical verification. If you want to use paid or protected stickers, support the creators by purchasing them through official channels. Make sure your use of downloaded and converted stickers complies with the source platform, Telegram, creator licenses, and applicable law. Do not commit downloaded sticker assets, converted image files, or third-party binaries to public repositories.
