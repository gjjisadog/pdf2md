import Foundation

public final class ReadingProgressStore {
    private struct Storage: Codable {
        var byBook: [String: ReadingProgress] = [:]
        var byChapter: [String: ReadingProgress] = [:]
    }

    private let storageURL: URL
    private var storage: Storage
    private let encoder: JSONEncoder
    private let decoder: JSONDecoder

    public init(storageURL: URL) throws {
        self.storageURL = storageURL
        self.encoder = JSONEncoder()
        self.decoder = JSONDecoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        encoder.dateEncodingStrategy = .iso8601
        decoder.dateDecodingStrategy = .iso8601

        if FileManager.default.fileExists(atPath: storageURL.path) {
            do {
                let data = try Data(contentsOf: storageURL)
                self.storage = try decoder.decode(Storage.self, from: data)
            } catch {
                try? Self.recoverCorruptStorage(at: storageURL)
                self.storage = Storage()
            }
        } else {
            self.storage = Storage()
        }
    }

    public func save(_ progress: ReadingProgress) throws {
        storage.byBook[progress.bookId] = progress
        storage.byChapter[Self.chapterKey(bookId: progress.bookId, chapterPath: progress.chapterPath)] = progress
        try persist()
    }

    public func progress(forBookId bookId: String) -> ReadingProgress? {
        storage.byBook[bookId]
    }

    public func progress(forBookId bookId: String, chapterPath: String) -> ReadingProgress? {
        storage.byChapter[Self.chapterKey(bookId: bookId, chapterPath: chapterPath)]
    }

    private func persist() throws {
        try FileManager.default.createDirectory(
            at: storageURL.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )
        let data = try encoder.encode(storage)
        try data.write(to: storageURL, options: [.atomic])
    }

    private static func chapterKey(bookId: String, chapterPath: String) -> String {
        "\(bookId)::\(chapterPath)"
    }

    private static func recoverCorruptStorage(at storageURL: URL) throws {
        let backupName = storageURL.lastPathComponent + ".corrupt-\(Int(Date().timeIntervalSince1970))"
        let backupURL = storageURL.deletingLastPathComponent().appendingPathComponent(backupName)
        try? FileManager.default.moveItem(at: storageURL, to: backupURL)
    }
}
