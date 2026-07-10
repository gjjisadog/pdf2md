import Foundation
import BookMDReaderCore

@MainActor
final class BookRuntime {
    let book: LocalBook
    let manifest: BookManifest
    let readingConfig: ReadingConfig

    private var searchItems: [SearchItem]?
    private var sourceMapIndex: SourceMapIndex?

    init(book: LocalBook) throws {
        self.book = book
        self.manifest = book.manifest
        let configURL = book.directoryURL.appendingPathComponent("reading_config.json")
        if let data = try? Data(contentsOf: configURL),
           let config = try? JSONDecoder().decode(ReadingConfig.self, from: data) {
            self.readingConfig = config
        } else {
            self.readingConfig = ReadingConfig(
                defaultMode: "zh",
                layout: "paged",
                fontSize: 18,
                lineHeight: 1.75,
                theme: "light",
                paragraphIndent: true
            )
        }
    }

    func markdown(for chapter: BookChapter) async throws -> String {
        let url = book.directoryURL.appendingPathComponent(chapter.path)
        let assetBase = book.directoryURL.appendingPathComponent("assets", isDirectory: true).absoluteString
        let markdown = try await Task.detached(priority: .userInitiated) {
            try String(contentsOf: url, encoding: .utf8)
        }.value
        return markdown.replacingOccurrences(of: "../assets/", with: assetBase)
    }

    func search(_ query: String) async throws -> [SearchItem] {
        let items = try await loadSearchItems()
        return SearchService(items: items).search(query)
    }

    func sourceBlock(id blockId: String) async throws -> SourceMapBlock? {
        let index = try await loadSourceMapIndex()
        return index.block(for: blockId)
    }

    func terms() async throws -> [BookTerm] {
        let url = book.directoryURL.appendingPathComponent("terms.json")
        guard FileManager.default.fileExists(atPath: url.path) else { return [] }
        return try await Task.detached(priority: .utility) {
            let data = try Data(contentsOf: url)
            return try JSONDecoder().decode(TermsFile.self, from: data).terms
        }.value
    }

    private func loadSearchItems() async throws -> [SearchItem] {
        if searchItems == nil {
            let url = book.directoryURL.appendingPathComponent("search_index.json")
            searchItems = try await Task.detached(priority: .userInitiated) {
                let data = try Data(contentsOf: url)
                return try JSONDecoder().decode(SearchIndex.self, from: data).items
            }.value
        }
        return searchItems ?? []
    }

    private func loadSourceMapIndex() async throws -> SourceMapIndex {
        if sourceMapIndex == nil {
            let url = book.directoryURL.appendingPathComponent("source_map.json")
            sourceMapIndex = try await Task.detached(priority: .userInitiated) {
                let data = try Data(contentsOf: url)
                return SourceMapIndex(blocks: try JSONDecoder().decode(SourceMap.self, from: data).blocks)
            }.value
        }
        return sourceMapIndex ?? SourceMapIndex(blocks: [])
    }

    var originalPDFURL: URL? {
        let url = book.directoryURL.appendingPathComponent("source/original.pdf")
        return FileManager.default.fileExists(atPath: url.path) ? url : nil
    }
}
