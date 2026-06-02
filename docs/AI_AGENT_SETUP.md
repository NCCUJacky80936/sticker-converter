# AI Agent Setup / AI Agent 使用方式

## 繁體中文

這個 repository 可以被 Codex、Claude Code 或其他 coding agent 下載後作為貼圖轉換 workflow 使用。核心是：

- `skills/sticker-telegram-importer/SKILL.md`：Codex-style skill。
- `AGENTS.md`：通用 agent / Codex 專案指令。
- `CLAUDE.md`：Claude Code 專案指令。
- `.claude/commands/sticker-convert.md`：Claude Code slash command。
- `scripts/`：agent 實際執行的 deterministic CLI。

## Codex 使用

方式一：直接 clone repo，讓 Codex 在 repo root 工作。Codex 會讀取 `AGENTS.md`，並可使用 `skills/sticker-telegram-importer/SKILL.md` 的流程。

```bash
git clone https://github.com/NCCUJacky80936/sticker-converter.git
cd sticker-converter
```

方式二：把 skill 複製到你的 Codex skills 目錄：

```bash
mkdir -p ~/.codex/skills
cp -R skills/sticker-telegram-importer ~/.codex/skills/
```

然後在對話中提供貼圖來源 URL，請 agent 使用 sticker conversion workflow。

## Claude Code 使用

Clone repo 後，在 repo root 啟動 Claude Code：

```bash
git clone https://github.com/NCCUJacky80936/sticker-converter.git
cd sticker-converter
claude
```

Claude Code 會讀取 `CLAUDE.md`。若支援 slash commands，可使用 `.claude/commands/sticker-convert.md` 所定義的流程。

## 必要本機設定

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env.local
chmod 600 .env.local
```

`.env.local` 至少需要：

```bash
TELEGRAM_BOT_TOKEN="..."
TELEGRAM_USER_ID="123456789"
```

`TELEGRAM_USER_ID` 必須是純數字。使用 Telegram 前，請先對自己的 bot 送出 `/start`。

還需要準備相容的貼圖下載器 binary：

```bash
bin/sticker-importer
```

請勿把 `.env.local`、下載後的貼圖素材、`runs/` 輸出或本機 binary commit 到 repo。

## English

This repository can be cloned by Codex, Claude Code, or other coding agents as a sticker conversion workflow. The core files are:

- `skills/sticker-telegram-importer/SKILL.md`: Codex-style skill.
- `AGENTS.md`: generic agent / Codex project instructions.
- `CLAUDE.md`: Claude Code project instructions.
- `.claude/commands/sticker-convert.md`: Claude Code slash command.
- `scripts/`: deterministic CLI used by the agent.

## Codex Usage

Option 1: clone the repo and let Codex work from the repo root. Codex can read `AGENTS.md` and follow the workflow in `skills/sticker-telegram-importer/SKILL.md`.

```bash
git clone https://github.com/NCCUJacky80936/sticker-converter.git
cd sticker-converter
```

Option 2: copy the skill into your Codex skills directory:

```bash
mkdir -p ~/.codex/skills
cp -R skills/sticker-telegram-importer ~/.codex/skills/
```

Then provide a sticker source URL in chat and ask the agent to use the sticker conversion workflow.

## Claude Code Usage

Clone the repo and start Claude Code from the repo root:

```bash
git clone https://github.com/NCCUJacky80936/sticker-converter.git
cd sticker-converter
claude
```

Claude Code can read `CLAUDE.md`. If slash commands are enabled, use the workflow in `.claude/commands/sticker-convert.md`.

## Required Local Setup

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env.local
chmod 600 .env.local
```

`.env.local` needs at least:

```bash
TELEGRAM_BOT_TOKEN="..."
TELEGRAM_USER_ID="123456789"
```

`TELEGRAM_USER_ID` must be numeric. Before Telegram import, send `/start` to your own bot.

Prepare a compatible sticker importer binary:

```bash
bin/sticker-importer
```

Do not commit `.env.local`, downloaded sticker assets, `runs/` outputs, or local binaries.
