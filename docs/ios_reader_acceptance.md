# iPadOS BookMD Reader Acceptance Matrix

This matrix tracks the original phase-one and phase-two requirements for the iPad mini reader. The local iOS runtime gate now builds the app and runs both core XCTest coverage and a real-sample iPad mini UI flow.

Status values:

- `static-pass`: Source/project/sample evidence is present and covered by `verify_ios_static.py`.
- `runtime-pass`: Covered by `apps/reader-ios/scripts/verify_ios_release.py` on an iPad mini simulator.
- `manual-recommended`: Still worth spot-checking by hand on a physical iPad mini before personal daily use.

## Phase One MVP

| ID | Requirement | Source Evidence | Verification |
| --- | --- | --- | --- |
| P1-01 | Create iPadOS/iOS SwiftUI app project | `apps/reader-ios/BookMDReader.xcodeproj`, `BookMDReaderApp.swift`, `project.yml` | static-pass, runtime-pass |
| P1-02 | Import `.bookmd` from Files | `ShelfView.fileImporter`, `UTType.bookMD`, `Info.plist`; UI test imports the same archive through `BookLibraryStore.importBook` into a clean sandbox | static-pass, runtime-pass, manual-recommended for Files picker |
| P1-03 | Unpack `.bookmd` into app sandbox | `BookLibraryStore.importBook`, `safeBookDirectoryName`, backup-based replacement, `BookMDArchive.extract`; UI test verifies the imported real book appears from a temporary support root | static-pass, runtime-pass |
| P1-04 | Read `book.json` and show shelf | `BookLibraryStore.refresh`, `LocalBook`, `ShelfView`; UI test sees `DC-DC Converter Topologies Basic to Advanced` and `18 章` | static-pass, runtime-pass |
| P1-05 | Tap book to enter TOC | `ShelfView` `NavigationLink`, `BookWorkspaceView` TOC section; UI test opens the real book and waits for `toc.chapter.chapters/001_chapter_1.md` | static-pass, runtime-pass |
| P1-06 | Tap chapter / search result to open reader | `BookWorkspaceView.selectedChapter`, `ReaderView`; UI test opens the reader via the first `Converter` search result | static-pass, runtime-pass |
| P1-07 | Render chapter Markdown in WKWebView | `BookMDWebView`, shared renderer resources; UI test waits for `reader.webview` after the real-sample jump and verifies the rendered `source block p001_b001` accessibility node exists | static-pass, runtime-pass |
| P1-08 | Save and restore reading progress | `ReadingProgressStore`, `BookMDWebView.progressChanged`, `onReadingProgressChangedPayload`, `restoreProgress`; core tests persist book/chapter progress with scroll/page fields; UI test terminates and relaunches the app, then verifies the book reopens directly to `reader.webview` | static-pass, runtime-pass |
| P1-09 | Search `search_index.json` and jump to block | `BookRuntime.search`, `SearchService`, `targetBlockId`, `jumpToBlock`; UI test searches `Converter`, taps `search.result.p001_b001`, and opens the reader | static-pass, runtime-pass |
| P1-10 | Show source map info for a rendered block | `BookMDWebView.sourceMapRequested`, native tap fallback, `SourceMapSheet`, `SourceMapIndex`; UI test first proves the target block is rendered in WKWebView, then uses the UI-test source-map control to invoke the same `showSourceMap(targetBlockId)` path and verifies page/bbox | static-pass, runtime-pass, manual-recommended for direct finger tap on WKWebView text |
| P1-11 | Adapt iPad mini portrait/landscape | `BookWorkspaceView.NavigationSplitView(columnVisibility: .all)`, search-first sidebar, `ReaderView`; UI test rotates landscape and portrait | static-pass, runtime-pass |
| P1-12 | Show import/unpack/read errors | `BookLibraryStore.lastError`, `ShelfView.alert`, `ReaderView.alert`, `BookWorkspaceView.alert`, duplicate zip paths are reported as `BookMDError.duplicateArchivePath` | static-pass, runtime-pass for duplicate-path core behavior |
| P1-13 | Handle large real book sample | `tmp/real_book_full_clean_toc.bookmd` baseline: 18 chapters, 3474 search items, 3483 source-map blocks; `BookRuntime` loads chapter/search/source-map JSON with `Task.detached`; UI test imports/searches/jumps in the real sample | static-pass, runtime-pass |

