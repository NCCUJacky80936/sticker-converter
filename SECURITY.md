# Security Policy / 安全政策

## 繁體中文

## 回報安全問題

請不要在公開 issue 貼出 Telegram bot token、API key、私有貼圖素材或可識別個人資料。若你發現 token 外洩、錯誤訊息未遮蔽 secret，或匯入流程會意外公開本機檔案，請用私下管道回報維護者。

## Secret 管理

- 使用 `.env.local` 儲存本機 token，並設定 `chmod 600 .env.local`。
- `.env.local` 已在 `.gitignore` 中排除，不要改成可 commit。
- 若 token 曾貼到公開 issue、PR、log 或聊天紀錄，請立刻旋轉。

## Generated Data

`runs/` 可能包含下載後的貼圖素材、Telegram 匯入結果與本機 log。這些檔案預設不應進入公開 repo。

## Copyright-Sensitive Assets

本專案僅供教學、研究與技術驗證。下載後的貼圖素材與轉換後圖檔可能受著作權、商標權與平台條款保護，請不要公開散布或 commit。若需要使用付費或受保護的貼圖，請支持創作者並透過官方管道購買正版。

## English

## Reporting Security Issues

Do not post Telegram bot tokens, private sticker assets, or personally identifiable information in public issues. If you find a token leak, unredacted secret in an error message, or a path that unexpectedly exposes local files, report it privately to the maintainer.

## Secret Handling

- Store local tokens in `.env.local` and run `chmod 600 .env.local`.
- `.env.local` is ignored by `.gitignore`; do not make it commit-able.
- If a token appears in a public issue, PR, log, or chat transcript, rotate it immediately.

## Generated Data

`runs/` may contain downloaded sticker assets, Telegram import results, and local logs. These files should not be committed to public repositories.

## Copyright-Sensitive Assets

This project is intended only for education, research, and technical verification. Downloaded sticker assets and converted image files may be protected by copyright, trademark, and platform terms. Do not publicly redistribute or commit them. If you want to use paid or protected stickers, support the creators by purchasing them through official channels.
