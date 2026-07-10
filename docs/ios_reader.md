# iPadOS BookMD Reader

The iPadOS reader lives under `apps/reader-ios`.

## Current Scope

Phase-one implementation targets an iPad mini-first offline reader:

- SwiftUI app shell with an iPad-only target.
- Files import for `.bookmd`.
- BookMD validation and sandbox extraction.
- ZIP parsing reports duplicate archive paths as import errors instead of crashing while building the archive index.
- Local shelf backed by `Application Support/BookMD/books`.
- Safe sandbox directory names derived from `book_id`; replacing an existing imported book uses a backup directory so failed replacement can roll back, and failed imports clean up `.import-*` staging folders.
- TOC and search sidebar.
- The book workspace opens on the TOC/search surface when there is no saved progress; saved progress restores the previous chapter/block.
- Search is placed above the TOC so it remains reachable on iPad mini landscape.
- WKWebView-based Markdown reading using the shared renderer assets from `packages/markdown_renderer/renderer`.
- JS bridge for source-map taps and reading progress callbacks.
- WKWebView teardown removes script message handlers to avoid retaining readers after chapter/view transitions.
- Local progress persistence in `Application Support/BookMD/progress/progress.json`, including block id, vertical scroll, paged horizontal scroll, page index, and page count.
- Corrupt `progress.json` files are moved aside with a `.corrupt-*` suffix and replaced by an empty progress store so reading can continue.
- Source-map sheet showing page, bbox, type, source text, and translated text.
- Per-book reading settings for font size, line height, theme, layout, and language mode.
- Reader settings are normalized on load/save so old or invalid local preferences cannot push unsafe values into the renderer.
- Terms list from `terms.json`.
- PDFKit page review from source-map page numbers when `source/original.pdf` exists.
- Background loading for large chapter/search/source-map files to reduce main-thread stalls on iPad mini.
- Offline-first WebView shell: renderer assets are bundled locally and `http`/`https` navigation is cancelled in the WKWebView navigation delegate.
- UI automation support is gated by `BOOKMD_UI_TEST_*` launch environment variables and is used only by `BookMDReaderUITests`.

The reader does not change the `.bookmd` format and does not require network access at runtime.

Requirement-by-requirement tracking is in:

```text
docs/ios_reader_acceptance.md
```

## Project

Generate or refresh the Xcode project with:

```bash
cd apps/reader-ios
xcodegen generate
```

Open:

```text
apps/reader-ios/BookMDReader.xcodeproj
```

Targets:

- `BookMDReaderCore`: BookMD models, ZIP validation/extraction, search, source-map lookup, progress storage.
- `BookMDReader`: SwiftUI + WKWebView iPad app.
- `BookMDReaderTests`: unit tests for the real `.bookmd` sample.
- `BookMDReaderUITests`: iPad mini UI flow for real-sample import, shelf, TOC/search, terms, reader opening, source-map sheet, PDF page review, settings sheet, rotation, and relaunch progress restore.

## Real Sample

The current real sample is:

```text
tmp/real_book_full_clean_toc.bookmd
```

Observed baseline:

- Title: `DC-DC Converter Topologies Basic to Advanced`
- Chapters: 18
- Search items: 3474
- Source-map blocks: 3483
- First `Converter` search hit: `p001_b001`

## Verification Notes

The repository includes:

```bash
cd apps/reader-ios
python3 scripts/verify_ios_release.py
```

This is the main release gate. It regenerates the Xcode project, runs static verification, compiles the `BookMDReaderCore` Swift verifier with `--compile-only`, checks Xcode health, auto-selects an available iPad mini simulator, and runs `xcodebuild test` when the local Xcode installation is usable. Use `--destination` to override simulator selection.

The release gate currently runs the iPad mini simulator path on this machine with Xcode 26.5 and iOS 26.5 Simulator.

The repository also includes:

```bash
python3 apps/reader-ios/scripts/verify_ios_static.py
```

This script does not require Xcode compilation. It verifies the iOS project structure, renderer parity, `.bookmd` document type declaration, and the real sample baseline. The sample checks include chapter path safety, unique chapter paths, unique chapter order values, chapter file existence, search-to-chapter references, search-to-source-map references, positive source pages, four-value numeric bboxes, non-empty terms, and a non-empty embedded PDF.

The core-only smoke script is:

```bash
python3 apps/reader-ios/scripts/verify_ios_core.py
```

By default this script compiles a temporary snapshot of the core Swift files and runs a generated verifier against the real sample. The release gate uses `python3 scripts/verify_ios_core.py --compile-only` before `xcodebuild test`. Compiling a snapshot avoids false `swiftc` failures if workspace files are touched while verification is running.

The previous local Xcode simulator/private-framework blocker is documented in `docs/ios_xcode_repair.md`; it has been cleared on this machine by installing the iOS 26.5 simulator runtime.

## Manual Acceptance Checklist

Current automated iPad mini coverage:

1. Import `tmp/real_book_full_clean_toc.bookmd` into an isolated app sandbox.
2. Confirm the shelf shows the real book and `18 章`.
3. Enter the book workspace and confirm the TOC/search sidebar.
4. Open the terms sheet and confirm `pulse width modulation` / `脉宽调制`.
5. Search `Converter` and jump to `p001_b001`.
6. Confirm the reader WKWebView opens.
7. Confirm source-map page `1` and bbox `164, 465, 864, 969`.
8. Open `PDF 第 1 页` from source map.
9. Open the reading settings sheet and confirm font size, line height, theme, layout, and language controls.
10. Rotate iPad mini landscape and portrait and confirm the reader remains available.
11. Terminate and relaunch the app, then confirm the same book restores directly to the reader.

Manual spot-checks still recommended:

1. Import through the real Files picker.
2. Direct-tap rendered body blocks for source map.
3. Change font size, line height, theme, layout, and language mode while watching the rendered page.
4. Skim late-book chapters and searches for long-session responsiveness.