## Phase Two Experience

| ID | Requirement | Source Evidence | Verification |
| --- | --- | --- | --- |
| P2-01 | Kindle / Apple Books-like clean reading surface | `ReaderView`, renderer CSS, minimal toolbar | static-pass, manual-recommended |
| P2-02 | Font size, line height, theme switching | `ReaderSettingsSheet`, `ReaderSettingsStore`, `ReaderDisplaySettings.normalized`; UI test opens the settings sheet and verifies the font size, line height, theme, layout, and language controls | static-pass, runtime-pass |
| P2-03 | Landscape left TOC/search and right reader | `BookWorkspaceView.NavigationSplitView`, search section above TOC | static-pass, runtime-pass |
| P2-04 | Original PDF page review | `PDFPageView`, `PDFPageSheet`, `BookRuntime.originalPDFURL`; UI test opens `PDF 第 1 页` from source map | static-pass, runtime-pass |
| P2-05 | Terms glossary | `TermsView`, `BookRuntime.terms`; UI test opens the terms sheet and verifies `pulse width modulation` / `脉宽调制` from the real sample | static-pass, runtime-pass |
| P2-06 | Chinese/English/bilingual display mode | `ReaderSettingsSheet.languageMode`, `BookMDWebView` config bridge; UI test verifies the language-mode control is present in the settings sheet | static-pass, runtime-pass |
| P2-07 | Local persistent reading position | `ReadingProgressStore` JSON storage with block id, `scroll_y`, `scroll_x`, `page_index`, and `page_count`; corrupt progress files are moved aside and the store is rebuilt empty; UI test covers relaunch restore from the same sandbox | static-pass, runtime-pass |
| P2-08 | Offline runtime | No network API, local sandbox files, embedded renderer resources, `BookMDWebView` cancels `http`/`https` navigation | static-pass |
| P2-09 | Apple Pencil annotation | Future optional item; not required for current MVP completion | not-in-scope |

## Performance Notes

Large-book operations are structured to avoid synchronous main-thread JSON decoding:

- `BookRuntime.markdown(for:)` reads chapter files in a detached task.
- `BookRuntime.search(_:)` lazily loads `search_index.json` in a detached task, caches the decoded items, and avoids loading on blank queries.
- `BookRuntime.sourceBlock(id:)` lazily loads `source_map.json` in a detached task and caches a block-id index.
- `BookWorkspaceView` shows search progress while the first search index load is running.
- `BookMDWebView` consumes the shared renderer's full progress payload so paged mode can restore by block id, horizontal scroll, and page index.
- `verify_ios_static.py` validates unique chapter paths/order values and every real-sample search result against chapter markdown and `source_map.json`, plus source page and bbox shape, so large-book wiring is checked without Xcode.
- `verify_ios_release.py` runs `verify_ios_core.py --compile-only` before the Xcode runtime gate, giving a Swift compile-level check for `BookMDReaderCore` even while local Swift executables cannot be run reliably.

The runtime gate now exercises the real sample on an iPad mini simulator through `BookMDReaderUITests`, including terms, search-to-reader navigation, rendered block exposure inside WKWebView, source-map sheet data, original PDF page review, settings controls, explicit sheet close actions, orientation changes, and relaunch-based reading-progress restore.

## Runtime Gate

Run the iPad mini gate with:

```bash
cd apps/reader-ios
xcodegen generate
BOOKMD_REAL_SAMPLE=/Users/wangxuwen/Documents/pdf2md/tmp/real_book_full_clean_toc.bookmd \
  xcodebuild test -project BookMDReader.xcodeproj -scheme BookMDReader -destination 'platform=iOS Simulator,name=iPad mini (A17 Pro)'
```

Equivalent release-gate command:

```bash
cd apps/reader-ios
python3 scripts/verify_ios_release.py
```

The release gate auto-selects an available iPad mini simulator with `xcrun simctl`. If the local simulator name differs, either install an iPad mini runtime or pass an explicit `--destination`.

The UI test uses `BOOKMD_UI_TEST_*` launch environment keys to import the real sample into an isolated temporary support root. Normal app launches still use Files import and the app's `Application Support` sandbox.

Manual spot-checks are still recommended before long personal reading sessions: import through the Files picker, direct-tap rendered text for source map on a physical iPad mini, adjust settings while watching the rendered typography/theme, and skim late-book chapters for responsiveness.
