import Foundation

public struct BookMDValidationResult: Equatable, Sendable {
    public let isValid: Bool
    public let errors: [String]
    public let warnings: [String]
    public let manifest: BookManifest?
}

public enum BookMDError: Error, LocalizedError, Equatable {
    case archiveNotFound(String)
    case invalidArchive(String)
    case missingRequiredFile(String)
    case unsafeArchivePath(String)
    case invalidJSON(String)
    case missingChapter(String)
    case fileNotFoundInArchive(String)
    case extractionTargetExists(String)
    case duplicateArchivePath(String)

    public var errorDescription: String? {
        switch self {
        case .archiveNotFound(let path):
            return "BookMD 文件不存在：\(path)"
        case .invalidArchive(let path):
            return "无法读取 BookMD zip 包：\(path)"
        case .missingRequiredFile(let name):
            return "BookMD 缺少必需文件：\(name)"
        case .unsafeArchivePath(let path):
            return "BookMD 包含不安全路径：\(path)"
        case .invalidJSON(let name):
            return "BookMD JSON 无法解析：\(name)"
        case .missingChapter(let path):
            return "book.json 引用的章节不存在：\(path)"
        case .fileNotFoundInArchive(let path):
            return "BookMD 包内找不到文件：\(path)"
        case .extractionTargetExists(let path):
            return "导入目标已存在：\(path)"
        case .duplicateArchivePath(let path):
            return "BookMD 包含重复路径：\(path)"
        }
    }
}

public final class BookMDArchiveValidator {
    private let requiredFiles = [
        "book.json",
        "source_map.json",
        "terms.json",
        "translation.json",
        "reading_config.json",
        "search_index.json",
    ]

    public init() {}

    public func validateArchive(at url: URL) throws -> BookMDValidationResult {
        guard FileManager.default.fileExists(atPath: url.path) else {
            throw BookMDError.archiveNotFound(url.path)
        }

        let archive = try BookMDZipArchive(url: url)

        var errors: [String] = []
        var warnings: [String] = []
        let names = Set(archive.paths)

        for name in names where !Self.isSafeArchivePath(name) {
            errors.append(BookMDError.unsafeArchivePath(name).localizedDescription)
        }

        for required in requiredFiles where !names.contains(required) {
            errors.append(BookMDError.missingRequiredFile(required).localizedDescription)
        }

        if !names.contains(where: { $0.hasPrefix("chapters/") && $0.hasSuffix(".md") }) {
            errors.append("BookMD 缺少 chapters/*.md 章节文件")
        }

        if !names.contains("source/original.pdf") {
            warnings.append("BookMD 缺少 source/original.pdf，阅读可继续但无法回看原 PDF")
        }

        var manifest: BookManifest?
        if names.contains("book.json") {
            do {
                manifest = try BookMDArchive(url: url).manifest()
                if let formatVersion = manifest?.formatVersion {
                    let major = formatVersion.split(separator: ".", maxSplits: 1).first.map(String.init)
                    if major != "1" {
                        errors.append("Unsupported BookMD format major version: \(formatVersion)")
                    }
                } else {
                    warnings.append("Legacy BookMD format detected; migration to format_version 1.0 is recommended")
                }
                for chapter in manifest?.chapters ?? [] where !names.contains(chapter.path) {
                    errors.append(BookMDError.missingChapter(chapter.path).localizedDescription)
                }
            } catch {
                errors.append(BookMDError.invalidJSON("book.json").localizedDescription)
            }
        }

        return BookMDValidationResult(
            isValid: errors.isEmpty,
            errors: errors,
            warnings: warnings,
            manifest: manifest
        )
    }

    static func isSafeArchivePath(_ path: String) -> Bool {
        guard !path.isEmpty, !path.hasPrefix("/") else { return false }
        let components = path.split(separator: "/", omittingEmptySubsequences: false)
        return !components.contains("..")
    }
}

public final class BookMDArchive {
    public let url: URL
    private let archive: BookMDZipArchive
    private let decoder: JSONDecoder

