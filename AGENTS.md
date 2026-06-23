# AGENTS.md

## Project

Chrome extension (Manifest V3) converting Feishu/Lark documents to LaTeX.
Stage: L0 skeleton — DOM-based extraction, single-file .tex export, no build step.

## Structure

```
manifest.json            # MV3 — content script matches /docx/, /docs/, /wiki/ on feishu.cn + larksuite.com
src/content/main.js      # injected into Feishu pages: DOM → block AST, sends via chrome.runtime.sendMessage
src/popup/popup.html     # popup markup
src/popup/popup.js       # popup UI + inline TeX generator + chrome.downloads API
icons/                   # extension icons (empty in L0)
```

PRD is in-repo: `飞书文档转TeX项目Chrome插件_PRD.md`

## Conventions

- **No build system.** Raw JS, no bundler, no package.json. Edit → reload extension in `chrome://extensions/`.
- **No tests or lint.** Verify by loading unpacked extension on a live Feishu doc.
- **TeX generation is inlined in popup.js**, not a shared module. `escapeTex` exists in both content/main.js and popup/popup.js — keep in sync when changing escaping rules.
- **Content script must handle 3 path types:** `/docx/*`, `/docs/*`, `/wiki/*` on both `feishu.cn` and `larksuite.com`. When adding URL patterns, update `manifest.json` matches AND the regexes in `content/main.js`.
- **Block detection is regex-based on class + data-type attributes.** Feishu DOM changes without notice. Fallback path (main.js lines 115-126) catches unstructured content.
- **Target TeX engine:** XeLaTeX/LuaLaTeX via `ctexart`. Uses `listings` (not `minted`) to avoid Python dependency.

## Gotchas

- `chrome.runtime.onMessage` requires synchronous `sendResponse`. Content script returns synchronously; if you make it async, return `true` from the listener.
- Images are NOT downloaded in L0 — only `% TODO:` comments are emitted.
- `icons/` is empty; Chrome shows a default icon. Add 16/48/128 PNGs and update manifest `default_icon` when ready.

## Manual test

1. `chrome://extensions/` → Developer mode → Load unpacked → select repo root
2. Open a Feishu doc (`/docx/`, `/docs/`, or `/wiki/` path)
3. Click extension icon → should show "已检测到飞书文档" with block count
4. Click export → downloads a `.tex` file
5. Upload `.tex` to Overleaf to verify compilation (no local TeX needed)
