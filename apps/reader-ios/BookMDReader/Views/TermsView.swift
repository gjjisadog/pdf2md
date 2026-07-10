import SwiftUI
import BookMDReaderCore

struct TermsView: View {
    let terms: [BookTerm]

    var body: some View {
        List {
            ForEach(Array(terms.enumerated()), id: \.offset) { _, term in
                TermRow(term: term)
                    .accessibilityIdentifier("terms.row.\(term.source)")
            }
        }
        .accessibilityIdentifier("terms.list")
        .navigationTitle("术语表")
    }
}

private struct TermRow: View {
    let term: BookTerm

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(alignment: .firstTextBaseline) {
                Text(term.source)
                    .font(.headline)
                if let abbr = term.abbr, !abbr.isEmpty {
                    Text(abbr)
                        .font(.caption)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(.secondary.opacity(0.12), in: Capsule())
                }
            }
            Text(term.target)
                .font(.subheadline)
            if let note = term.note, !note.isEmpty {
                Text(note)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(.vertical, 4)
    }
}
