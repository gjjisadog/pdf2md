# Architecture

BookMD MVP is a local-first monorepo for turning OCR/parser output into a mobile-readable `.bookmd` package.

## Components

- `apps/converter_desktop`: Python CLI that consumes `ocr_output/` and builds `.bookmd`.
- `apps/reader-android`: Kotlin + WebView reader skeleton.
- `packages/bookmd_core`: package and validation helpers for `.bookmd`.
- `packages/source_map_core`: OCR block normalization and source-map generation.
- `packages/translator_core`: translation interface, noop translator, and DeepSeek configuration guard.
- `packages/markdown_renderer`: static WebView renderer assets.

OCR is intentionally outside this project.
