import SwiftUI

@main
struct BookMDReaderApp: App {
    @StateObject private var library: BookLibraryStore

    init() {
        let supportRoot = UITestBootstrap.supportRootURL()
        UITestBootstrap.resetSupportRootIfRequested(supportRoot)
        self._library = StateObject(wrappedValue: BookLibraryStore(supportRootURL: supportRoot))
    }

    var body: some Scene {
        WindowGroup {
            ShelfView()
                .environmentObject(library)
                .task {
                    await UITestBootstrap.importSampleIfRequested(into: library)
                }
        }
    }
}

private enum UITestBootstrap {
    private static var environment: [String: String] {
        ProcessInfo.processInfo.environment
    }

    static func supportRootURL() -> URL? {
        guard let path = environment["BOOKMD_UI_TEST_SUPPORT_ROOT"], !path.isEmpty else {
            return nil
        }
        return URL(fileURLWithPath: path, isDirectory: true)
    }

    static func resetSupportRootIfRequested(_ url: URL?) {
        guard environment["BOOKMD_UI_TEST_RESET_LIBRARY"] == "1", let url else { return }
        try? FileManager.default.removeItem(at: url)
    }

    @MainActor
    static func importSampleIfRequested(into library: BookLibraryStore) async {
        guard let path = environment["BOOKMD_UI_TEST_IMPORT_PATH"], !path.isEmpty else { return }
        guard library.books.isEmpty else { return }
        await library.importBook(from: URL(fileURLWithPath: path))
    }
}
