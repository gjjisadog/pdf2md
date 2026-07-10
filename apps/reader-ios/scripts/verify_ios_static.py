#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import plistlib
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
SAMPLE = REPO / "tmp" / "real_book_full_clean_toc.bookmd"
PROJECT = ROOT / "BookMDReader.xcodeproj" / "project.pbxproj"
SCHEME = ROOT / "BookMDReader.xcodeproj" / "xcshareddata" / "xcschemes" / "BookMDReader.xcscheme"
INFO_PLIST = ROOT / "BookMDReader" / "Info.plist"
RENDERER_SOURCE = REPO / "packages" / "markdown_renderer" / "renderer"
RENDERER_IOS = ROOT / "BookMDReader" / "Resources" / "renderer"
ACCEPTANCE = REPO / "docs" / "ios_reader_acceptance.md"
IOS_DOC = REPO / "docs" / "ios_reader.md"
XCODE_REPAIR_DOC = REPO / "docs" / "ios_xcode_repair.md"


REQUIRED_FILES = [
    "BookMDReader/BookMDReaderApp.swift",
    "BookMDReader/Models/BookMDDocumentType.swift",
    "BookMDReader/Models/LocalBook.swift",
    "BookMDReader/Models/ReaderDisplaySettings.swift",
    "BookMDReader/Rendering/BookMDWebView.swift",
    "BookMDReader/Services/BookLibraryStore.swift",
    "BookMDReader/Services/BookRuntime.swift",
    "BookMDReader/Services/ReaderSettingsStore.swift",
    "BookMDReader/Views/BookWorkspaceView.swift",
    "BookMDReader/Views/PDFPageView.swift",
    "BookMDReader/Views/ReaderSettingsSheet.swift",
    "BookMDReader/Views/ReaderView.swift",
    "BookMDReader/Views/ShelfView.swift",
    "BookMDReader/Views/SourceMapSheet.swift",
    "BookMDReader/Views/TermsView.swift",
    "Sources/BookMDReaderCore/BookMDArchive.swift",
    "Sources/BookMDReaderCore/BookMDZipInflate.c",
    "Sources/BookMDReaderCore/BookMDZipInflate.h",
    "Sources/BookMDReaderCore/BookModels.swift",
    "Sources/BookMDReaderCore/ReadingProgressStore.swift",
    "Sources/BookMDReaderCore/SearchService.swift",
    "Sources/BookMDReaderCore/SourceMapIndex.swift",
    "Tests/BookMDReaderCoreTests/BookMDReaderCoreTests.swift",
    "Tests/BookMDReaderUITests/BookMDReaderUITests.swift",
    "scripts/verify_ios_core.py",
    "scripts/verify_ios_release.py",
]


def fail(message: str) -> None:
    raise AssertionError(message)


def is_safe_archive_path(path: str) -> bool:
    if not path or path.startswith("/"):
        return False
    return ".." not in path.split("/")


def verify_files() -> None:
    missing = [path for path in REQUIRED_FILES if not (ROOT / path).exists()]
    if missing:
        fail(f"missing iOS reader files: {missing}")


def verify_project() -> None:
    text = PROJECT.read_text(encoding="utf-8")
    for token in [
        "BookMDReaderCore",
        "BookMDReaderTests",
        "BookMDZipInflate.c",
        "BookMDWebView.swift",
        "ReaderSettingsSheet.swift",
        "PDFPageView.swift",
        "TermsView.swift",
        "bookmd-renderer.js",
        "TARGETED_DEVICE_FAMILY = 2",
        "OTHER_LDFLAGS = \"$(inherited) -lz\"",
    ]:
        if token not in text:
            fail(f"project is missing token: {token}")

    with INFO_PLIST.open("rb") as handle:
        plist = plistlib.load(handle)
    declarations = plist.get("UTImportedTypeDeclarations", [])
    if not any(item.get("UTTypeIdentifier") == "com.bookmd.bookmd" for item in declarations):
        fail("Info.plist does not declare com.bookmd.bookmd")
    scheme = SCHEME.read_text(encoding="utf-8")
    for token in ["BookMDReader", "BookMDReaderTests", "TestAction", "BuildAction"]:
        if token not in scheme:
            fail(f"BookMDReader scheme is missing token: {token}")


def verify_test_fixture_lookup() -> None:
    test_text = (ROOT / "Tests" / "BookMDReaderCoreTests" / "BookMDReaderCoreTests.swift").read_text(
        encoding="utf-8"
    )
    for token in [
        "BOOKMD_REAL_SAMPLE",
        'while directory.path != "/"',
        "tmp/real_book_full_clean_toc.bookmd",
        "testSourceMapIndexKeepsFirstDuplicateBlockId",
        "XCTAssertEqual(block?.sourceText, \"first\")",
        "testSearchItemIdentityIncludesChapterAndBlock",
        "XCTAssertNotEqual(first.id, second.id)",
    ]:
        if token not in test_text:
            fail(f"iOS core tests are missing token: {token}")


