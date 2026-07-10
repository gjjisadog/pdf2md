import Foundation

public struct BookManifest: Codable, Equatable, Sendable {
    public let bookId: String
    public let title: String
    public let author: String?
    public let sourcePDF: String?
    public let language: String?
    public let createdAt: String?
    public let version: String?
    public let chapters: [BookChapter]

    enum CodingKeys: String, CodingKey {
        case bookId = "book_id"
        case title
        case author
        case sourcePDF = "source_pdf"
        case language
        case createdAt = "created_at"
        case version
        case chapters
    }
}

public struct BookChapter: Codable, Equatable, Hashable, Identifiable, Sendable {
    public let id: String
    public let title: String
    public let path: String
    public let order: Int
}

public struct ReadingConfig: Codable, Equatable, Sendable {
    public let defaultMode: String
    public let layout: String
    public let fontSize: Int
    public let lineHeight: Double
    public let theme: String
    public let paragraphIndent: Bool?

    public init(
        defaultMode: String,
        layout: String,
        fontSize: Int,
        lineHeight: Double,
        theme: String,
        paragraphIndent: Bool?
    ) {
        self.defaultMode = defaultMode
        self.layout = layout
        self.fontSize = fontSize
        self.lineHeight = lineHeight
        self.theme = theme
        self.paragraphIndent = paragraphIndent
    }

    enum CodingKeys: String, CodingKey {
        case defaultMode = "default_mode"
        case layout
        case fontSize = "font_size"
        case lineHeight = "line_height"
        case theme
        case paragraphIndent = "paragraph_indent"
    }
}

public struct SearchIndex: Codable, Equatable, Sendable {
    public let items: [SearchItem]
}

public struct SearchItem: Codable, Equatable, Identifiable, Sendable {
    public var id: String { "\(chapterPath)::\(blockId)" }

    public let blockId: String
    public let chapterId: String
    public let chapterPath: String
    public let chapterTitle: String
    public let type: String
    public let text: String

    enum CodingKeys: String, CodingKey {
        case blockId = "block_id"
        case chapterId = "chapter_id"
        case chapterPath = "chapter_path"
        case chapterTitle = "chapter_title"
        case type
        case text
    }
}

public struct SourceMap: Codable, Equatable, Sendable {
    public let blocks: [SourceMapBlock]
}

public struct SourceMapBlock: Codable, Equatable, Identifiable, Sendable {
    public var id: String { blockId }

    public let blockId: String
    public let chapterId: String?
    public let markdownPath: String?
    public let sourcePage: Int
    public let bbox: [Double]
    public let sourceText: String
    public let translatedText: String?
    public let type: String

    enum CodingKeys: String, CodingKey {
        case blockId = "block_id"
        case chapterId = "chapter_id"
        case markdownPath = "markdown_path"
        case sourcePage = "source_page"
        case bbox
        case sourceText = "source_text"
        case translatedText = "translated_text"
        case type
    }
}

public struct TermsFile: Codable, Equatable, Sendable {
    public let terms: [BookTerm]
}

public struct BookTerm: Codable, Equatable, Identifiable, Sendable {
    public var id: String { "\(source)::\(target)::\(abbr ?? "")" }

    public let source: String
    public let target: String
    public let abbr: String?
    public let category: String?
    public let note: String?
}

public struct ReadingProgress: Codable, Equatable, Sendable {
    public let bookId: String
    public let chapterPath: String
    public let blockId: String
    public let scrollY: Int
    public let scrollX: Int
    public let pageIndex: Int
    public let pageCount: Int
    public let updatedAt: Date

    enum CodingKeys: String, CodingKey {
        case bookId
        case chapterPath
        case blockId
        case scrollY
        case scrollX
        case pageIndex
        case pageCount
        case updatedAt
    }

    public init(
        bookId: String,
        chapterPath: String,
        blockId: String,
        scrollY: Int,
        scrollX: Int = 0,
        pageIndex: Int = 0,
        pageCount: Int = 0,
        updatedAt: Date = Date()
    ) {
        self.bookId = bookId
        self.chapterPath = chapterPath
        self.blockId = blockId
        self.scrollY = scrollY
        self.scrollX = scrollX
        self.pageIndex = pageIndex
        self.pageCount = pageCount
        self.updatedAt = updatedAt
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        self.bookId = try container.decode(String.self, forKey: .bookId)
        self.chapterPath = try container.decode(String.self, forKey: .chapterPath)
        self.blockId = try container.decode(String.self, forKey: .blockId)
        self.scrollY = try container.decode(Int.self, forKey: .scrollY)
        self.scrollX = try container.decodeIfPresent(Int.self, forKey: .scrollX) ?? 0
        self.pageIndex = try container.decodeIfPresent(Int.self, forKey: .pageIndex) ?? 0
        self.pageCount = try container.decodeIfPresent(Int.self, forKey: .pageCount) ?? 0
        self.updatedAt = try container.decode(Date.self, forKey: .updatedAt)
    }
}
