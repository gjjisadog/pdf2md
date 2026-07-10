import SwiftUI
import UniformTypeIdentifiers

struct ShelfView: View {
    @EnvironmentObject private var library: BookLibraryStore
    @State private var isImporterPresented = false

    var body: some View {
        NavigationStack {
            List {
                if library.books.isEmpty {
                    ContentUnavailableView("没有本地书籍", systemImage: "books.vertical")
                } else {
                    ForEach(library.books) { book in
                        NavigationLink {
                            BookWorkspaceView(book: book)
                        } label: {
                            BookRow(book: book)
                        }
                    }
                }
            }
            .accessibilityIdentifier("shelf.list")
            .navigationTitle("BookMD")
            .toolbar {
                Button {
                    isImporterPresented = true
                } label: {
                    Label("导入", systemImage: "square.and.arrow.down")
                }
            }
        }
        .fileImporter(
            isPresented: $isImporterPresented,
            allowedContentTypes: [.bookMD, .zip],
            allowsMultipleSelection: false
        ) { result in
            guard case .success(let urls) = result, let url = urls.first else { return }
            Task { await library.importBook(from: url) }
        }
        .overlay {
            if library.isImporting {
                ProgressView("正在导入 BookMD...")
                    .padding()
                    .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 8))
            }
        }
        .alert("BookMD 错误", isPresented: Binding(
            get: { library.lastError != nil },
            set: { if !$0 { library.lastError = nil } }
        )) {
            Button("好", role: .cancel) {}
        } message: {
            Text(library.lastError ?? "")
        }
    }
}

private struct BookRow: View {
    let book: LocalBook

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(book.title)
                .font(.headline)
                .lineLimit(3)
                .accessibilityIdentifier("shelf.book.title.\(book.id)")
            Text("\(book.manifest.chapters.count) 章")
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
        .padding(.vertical, 6)
    }
}
