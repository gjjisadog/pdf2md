# Phase 4 Scope

Phase 4 turns the current buildable Android reading MVP into a more reliable professional mobile reading experience by hardening the Markdown renderer and wiring Android reader controls around it.

## Positioning

The original project prompt names stage four as `markdown-renderer`. In this repository, phase three already delivered a buildable Android MVP, so phase four should combine the original renderer stage with the reader experience gaps discovered during emulator verification.

## Goals

- Make `packages/markdown_renderer/renderer` the single source of truth for Android WebView rendering.
- Support professional BookMD blocks more completely:
  - `formula`
  - `figure`
  - `table`
  - `bilingual`
  - footnotes
  - code blocks
  - reference links and anchors
  - Markdown tables
- Improve mobile reading behavior:
  - paged and scroll modes
  - zh/en/bilingual display modes
  - font size and line-height settings
  - light and dark theme
  - stable source-map click targets
  - image/table full-screen viewing path
- Persist reading progress at chapter/block/scroll position level.
- Add automated tests that protect renderer behavior and Android asset parity.

## Non-Goals

- No OCR/Paddle deployment.
- No cloud upload, account system, or sync.
- No PDF bbox screenshot rendering yet.
- No full native pagination engine; WebView CSS/JS pagination is enough if it is stable and testable.
- No commercial-grade UI redesign.

## Implementation Plan

1. Renderer Asset Unification
   - Replace the Android-only inline renderer with the packaged renderer assets.
   - Add a script or test that fails if Android renderer assets drift from `packages/markdown_renderer/renderer`.

2. Renderer Grammar Hardening
   - Expand renderer tests for custom BookMD blocks, Markdown tables, code fences, footnotes, references, anchors, and bilingual blocks.
   - Preserve `data-block-id` on every traceable block.
   - Ensure search highlighting can be cleared without breaking media/source-map click behavior.

3. Reading Layout And Language Modes
   - Apply `reading_config.json` in Android instead of only hardcoded defaults.
   - Add settings state for `layout`, `theme`, `font_size`, `line_height`, and `default_mode`.
   - Implement zh/en/bilingual visibility in renderer through CSS data attributes.

4. Media Interaction
   - Route image/table taps through the Android bridge.
   - Add a simple full-screen viewer Activity for image/table assets.
   - Keep formula taps source-map aware.

5. Progress And Navigation
   - Persist chapter path plus current block or scroll/page offset.
   - Restore progress when reopening a book.
   - Add previous/next chapter controls or equivalent navigation boundary.

6. Verification And Docs
   - Run Python tests and sample `.bookmd` build/validate.
   - Build Android debug APK.
   - Verify on emulator:
     - shelf -> TOC -> reader
     - paged/scroll mode
     - theme and font settings
     - image/table viewer
     - search jump
     - source-map dialog
   - Update README, `docs/android_reader_usage.md`, and troubleshooting notes.

## Acceptance Criteria

- `python -m pytest` passes.
- Sample `.bookmd` builds and validates.
- `apps/reader-android ./gradlew assembleDebug` succeeds.
- Android WebView uses renderer assets derived from `packages/markdown_renderer/renderer`.
- Emulator shows formulas, figures, tables, bilingual blocks, search highlights, and source-map dialogs without broken assets.
- Settings changes are visible in reader and persist across reopening.
- Reading progress restores to the last chapter/block or scroll position.

## Completed In Phase 4

- Added `scripts/sync_android_renderer_assets.py`.
- Made Android renderer assets match `packages/markdown_renderer/renderer`.
- Added renderer support boundaries for:
  - Markdown tables
  - code fences
  - footnotes
  - reference links
  - anchors
  - language mode data attributes
  - progress save/restore APIs
- Added Android `SettingsActivity`.
- Added Android `ImageViewerActivity`.
- Wired media taps through `BookMdWebBridge`.
- Loaded `reading_config.json` defaults in `ReaderActivity`.
- Persisted chapter/block/scroll progress through `ReadingProgressStore`.

## Verification

```bash
python -m pytest
rm -rf /tmp/bookmd-phase4 && mkdir -p /tmp/bookmd-phase4
python -m converter build --source-pdf samples/ocr_output_sample/original.pdf --ocr-output samples/ocr_output_sample --output /tmp/bookmd-phase4/sample.bookmd --translate false
python -m converter validate /tmp/bookmd-phase4/sample.bookmd
cd apps/reader-android
ANDROID_HOME=/tmp/bookmd-android-sdk ANDROID_SDK_ROOT=/tmp/bookmd-android-sdk ./gradlew --no-daemon assembleDebug
```

This phase was also checked on an Android 33 arm64 emulator by installing the debug APK, unpacking a sample `.bookmd` into app-private storage, and exercising:

- shelf -> TOC -> reader
- SettingsActivity
- renderer asset loading from app-private files
- SVG figure full-screen viewing through ImageViewerActivity
- source-map dialog
- search result navigation
- progress persistence in `bookmd_progress.xml`
