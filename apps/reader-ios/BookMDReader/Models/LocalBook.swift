import Foundation
import BookMDReaderCore

struct LocalBook: Identifiable, Equatable, Hashable {
    var id: String { manifest.bookId }

    let directoryURL: URL
    let manifest: BookManifest
    let importedAt: Date

    var title: String {
        manifest.title.isEmpty ? directoryURL.lastPathComponent : manifest.title
    }

    static func == (lhs: LocalBook, rhs: LocalBook) -> Bool {
        lhs.id == rhs.id
    }

    func hash(into hasher: inout Hasher) {
        hasher.combine(id)
    }
}
