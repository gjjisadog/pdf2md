import SwiftUI
import BookMDReaderCore

struct ReaderView: View {
    @EnvironmentObject private var library: BookLibraryStore
    let runtime: BookRuntime
    let chapter: BookChapter
    let targetBlockId: String?

    @State private var markdown = ""
    @State private var settings: ReaderDisplaySettings
    @State private var isSettingsPresented = false
    @State private var sourceBlock: SourceMapBlock?
    @State private var pdfPageNumber: Int?
    @State private var errorMessage: String?

    init(runtime: BookRuntime, chapter: BookChapter, targetBlockId: String?) {
        self.runtime = runtime
        self.chapter = chapter
        self.targetBlockId = targetBlockId
        let loadedSettings = ReaderSettingsStore(bookId: runtime.manifest.bookId)
            .load(defaultConfig: runtime.readingConfig)
        self._settings = State(initialValue: loadedSettings)
    }

    var body: some View {
        BookMDWebView(
            markdown: markdown,
            config: settings.readingConfig(),
            targetBlockId: targetBlockId,
            restoredProgress: restoredProgress,
            onSourceMapRequested: showSourceMap,
            onProgressChanged: saveProgress
        )
        .navigationTitle(chapter.title)
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItemGroup(placement: .topBarTrailing) {
                if isUITestMode, let targetBlockId, !targetBlockId.isEmpty {
                    Button {
                        showSourceMap(targetBlockId)
                    } label: {
                        Label("Source Map", systemImage: "scope")
                    }
                    .accessibilityIdentifier("reader.test.sourceMap")
                }
                Button {
                    isSettingsPresented = true
                } label: {
                    Label("阅读设置", systemImage: "textformat.size")
                }
                .accessibilityIdentifier("reader.settings.button")
            }
        }
        .task(id: chapter.path) {
            do {
                markdown = try await runtime.markdown(for: chapter)
            } catch {
                errorMessage = error.localizedDescription
            }
        }
        .sheet(item: $sourceBlock) { block in
            SourceMapSheet(block: block) { page in
                pdfPageNumber = page
            }
        }
        .sheet(isPresented: $isSettingsPresented) {
            ReaderSettingsSheet(settings: $settings)
                .onDisappear {
                    ReaderSettingsStore(bookId: runtime.manifest.bookId).save(settings)
                }
        }
        .sheet(item: pdfPageBinding) { page in
            if let pdfURL = runtime.originalPDFURL {
                PDFPageSheet(pdfURL: pdfURL, pageNumber: page.value)
            } else {
                ContentUnavailableView("未找到原 PDF", systemImage: "doc.questionmark")
            }
        }
        .alert("阅读错误", isPresented: Binding(
            get: { errorMessage != nil },
            set: { if !$0 { errorMessage = nil } }
        )) {
            Button("好", role: .cancel) {}
        } message: {
            Text(errorMessage ?? "")
        }
    }

    private var restoredProgress: ReadingProgress? {
        try? library.progressStore().progress(forBookId: runtime.manifest.bookId, chapterPath: chapter.path)
    }

    private var isUITestMode: Bool {
        ProcessInfo.processInfo.environment["BOOKMD_UI_TEST_MODE"] == "1"
    }

    private var pdfPageBinding: Binding<PDFPage?> {
        Binding(
            get: { pdfPageNumber.map(PDFPage.init(value:)) },
            set: { pdfPageNumber = $0?.value }
        )
    }

    private func showSourceMap(_ blockId: String) {
        Task {
            do {
                sourceBlock = try await runtime.sourceBlock(id: blockId)
            } catch {
                errorMessage = error.localizedDescription
            }
        }
    }

    private func saveProgress(progress: BookMDWebProgress) {
        do {
            try library.progressStore().save(ReadingProgress(
                bookId: runtime.manifest.bookId,
                chapterPath: chapter.path,
                blockId: progress.blockId,
                scrollY: progress.scrollY,
                scrollX: progress.scrollX,
                pageIndex: progress.pageIndex,
                pageCount: progress.pageCount
            ))
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private struct PDFPage: Identifiable {
        let value: Int
        var id: Int { value }
    }
}
