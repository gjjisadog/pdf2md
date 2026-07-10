import Foundation
import SwiftUI
import BookMDReaderCore

@MainActor
final class BookLibraryStore: ObservableObject {
    @Published private(set) var books: [LocalBook] = []
    @Published var lastError: String?
    @Published var isImporting = false

    let rootURL: URL
    private let progressURL: URL

    init(fileManager: FileManager = .default, supportRootURL: URL? = nil) {
        let support = supportRootURL ?? fileManager.urls(for: .applicationSupportDirectory, in: .userDomainMask).first
            ?? fileManager.temporaryDirectory
        self.rootURL = support.appendingPathComponent("BookMD/books", isDirectory: true)
        self.progressURL = support.appendingPathComponent("BookMD/progress/progress.json")
        refresh()
    }

    func refresh() {
        do {
            try FileManager.default.createDirectory(at: rootURL, withIntermediateDirectories: true)
            let directories = try FileManager.default.contentsOfDirectory(
                at: rootURL,
                includingPropertiesForKeys: [.creationDateKey],
                options: [.skipsHiddenFiles]
            )
            books = try directories.compactMap { directory in
                let manifestURL = directory.appendingPathComponent("book.json")
                guard FileManager.default.fileExists(atPath: manifestURL.path) else { return nil }
                let data = try Data(contentsOf: manifestURL)
                let manifest = try JSONDecoder().decode(BookManifest.self, from: data)
                let values = try directory.resourceValues(forKeys: [.creationDateKey])
                return LocalBook(
                    directoryURL: directory,
                    manifest: manifest,
                    importedAt: values.creationDate ?? .distantPast
                )
            }
            .sorted { $0.importedAt > $1.importedAt }
        } catch {
            lastError = error.localizedDescription
        }
    }

    func importBook(from sourceURL: URL) async {
        isImporting = true
        defer { isImporting = false }

        do {
            let needsAccess = sourceURL.startAccessingSecurityScopedResource()
            defer {
                if needsAccess {
                    sourceURL.stopAccessingSecurityScopedResource()
                }
            }

            let validator = BookMDArchiveValidator()
            let validation = try validator.validateArchive(at: sourceURL)
            guard validation.isValid, let manifest = validation.manifest else {
                throw ImportError.invalidBook(validation.errors.joined(separator: "\n"))
            }

            let archive = try BookMDArchive(url: sourceURL)
            let destination = rootURL.appendingPathComponent(safeBookDirectoryName(manifest.bookId), isDirectory: true)
            let temporary = rootURL.appendingPathComponent(".import-\(UUID().uuidString)", isDirectory: true)
            let destinationBackup = rootURL.appendingPathComponent(".replace-\(UUID().uuidString)", isDirectory: true)
            defer { try? FileManager.default.removeItem(at: temporary) }

            if FileManager.default.fileExists(atPath: temporary.path) {
                try FileManager.default.removeItem(at: temporary)
            }
            try archive.extract(to: temporary)
            do {
                if FileManager.default.fileExists(atPath: destinationBackup.path) {
                    try FileManager.default.removeItem(at: destinationBackup)
                }
                if FileManager.default.fileExists(atPath: destination.path) {
                    try FileManager.default.moveItem(at: destination, to: destinationBackup)
                }
                try FileManager.default.moveItem(at: temporary, to: destination)
                if FileManager.default.fileExists(atPath: destinationBackup.path) {
                    try FileManager.default.removeItem(at: destinationBackup)
                }
            } catch {
                try? FileManager.default.removeItem(at: destination)
                if FileManager.default.fileExists(atPath: destinationBackup.path) {
                    try? FileManager.default.moveItem(at: destinationBackup, to: destination)
                }
                throw error
            }
            refresh()
        } catch {
            lastError = error.localizedDescription
        }
    }

    func progressStore() throws -> ReadingProgressStore {
        try ReadingProgressStore(storageURL: progressURL)
    }

    private func safeBookDirectoryName(_ rawName: String) -> String {
        let source = rawName.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !source.isEmpty else { return UUID().uuidString }

        let allowed = CharacterSet.alphanumerics.union(CharacterSet(charactersIn: "._-"))
        let cleaned = String(source.unicodeScalars.map { scalar in
            allowed.contains(scalar) ? Character(String(scalar)) : "_"
        })
        .trimmingCharacters(in: CharacterSet(charactersIn: "._- "))

        return cleaned.isEmpty ? UUID().uuidString : cleaned
    }

    enum ImportError: LocalizedError {
        case invalidBook(String)

        var errorDescription: String? {
            switch self {
            case .invalidBook(let message):
                return message.isEmpty ? "BookMD 校验失败" : message
            }
        }
    }
}