def verify_feature_hooks() -> None:
    checks = {
        "BookMDReader/Views/ShelfView.swift": [
            ".fileImporter",
            "allowedContentTypes: [.bookMD, .zip]",
            "library.importBook",
            "NavigationStack",
        ],
        "BookMDReader/Views/BookWorkspaceView.swift": [
            "NavigationSplitView",
            "NavigationSplitViewVisibility",
            "navigationSplitViewStyle(.balanced)",
            "ForEach(runtime.manifest.chapters.sorted { $0.order < $1.order }, id: \\.path)",
            "try await runtime.search",
            "isSearching",
            "TermsView",
            "targetBlockId = item.blockId",
            "restoreChapter",
            "Section(\"搜索\")",
            "Section(\"资料\")",
            "Section(\"目录\")",
            "isTermsPresented",
            "terms.done",
        ],
        "BookMDReader/Views/ReaderView.swift": [
            "try await runtime.markdown",
            "try await runtime.sourceBlock",
            "ReaderSettingsSheet",
            "PDFPageSheet",
            "SourceMapSheet",
            "BOOKMD_UI_TEST_MODE",
            "reader.test.sourceMap",
            "reader.settings.button",
            "progress.scrollX",
            "progress.pageIndex",
            "progress.pageCount",
            "saveProgress",
        ],
        "BookMDReader/Views/TermsView.swift": [
            "ForEach(Array(terms.enumerated()), id: \\.offset)",
            "TermRow(term: term)",
            "terms.list",
            "terms.row.",
        ],
        "BookMDReader/Views/ReaderSettingsSheet.swift": [
            "reader.settings.form",
            "reader.settings.fontSize",
            "reader.settings.lineHeight",
            "reader.settings.theme",
            "reader.settings.layout",
            "reader.settings.language",
            "reader.settings.done",
        ],
        "BookMDReader/Views/PDFPageView.swift": [
            "pdf.done",
        ],
        "BookMDReader/Models/ReaderDisplaySettings.swift": [
            "func normalized() -> ReaderDisplaySettings",
            "min(max(fontSize, 14), 28)",
            "min(max(lineHeight, 1.3), 2.2)",
            "Set([\"light\", \"dark\"])",
            "Set([\"scroll\", \"paged\"])",
            "Set([\"zh\", \"en\", \"bilingual\"])",
        ],
        "BookMDReader/Services/BookLibraryStore.swift": [
            "safeBookDirectoryName",
            "CharacterSet.alphanumerics",
            "appendingPathComponent(safeBookDirectoryName",
            "destinationBackup",
            "defer { try? FileManager.default.removeItem(at: temporary) }",
        ],
        "BookMDReader/Rendering/BookMDWebView.swift": [
            "window.AndroidBookMD",
            "sourceMapRequested",
            "progressChanged",
            "decidePolicyFor navigationAction",
            'scheme == "http" || scheme == "https"',
            "decisionHandler(.cancel)",
            "dismantleUIView",
            "removeScriptMessageHandler(forName: \"sourceMapRequested\")",
            "removeScriptMessageHandler(forName: \"progressChanged\")",
            "webView.navigationDelegate = nil",
            "onReadingProgressChangedPayload",
            "lastAppliedTargetBlockId",
            "applyPendingPosition",
            "NSNumber",
            '"scroll_x": progress.scrollX',
            '"page_index": progress.pageIndex',
            '"page_count": progress.pageCount',
            "window.BookMDReader.jumpToBlock",
            "window.BookMDReader.restoreProgress",
            'Bundle.main.url(forResource: name, withExtension: ext)',
            "UITapGestureRecognizer",
            "webView.scrollView.addGestureRecognizer",
            "UIGestureRecognizerDelegate",
            "shouldRecognizeSimultaneouslyWith",
            "handleTap",
            "window.BookMDReader.blockIdAtPoint",
            '"native_source_links": true',
            'scheme == "bookmd-source"',
            "parent.onSourceMapRequested(blockId)",
        ],
        "Sources/BookMDReaderCore/BookModels.swift": [
            'public var id: String { "\\(chapterPath)::\\(blockId)" }',
            "public let scrollX: Int",
            "public let pageIndex: Int",
            "public let pageCount: Int",
            "decodeIfPresent(Int.self, forKey: .scrollX)",
            "decodeIfPresent(Int.self, forKey: .pageIndex)",
            "decodeIfPresent(Int.self, forKey: .pageCount)",
        ],
        "Sources/BookMDReaderCore/ReadingProgressStore.swift": [
            "recoverCorruptStorage",
            ".corrupt-",
            "try? FileManager.default.moveItem(at: storageURL, to: backupURL)",
            "self.storage = Storage()",
        ],
        "Sources/BookMDReaderCore/BookMDArchive.swift": [
            "case duplicateArchivePath(String)",
            "BookMD 包含重复路径",
            "if entriesByPath[entry.path] != nil",
            "throw BookMDError.duplicateArchivePath(entry.path)",
        ],
        "Sources/BookMDReaderCore/SourceMapIndex.swift": [
            "var index: [String: SourceMapBlock] = [:]",
            "if index[block.blockId] == nil",
            "self.blocksById = index",
        ],
        "BookMDReader/Services/BookRuntime.swift": [
            "@MainActor",
            "Task.detached",
            "loadSearchItems",
            "loadSourceMapIndex",
            "search_index.json",
            "source_map.json",
            "terms.json",
            "source/original.pdf",
        ],
        "scripts/verify_ios_core.py": [
            "argparse",
            "import shutil",
            "snapshot_swift_sources",
            "source_snapshot",
            "shutil.copy2",
            "--compile-only",
            "iOS core compile verification passed",
            "iOS core runtime verifier timed out",
            "Use --compile-only",
            "BookMDZipInflate.c",
            "-import-objc-header",
            "BookMDZipInflate.h",
            "scrollX: 4096",
            "pageIndex: 12",
            "pageCount: 24",
            "-lz",
        ],
        "scripts/verify_ios_release.py": [
            "verify_ios_static.py",
            "verify_ios_core.py",
            "--compile-only",
            "xcodegen",
            "xcodebuild",
            "xcrun",
            "simctl",
            "resolve_destination",
            "iPad mini",
            "BOOKMD_REAL_SAMPLE",
            "--allow-xcode-blocked",
        ],
        "Tests/BookMDReaderUITests/BookMDReaderUITests.swift": [
            "BOOKMD_UI_TEST_IMPORT_PATH",
            "BOOKMD_UI_TEST_SUPPORT_ROOT",
            "DC-DC Converter Topologies Basic to Advanced",
            "18 章",
            "book.search.field",
            "book.terms.link",
            "terms.list",
            "pulse width modulation",
            "terms.done",
            "search.result.p001_b001",
            "reader.webview",
            "reader.test.sourceMap",
            "sourceMap.page.1",
            "sourceMap.bbox.164, 465, 864, 969",
            "PDF 第 1 页",
            "pdf.done",
            "reader.settings.button",
            "reader.settings.form",
            "reader.settings.done",
            "XCUIDevice.shared.orientation",
        ],
    }
    for relative_path, tokens in checks.items():
        text = (ROOT / relative_path).read_text(encoding="utf-8")
        for token in tokens:
            if token not in text:
                fail(f"{relative_path} is missing feature token: {token}")
    shelf = (ROOT / "BookMDReader" / "Views" / "ShelfView.swift").read_text(encoding="utf-8")
    if "NavigationSplitView" in shelf:
        fail("ShelfView should stay a simple shelf; split view belongs inside BookWorkspaceView")


