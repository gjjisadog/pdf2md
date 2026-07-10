import XCTest
@testable import BookMDReaderCore

final class BookMDReaderCoreTests: XCTestCase {
    private var sampleBookURL: URL {
        if let override = ProcessInfo.processInfo.environment["BOOKMD_REAL_SAMPLE"] {
            return URL(fileURLWithPath: override)
        }

        var directory = URL(fileURLWithPath: #filePath).deletingLastPathComponent()
        while directory.path != "/" {
            let candidate = directory.appendingPathComponent("tmp/real_book_full_clean_toc.bookmd")
            if FileManager.default.fileExists(atPath: candidate.path) {
                return candidate
            }
            directory.deleteLastPathComponent()
        }
        return URL(fileURLWithPath: "/tmp/missing-real-book-full-clean-toc.bookmd")
    }

    func testValidatorAcceptsRealBookAndReportsManifest() throws {
        let validation = try BookMDArchiveValidator().validateArchive(at: sampleBookURL)

        XCTAssertTrue(validation.isValid)
        XCTAssertEqual(validation.manifest?.title, "DC-DC Converter Topologies Basic to Advanced")
        XCTAssertEqual(validation.manifest?.chapters.count, 18)
        XCTAssertEqual(validation.manifest?.chapters.first?.path, "chapters/001_chapter_1.md")
    }

    func testSearchIndexFindsConverterAndPreservesJumpMetadata() throws {
        let archive = try BookMDArchive(url: sampleBookURL)
        let index = try archive.searchIndex()
        let results = SearchService(items: index.items).search("Converter")

        XCTAssertFalse(results.isEmpty)
        XCTAssertEqual(results.first?.chapterPath, "chapters/001_chapter_1.md")
        XCTAssertEqual(results.first?.blockId, "p001_b001")
    }

    func testSearchItemIdentityIncludesChapterAndBlock() throws {
        let first = SearchItem(
            blockId: "duplicate",
            chapterId: "chapter-1",
            chapterPath: "chapters/001.md",
            chapterTitle: "Chapter 1",
            type: "paragraph",
            text: "converter"
        )
        let second = SearchItem(
            blockId: "duplicate",
            chapterId: "chapter-2",
            chapterPath: "chapters/002.md",
            chapterTitle: "Chapter 2",
            type: "paragraph",
            text: "converter"
        )

        XCTAssertNotEqual(first.id, second.id)
    }

    func testSourceMapIndexFindsPageBBoxAndSourceText() throws {
        let archive = try BookMDArchive(url: sampleBookURL)
        let sourceMap = try archive.sourceMap()
        let block = SourceMapIndex(blocks: sourceMap.blocks).block(for: "p001_b001")

        XCTAssertEqual(block?.sourcePage, 1)
        XCTAssertEqual(block?.bbox, [164, 465, 864, 969])
        XCTAssertEqual(block?.sourceText, "DC-DC  Converter  Topologies  Basic to Advanced ")
    }

    func testSourceMapIndexKeepsFirstDuplicateBlockId() throws {
        let first = SourceMapBlock(
            blockId: "duplicate",
            chapterId: "chapter-1",
            markdownPath: "chapters/001.md",
            sourcePage: 1,
            bbox: [1, 2, 3, 4],
            sourceText: "first",
            translatedText: nil,
            type: "paragraph"
        )
        let second = SourceMapBlock(
            blockId: "duplicate",
            chapterId: "chapter-1",
            markdownPath: "chapters/001.md",
            sourcePage: 2,
            bbox: [5, 6, 7, 8],
            sourceText: "second",
            translatedText: nil,
            type: "paragraph"
        )

        let block = SourceMapIndex(blocks: [first, second]).block(for: "duplicate")

        XCTAssertEqual(block?.sourceText, "first")
        XCTAssertEqual(block?.sourcePage, 1)
    }

    func testProgressStorePersistsBookAndChapterProgress() throws {
        let directory = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString, isDirectory: true)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: directory) }

        let store = try ReadingProgressStore(storageURL: directory.appendingPathComponent("progress.json"))
        let progress = ReadingProgress(
            bookId: "book-1",
            chapterPath: "chapters/018_chapter_18.md",
            blockId: "p461_b002",
            scrollY: 2048,
            scrollX: 4096,
            pageIndex: 12,
            pageCount: 24,
            updatedAt: Date(timeIntervalSince1970: 1_800_000_000)
        )

        try store.save(progress)

        let reloaded = try ReadingProgressStore(storageURL: directory.appendingPathComponent("progress.json"))
        XCTAssertEqual(reloaded.progress(forBookId: "book-1")?.chapterPath, "chapters/018_chapter_18.md")
        XCTAssertEqual(reloaded.progress(forBookId: "book-1")?.blockId, "p461_b002")
        XCTAssertEqual(reloaded.progress(forBookId: "book-1", chapterPath: "chapters/018_chapter_18.md")?.scrollY, 2048)
        XCTAssertEqual(reloaded.progress(forBookId: "book-1", chapterPath: "chapters/018_chapter_18.md")?.scrollX, 4096)
        XCTAssertEqual(reloaded.progress(forBookId: "book-1", chapterPath: "chapters/018_chapter_18.md")?.pageIndex, 12)
        XCTAssertEqual(reloaded.progress(forBookId: "book-1", chapterPath: "chapters/018_chapter_18.md")?.pageCount, 24)
    }
}