    public init(url: URL) throws {
        self.url = url
        self.archive = try BookMDZipArchive(url: url)
        self.decoder = JSONDecoder()
    }

    public func manifest() throws -> BookManifest {
        try decode(BookManifest.self, from: "book.json")
    }

    public func readingConfig() throws -> ReadingConfig {
        try decode(ReadingConfig.self, from: "reading_config.json")
    }

    public func searchIndex() throws -> SearchIndex {
        try decode(SearchIndex.self, from: "search_index.json")
    }

    public func sourceMap() throws -> SourceMap {
        try decode(SourceMap.self, from: "source_map.json")
    }

    public func chapterMarkdown(path: String) throws -> String {
        try textFile(path)
    }

    public func textFile(_ path: String) throws -> String {
        let data = try dataFile(path)
        guard let text = String(data: data, encoding: .utf8) else {
            throw BookMDError.invalidJSON(path)
        }
        return text
    }

    public func dataFile(_ path: String) throws -> Data {
        guard BookMDArchiveValidator.isSafeArchivePath(path) else {
            throw BookMDError.unsafeArchivePath(path)
        }
        return try archive.data(for: path)
    }

    public func extract(to destination: URL) throws {
        if FileManager.default.fileExists(atPath: destination.path) {
            throw BookMDError.extractionTargetExists(destination.path)
        }
        try FileManager.default.createDirectory(at: destination, withIntermediateDirectories: true)
        do {
            for path in archive.paths {
                guard BookMDArchiveValidator.isSafeArchivePath(path) else {
                    throw BookMDError.unsafeArchivePath(path)
                }
                let outputURL = destination.appendingPathComponent(path)
                if path.hasSuffix("/") {
                    try FileManager.default.createDirectory(at: outputURL, withIntermediateDirectories: true)
                } else {
                    try FileManager.default.createDirectory(
                        at: outputURL.deletingLastPathComponent(),
                        withIntermediateDirectories: true
                    )
                    try archive.data(for: path).write(to: outputURL, options: [.atomic])
                }
            }
        } catch {
            try? FileManager.default.removeItem(at: destination)
            throw error
        }
    }

    private func decode<T: Decodable>(_ type: T.Type, from path: String) throws -> T {
        do {
            return try decoder.decode(T.self, from: dataFile(path))
        } catch let error as BookMDError {
            throw error
        } catch {
            throw BookMDError.invalidJSON(path)
        }
    }
}

private struct BookMDZipEntry {
    let path: String
    let compressionMethod: UInt16
    let compressedSize: Int
    let uncompressedSize: Int
    let localHeaderOffset: Int
}

private final class BookMDZipArchive {
    let paths: [String]

    private let payload: Data
    private let entriesByPath: [String: BookMDZipEntry]

    init(url: URL) throws {
        self.payload = try Data(contentsOf: url)
        let entries = try Self.readCentralDirectory(from: payload, archivePath: url.path)
        self.paths = entries.map(\.path)
        var entriesByPath: [String: BookMDZipEntry] = [:]
        for entry in entries {
            if entriesByPath[entry.path] != nil {
                throw BookMDError.duplicateArchivePath(entry.path)
            }
            entriesByPath[entry.path] = entry
        }
        self.entriesByPath = entriesByPath
    }

    func data(for path: String) throws -> Data {
        guard let entry = entriesByPath[path] else {
            throw BookMDError.fileNotFoundInArchive(path)
        }
        guard payload.readUInt32(at: entry.localHeaderOffset) == 0x0403_4b50 else {
            throw BookMDError.invalidArchive(path)
        }
        let nameLength = Int(payload.readUInt16(at: entry.localHeaderOffset + 26))
        let extraLength = Int(payload.readUInt16(at: entry.localHeaderOffset + 28))
        let dataOffset = entry.localHeaderOffset + 30 + nameLength + extraLength
        let dataEnd = dataOffset + entry.compressedSize
        guard dataOffset >= 0, dataEnd <= payload.count else {
            throw BookMDError.invalidArchive(path)
        }

        let compressed = payload.subdata(in: dataOffset..<dataEnd)
        switch entry.compressionMethod {
        case 0:
            return compressed
        case 8:
            return try Self.inflate(compressed, uncompressedSize: entry.uncompressedSize, path: path)
        default:
            throw BookMDError.invalidArchive("unsupported compression method \(entry.compressionMethod): \(path)")
        }
    }

