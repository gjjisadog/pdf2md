import SwiftUI
import BookMDReaderCore

struct BookWorkspaceView: View {
    @EnvironmentObject private var library: BookLibraryStore
    let book: LocalBook

    @State private var runtime: BookRuntime?
    @State private var selectedChapter: BookChapter?
    @State private var query = ""
    @State private var searchResults: [SearchItem] = []
    @State private var terms: [BookTerm] = []
    @State private var targetBlockId: String?
    @State private var isSearching = false
    @State private var isTermsPresented = false
    @State private var searchTask: Task<Void, Never>?
    @State private var errorMessage: String?
    @State private var columnVisibility: NavigationSplitViewVisibility = .all

    var body: some View {
        Group {
            if let runtime {
                NavigationSplitView(columnVisibility: $columnVisibility) {
                    List {
                        Section("搜索") {
                            TextField("搜索全书", text: $query)
                                .textInputAutocapitalization(.never)
                                .onSubmit(performSearch)
                                .accessibilityIdentifier("book.search.field")
                            Button {
                                performSearch()
                            } label: {
                                if isSearching {
                                    ProgressView()
                                } else {
                                    Label("搜索", systemImage: "magnifyingglass")
                                }
                            }
                            .accessibilityIdentifier("book.search.button")
                            ForEach(searchResults.prefix(30)) { item in
                                Button {
                                    openSearchResult(item)
                                } label: {
                                    VStack(alignment: .leading, spacing: 4) {
                                        Text(item.chapterTitle)
                                            .font(.caption)
                                            .foregroundStyle(.secondary)
                                        Text(item.text)
                                            .font(.subheadline)
                                        .lineLimit(3)
                                    }
                                }
                                .accessibilityIdentifier("search.result.\(item.blockId)")
                            }
                        }

                        if !terms.isEmpty {
                            Section("资料") {
                                Button {
                                    isTermsPresented = true
                                } label: {
                                    Label("术语表", systemImage: "character.book.closed")
                                }
                                .accessibilityIdentifier("book.terms.link")
                            }
                        }

                        Section("目录") {
                            ForEach(runtime.manifest.chapters.sorted { $0.order < $1.order }, id: \.path) { chapter in
                                Button {
                                    selectedChapter = chapter
                                    targetBlockId = nil
                                } label: {
                                    HStack {
                                        Text(chapter.title)
                                        if selectedChapter == chapter {
                                            Spacer()
                                            Image(systemName: "checkmark")
                                                .foregroundStyle(.secondary)
                                        }
                                    }
                                }
                                .accessibilityIdentifier("toc.chapter.\(chapter.path)")
                            }
                        }
                    }
                    .accessibilityIdentifier("book.sidebar")
                    .navigationTitle(runtime.manifest.title)
                } detail: {
                    if let selectedChapter {
                        ReaderView(
                            runtime: runtime,
                            chapter: selectedChapter,
                            targetBlockId: targetBlockId
                        )
                        .id(selectedChapter.path)
                    } else {
                        ContentUnavailableView("选择章节", systemImage: "text.book.closed")
                    }
                }
                .navigationSplitViewStyle(.balanced)
                .sheet(isPresented: $isTermsPresented) {
                    NavigationStack {
                        TermsView(terms: terms)
                            .toolbar {
                                ToolbarItem(placement: .topBarTrailing) {
                                    Button("完成") {
                                        isTermsPresented = false
                                    }
                                    .accessibilityIdentifier("terms.done")
                                }
                            }
                    }
                }
            } else {
                ProgressView("正在打开书籍...")
            }
        }
        .task(id: book.id) {
            do {
                let loaded = try BookRuntime(book: book)
                runtime = loaded
                terms = (try? await loaded.terms()) ?? []
                selectedChapter = restoreChapter(runtime: loaded)
            } catch {
                errorMessage = error.localizedDescription
            }
        }
        .alert("打开失败", isPresented: Binding(
            get: { errorMessage != nil },
            set: { if !$0 { errorMessage = nil } }
        )) {
            Button("好", role: .cancel) {}
        } message: {
            Text(errorMessage ?? "")
        }
    }

    private func performSearch() {
        guard let runtime else { return }
        guard !query.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            searchTask?.cancel()
            searchResults = []
            isSearching = false
            return
        }
        searchTask?.cancel()
        isSearching = true
        searchTask = Task {
            do {
                let results = try await runtime.search(query)
                guard !Task.isCancelled else { return }
                searchResults = results
            } catch {
                guard !Task.isCancelled else { return }
                errorMessage = error.localizedDescription
            }
            isSearching = false
        }
    }

    private func openSearchResult(_ item: SearchItem) {
        selectedChapter = runtime?.manifest.chapters.first { $0.path == item.chapterPath }
        targetBlockId = item.blockId
        if let runtime {
            try? library.progressStore().save(ReadingProgress(
                bookId: runtime.manifest.bookId,
                chapterPath: item.chapterPath,
                blockId: item.blockId,
                scrollY: 0,
                scrollX: 0,
                pageIndex: 0,
                pageCount: 0
            ))
        }
    }

    private func restoreChapter(runtime: BookRuntime) -> BookChapter? {
        guard let progress = try? library.progressStore().progress(forBookId: runtime.manifest.bookId) else {
            return nil
        }
        targetBlockId = progress.blockId
        return runtime.manifest.chapters.first { $0.path == progress.chapterPath }
    }
}