def verify_acceptance_matrix() -> None:
    text = ACCEPTANCE.read_text(encoding="utf-8")
    required_ids = [f"P1-{index:02d}" for index in range(1, 14)]
    required_ids.extend(f"P2-{index:02d}" for index in range(1, 10))
    for requirement_id in required_ids:
        if requirement_id not in text:
            fail(f"acceptance matrix is missing {requirement_id}")
    for token in ["static-pass", "runtime-pass", "manual-recommended", "Runtime Gate"]:
        if token not in text:
            fail(f"acceptance matrix is missing token: {token}")
    doc_text = IOS_DOC.read_text(encoding="utf-8")
    for token in ["verify_ios_release.py", "BookMDReaderUITests", "iPad mini simulator"]:
        if token not in doc_text:
            fail(f"iOS reader docs are missing release-gate token: {token}")
    if not XCODE_REPAIR_DOC.exists():
        fail("missing Xcode repair docs: docs/ios_xcode_repair.md")
    repair_text = XCODE_REPAIR_DOC.read_text(encoding="utf-8")
    for token in [
        "IDESimulatorFoundation",
        "DVTDownloads.framework",
        "xcodebuild -runFirstLaunch",
        "verify_ios_release.py",
        "Manual Runtime Acceptance",
    ]:
        if token not in repair_text:
            fail(f"Xcode repair docs are missing token: {token}")


