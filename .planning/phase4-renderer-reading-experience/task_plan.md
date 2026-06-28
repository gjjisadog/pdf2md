# Phase 4 Renderer And Reading Experience Plan

## Goal

Make the BookMD renderer the single source of truth for mobile reading, then harden Android reader controls around layout mode, language mode, media viewing, settings, progress, and renderer regression tests.

## Status

- Planning: complete
- Implementation: complete
- Verification: complete

## Scope

In scope:
- Sync Android WebView assets with `packages/markdown_renderer/renderer`.
- Improve renderer support for custom blocks, bilingual mode, markdown tables, footnotes, references, code blocks, and anchors.
- Add reader controls for paged/scroll layout, zh/en/bilingual mode, font size, line height, and theme.
- Implement image/table viewer behavior through Android bridge.
- Persist reading progress per book/chapter/layout.
- Add automated renderer regression tests and emulator verification path.

Out of scope:
- OCR model deployment.
- Cloud sync, account system, payment, or social features.
- PDF region screenshot rendering.
- Full production pagination engine beyond a stable WebView/CSS/JS paging boundary.

## Milestones

1. Renderer asset unification.
2. Renderer grammar and visual behavior hardening.
3. Android settings and mode controls.
4. Media viewer and source-map interaction polish.
5. Progress persistence and navigation.
6. Documentation and verification.

## Implementation Notes

- Android renderer assets now sync from `packages/markdown_renderer/renderer`.
- Renderer exposes Markdown table, code fence, footnote, reference link, language mode, `currentProgress`, and `restoreProgress` hooks.
- Android adds `SettingsActivity`, `ImageViewerActivity`, `ReaderSettings` persistence, and `ReadingProgressStore.saveProgress/readProgress`.
- Emulator verification covered shelf, TOC, reader rendering, SVG image viewer, source-map dialog, search jump, and progress persistence.

## Verification Commands

```bash
python -m pytest
python -m converter build --source-pdf samples/ocr_output_sample/original.pdf --ocr-output samples/ocr_output_sample --output /tmp/bookmd-phase4/sample.bookmd --translate false
python -m converter validate /tmp/bookmd-phase4/sample.bookmd
cd apps/reader-android
ANDROID_HOME=/tmp/bookmd-android-sdk ANDROID_SDK_ROOT=/tmp/bookmd-android-sdk ./gradlew --no-daemon assembleDebug
```

## Risks

| Risk | Mitigation |
| --- | --- |
| Android inline renderer drifts from package renderer | Make Android asset copy/generated from package renderer and test for parity. |
| `searchInChapter` mutates DOM and loses source-map events | Add renderer tests for search/clear/search/source click sequence. |
| Paged mode may be fragile in WebView | Keep CSS/JS paging boundary small and fall back to scroll mode cleanly. |
| Large chapters may jank | Avoid whole-book rendering; continue chapter-level rendering and store progress by chapter. |
