# Publishing to GitHub / 發佈到 GitHub

## 繁體中文

這個資料夾已整理成可公開的 GitHub 專案格式。

## 發佈前檢查

確認 README 保留著作權與用途警示：本工具僅供教學、研究與技術驗證；若需使用付費或受保護的貼圖，請支持創作者並透過官方管道購買正版。

確認公開文字維持泛化描述，不指名特定貼圖商店或來源平台。

確認以下檔案不會被公開：

- `.env.local`
- `.venv/`
- `runs/`
- `bin/sticker-importer`
- 其他本機 importer binary
- `scripts/__pycache__/`
- 任何下載後的貼圖素材

執行基本檢查：

```bash
.venv/bin/python -m py_compile scripts/sticker_to_telegram.py scripts/write_emoji_plan.py scripts/export_review.py
```

初始化與首次 commit：

```bash
git init
git add README.md LICENSE CONTRIBUTING.md SECURITY.md AGENTS.md CLAUDE.md .claude .env.example .gitignore requirements.txt scripts skills docs bin/.gitkeep runs/.gitkeep
git commit -m "Initial open source release"
```

若你使用 GitHub CLI：

```bash
gh repo create sticker-converter --public --source=. --remote=origin --push
```

若你在 GitHub 網站上手動建立 repo：

```bash
git branch -M main
git remote add origin git@github.com:<OWNER>/sticker-converter.git
git push -u origin main
```

## English

This folder is structured as a public GitHub project.

## Pre-Publish Checks

Make sure README keeps the copyright and usage notice: this tool is only for education, research, and technical verification; if users want paid or protected stickers, they should support creators by purchasing them through official channels.

Make sure public wording stays generic and does not name a specific sticker store or source platform.

Make sure these files are not published:

- `.env.local`
- `.venv/`
- `runs/`
- `bin/sticker-importer`
- other local importer binaries
- `scripts/__pycache__/`
- any downloaded sticker assets

Run the basic check:

```bash
.venv/bin/python -m py_compile scripts/sticker_to_telegram.py scripts/write_emoji_plan.py scripts/export_review.py
```

Initialize and create the first commit:

```bash
git init
git add README.md LICENSE CONTRIBUTING.md SECURITY.md AGENTS.md CLAUDE.md .claude .env.example .gitignore requirements.txt scripts skills docs bin/.gitkeep runs/.gitkeep
git commit -m "Initial open source release"
```

With GitHub CLI:

```bash
gh repo create sticker-converter --public --source=. --remote=origin --push
```

If you create the GitHub repository manually:

```bash
git branch -M main
git remote add origin git@github.com:<OWNER>/sticker-converter.git
git push -u origin main
```