def verify_renderer_sync() -> None:
    for name in ["bookmd-renderer.html", "bookmd-renderer.css", "bookmd-renderer.js"]:
        source = (RENDERER_SOURCE / name).read_bytes()
        ios = (RENDERER_IOS / name).read_bytes()
        if source != ios:
            fail(f"iOS renderer asset drifted: {name}")


def verify_sample() -> None:
    if not SAMPLE.exists():
        fail(f"missing real sample: {SAMPLE}")
    with zipfile.ZipFile(SAMPLE) as zf:
        names = set(zf.namelist())
        required = {
            "book.json",
            "source_map.json",
            "terms.json",
            "translation.json",
            "reading_config.json",
            "search_index.json",
            "source/original.pdf",
        }
        missing = sorted(required - names)
        if missing:
            fail(f"sample missing required files: {missing}")
        unsafe = sorted(name for name in names if not is_safe_archive_path(name))
        if unsafe:
            fail(f"sample contains unsafe archive paths: {unsafe[:5]}")
        if zf.getinfo("source/original.pdf").file_size <= 0:
            fail("sample source/original.pdf is empty")

        book = json.loads(zf.read("book.json"))
        search = json.loads(zf.read("search_index.json"))["items"]
        source_map = json.loads(zf.read("source_map.json"))["blocks"]
        terms = json.loads(zf.read("terms.json"))["terms"]

        if len(book["chapters"]) != 18:
            fail(f"expected 18 chapters, got {len(book['chapters'])}")
        chapter_paths = [chapter["path"] for chapter in book["chapters"]]
        if len(set(chapter_paths)) != len(chapter_paths):
            fail("book.json contains duplicate chapter paths")
        chapter_orders = [chapter.get("order") for chapter in book["chapters"]]
        if len(set(chapter_orders)) != len(chapter_orders):
            fail("book.json contains duplicate chapter order values")
        chapter_path_set = set(chapter_paths)
        for chapter in book["chapters"]:
            path = chapter["path"]
            if not is_safe_archive_path(path):
                fail(f"book.json chapter has unsafe path: {path}")
            if not path.startswith("chapters/") or not path.endswith(".md"):
                fail(f"book.json chapter path is not chapters/*.md: {path}")
            if path not in names:
                fail(f"book.json chapter missing from archive: {path}")

        chapter_texts = {path: zf.read(path).decode("utf-8") for path in chapter_paths}
        source_blocks_by_id = {block["block_id"]: block for block in source_map}
        for index, item in enumerate(search):
            chapter_path = item.get("chapter_path")
            block_id = item.get("block_id")
            if chapter_path not in chapter_path_set:
                fail(f"search item {index} references unknown chapter: {chapter_path}")
            if not block_id:
                fail(f"search item {index} is missing block_id")
            if block_id not in chapter_texts[chapter_path]:
                fail(f"search item {index} block is not present in chapter markdown: {block_id}")
            if block_id not in source_blocks_by_id:
                fail(f"search item {index} block is missing from source_map.json: {block_id}")

        for index, block in enumerate(source_map):
            block_id = block.get("block_id")
            markdown_path = block.get("markdown_path")
            bbox = block.get("bbox")
            source_page = block.get("source_page")
            if not block_id:
                fail(f"source map block {index} is missing block_id")
            if markdown_path and markdown_path not in chapter_path_set:
                fail(f"source map block {block_id} references unknown chapter: {markdown_path}")
            if not isinstance(source_page, int) or source_page <= 0:
                fail(f"source map block {block_id} has invalid source_page: {source_page}")
            if (
                not isinstance(bbox, list)
                or len(bbox) != 4
                or not all(isinstance(value, (int, float)) and math.isfinite(value) for value in bbox)
            ):
                fail(f"source map block {block_id} has invalid bbox: {bbox}")

        first_hit = next((item for item in search if "converter" in item["text"].lower()), None)
        if not first_hit:
            fail("search index does not find converter")
        chapter_text = zf.read(first_hit["chapter_path"]).decode("utf-8")
        if first_hit["block_id"] not in chapter_text:
            fail("search hit block id is not present in chapter markdown")
        block = next((item for item in source_map if item["block_id"] == first_hit["block_id"]), None)
        if not block:
            fail("source map does not contain first search hit")
        if block["source_page"] != 1:
            fail(f"expected first hit source page 1, got {block['source_page']}")
        if not terms:
            fail("terms.json should contain at least one term")

        print(
            "iOS static verification passed: "
            f"chapters={len(book['chapters'])} "
            f"search_items={len(search)} "
            f"source_blocks={len(source_map)} "
            f"first_hit={first_hit['block_id']}"
        )


def main() -> int:
    verify_files()
    verify_project()
    verify_test_fixture_lookup()
    verify_feature_hooks()
    verify_acceptance_matrix()
    verify_renderer_sync()
    verify_sample()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
