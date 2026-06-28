# Phase 4 Findings

## Current State

- Phase 3 completed Android buildable reading MVP on branch `codex/bookmd-mvp`.
- Android can import/open `.bookmd`, show shelf/TOC, render chapter Markdown in WebView, search, jump to a block, and show source-map dialog.
- Emulator verification confirmed image and table assets render from app-private imported `.bookmd` storage.
- `packages/markdown_renderer/renderer` contains the richer renderer split into HTML/CSS/JS.
- `apps/reader-android/app/src/main/assets/bookmd-renderer.html` is still an inline Android-specific renderer and can drift from the package renderer.

## Product Direction For Phase 4

The original prompt lists markdown-renderer as stage four. Because this project already moved Android MVP forward in phase three, phase four should now unify and harden the renderer and reader experience rather than build another skeleton.

## Key Decisions

- Treat `packages/markdown_renderer/renderer` as source of truth.
- Keep Android WebView as the rendering host.
- Prefer local tests around renderer parsing and asset parity before adding UI polish.
- Keep PDF region screenshot tracing out of phase four.

## Implementation Findings

- Static renderer parity tests are enough to catch Android/package asset drift.
- Android Gradle build succeeds with the split renderer assets loaded from `android_asset`.
- `ReaderActivity` can merge app settings with `reading_config.json` defaults without changing `.bookmd` format.
