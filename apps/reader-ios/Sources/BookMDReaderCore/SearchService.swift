import Foundation

public struct SearchService: Sendable {
    private let items: [SearchItem]

    public init(items: [SearchItem]) {
        self.items = items
    }

    public func search(_ query: String, limit: Int = 100) -> [SearchItem] {
        let normalizedQuery = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !normalizedQuery.isEmpty else { return [] }

        return items.lazy
            .filter { item in
                item.text.range(of: normalizedQuery, options: [.caseInsensitive, .diacriticInsensitive]) != nil
            }
            .prefix(max(0, limit))
            .map { $0 }
    }
}