    private static func readCentralDirectory(from data: Data, archivePath: String) throws -> [BookMDZipEntry] {
        guard let eocdOffset = findEndOfCentralDirectory(in: data) else {
            throw BookMDError.invalidArchive(archivePath)
        }
        let entryCount = Int(data.readUInt16(at: eocdOffset + 10))
        let centralDirectorySize = Int(data.readUInt32(at: eocdOffset + 12))
        let centralDirectoryOffset = Int(data.readUInt32(at: eocdOffset + 16))
        guard centralDirectoryOffset >= 0,
              centralDirectorySize >= 0,
              centralDirectoryOffset + centralDirectorySize <= data.count
        else {
            throw BookMDError.invalidArchive(archivePath)
        }

        var entries: [BookMDZipEntry] = []
        var offset = centralDirectoryOffset
        for _ in 0..<entryCount {
            guard offset + 46 <= data.count,
                  data.readUInt32(at: offset) == 0x0201_4b50
            else {
                throw BookMDError.invalidArchive(archivePath)
            }

            let compressionMethod = data.readUInt16(at: offset + 10)
            let compressedSize = Int(data.readUInt32(at: offset + 20))
            let uncompressedSize = Int(data.readUInt32(at: offset + 24))
            let nameLength = Int(data.readUInt16(at: offset + 28))
            let extraLength = Int(data.readUInt16(at: offset + 30))
            let commentLength = Int(data.readUInt16(at: offset + 32))
            let localHeaderOffset = Int(data.readUInt32(at: offset + 42))
            let nameOffset = offset + 46
            let nextOffset = nameOffset + nameLength + extraLength + commentLength
            guard nextOffset <= data.count else {
                throw BookMDError.invalidArchive(archivePath)
            }

            let nameData = data.subdata(in: nameOffset..<(nameOffset + nameLength))
            guard let path = String(data: nameData, encoding: .utf8) else {
                throw BookMDError.invalidArchive("invalid file name encoding")
            }
            entries.append(
                BookMDZipEntry(
                    path: path,
                    compressionMethod: compressionMethod,
                    compressedSize: compressedSize,
                    uncompressedSize: uncompressedSize,
                    localHeaderOffset: localHeaderOffset
                )
            )
            offset = nextOffset
        }
        return entries
    }

    private static func findEndOfCentralDirectory(in data: Data) -> Int? {
        guard data.count >= 22 else { return nil }
        let lowerBound = max(0, data.count - 65_557)
        var offset = data.count - 22
        while offset >= lowerBound {
            if data.readUInt32(at: offset) == 0x0605_4b50 {
                return offset
            }
            offset -= 1
        }
        return nil
    }

    private static func inflate(_ data: Data, uncompressedSize: Int, path: String) throws -> Data {
        if uncompressedSize == 0 {
            return Data()
        }

        var output = Data(count: uncompressedSize)
        let status = output.withUnsafeMutableBytes { outputBuffer in
            data.withUnsafeBytes { inputBuffer in
                BookMDInflateRawDeflate(
                    inputBuffer.bindMemory(to: UInt8.self).baseAddress!,
                    data.count,
                    outputBuffer.bindMemory(to: UInt8.self).baseAddress!,
                    uncompressedSize
                )
            }
        }
        guard status == 0 else {
            throw BookMDError.invalidArchive("unable to inflate \(path)")
        }
        return output
    }
}

private extension Data {
    func readUInt16(at offset: Int) -> UInt16 {
        UInt16(self[offset])
            | (UInt16(self[offset + 1]) << 8)
    }

    func readUInt32(at offset: Int) -> UInt32 {
        UInt32(self[offset])
            | (UInt32(self[offset + 1]) << 8)
            | (UInt32(self[offset + 2]) << 16)
            | (UInt32(self[offset + 3]) << 24)
    }
}
