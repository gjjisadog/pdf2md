import XCTest

final class BookMDReaderUITests: XCTestCase {
    private var sampleBookURL: URL {
        if let override = ProcessInfo.processInfo.environment["BOOKMD_REAL_SAMPLE"] {
            return URL(fileURLWithPath: override)
        }

        var directory = URL(fileURLWithPath: #filePath).deletingLastPathComponent()
        while directory.path != "/" {
            let candidate = directory.appendingPathComponent("tmp/real_book_full_clean_toc.bookmd")
            if FileManager.default.fileExists(atPath: candidate.path) {
                return candidate
            }
            directory.deleteLastPathComponent()
        }
        return URL(fileURLWithPath: "/tmp/missing-real-book-full-clean-toc.bookmd")
    }

    func testRealBookReaderFlowOnIPadMini() throws {
        let app = XCUIApplication()
        let sandbox = FileManager.default.temporaryDirectory
            .appendingPathComponent("bookmd-ios-ui-\(UUID().uuidString)", isDirectory: true)
        try? FileManager.default.removeItem(at: sandbox)
        try FileManager.default.createDirectory(at: sandbox, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: sandbox) }

        app.launchEnvironment["BOOKMD_UI_TEST_IMPORT_PATH"] = sampleBookURL.path
        app.launchEnvironment["BOOKMD_UI_TEST_SUPPORT_ROOT"] = sandbox.path
        app.launchEnvironment["BOOKMD_UI_TEST_RESET_LIBRARY"] = "1"
        app.launchEnvironment["BOOKMD_UI_TEST_MODE"] = "1"
        XCUIDevice.shared.orientation = .landscapeLeft
        app.launch()

        let shelfTitle = app.staticTexts["DC-DC Converter Topologies Basic to Advanced"]
        XCTAssertTrue(shelfTitle.waitForExistence(timeout: 30))
        XCTAssertTrue(app.staticTexts["18 章"].exists)

        shelfTitle.tap()

        let firstChapter = app.buttons["toc.chapter.chapters/001_chapter_1.md"]
        XCTAssertTrue(firstChapter.waitForExistence(timeout: 20))

        XCTAssertTrue(app.collectionViews["book.sidebar"].waitForExistence(timeout: 10))

        let termsLink = app.buttons["book.terms.link"]
        XCTAssertTrue(termsLink.waitForExistence(timeout: 10))
        termsLink.tap()
        XCTAssertTrue(app.collectionViews["terms.list"].waitForExistence(timeout: 10))
        XCTAssertTrue(app.staticTexts["pulse width modulation"].waitForExistence(timeout: 10))
        XCTAssertTrue(app.staticTexts["脉宽调制"].exists)
        app.buttons["terms.done"].tap()

        let searchField = app.descendants(matching: .any)["book.search.field"]
        XCTAssertTrue(searchField.waitForExistence(timeout: 10))
        searchField.tap()
        searchField.typeText("Converter")
        app.buttons["book.search.button"].tap()

        let firstResult = app.buttons["search.result.p001_b001"]
        XCTAssertTrue(firstResult.waitForExistence(timeout: 20))
        firstResult.tap()

        let webView = app.webViews["reader.webview"]
        XCTAssertTrue(webView.waitForExistence(timeout: 20))
        let sourceBlock = app.descendants(matching: .any)["source block p001_b001"]
        XCTAssertTrue(sourceBlock.waitForExistence(timeout: 20))
        let sourceMapButton = app.buttons["reader.test.sourceMap"]
        XCTAssertTrue(sourceMapButton.waitForExistence(timeout: 10))
        sourceMapButton.tap()

        XCTAssertTrue(app.navigationBars["p001_b001"].waitForExistence(timeout: 20))
        XCTAssertTrue(app.staticTexts["sourceMap.page.1"].exists)
        XCTAssertTrue(app.staticTexts["sourceMap.bbox.164, 465, 864, 969"].exists)
        app.buttons["查看原 PDF 页"].tap()

        XCTAssertTrue(app.navigationBars["PDF 第 1 页"].waitForExistence(timeout: 20))
        app.buttons["pdf.done"].tap()

        let settingsButton = app.buttons["reader.settings.button"]
        XCTAssertTrue(settingsButton.waitForExistence(timeout: 10))
        settingsButton.tap()
        XCTAssertTrue(app.collectionViews["reader.settings.form"].waitForExistence(timeout: 10))
        XCTAssertTrue(app.descendants(matching: .any)["reader.settings.fontSize"].exists)
        XCTAssertTrue(app.descendants(matching: .any)["reader.settings.lineHeight"].exists)
        XCTAssertTrue(app.descendants(matching: .any)["reader.settings.theme"].exists)
        XCTAssertTrue(app.descendants(matching: .any)["reader.settings.layout"].exists)
        XCTAssertTrue(app.descendants(matching: .any)["reader.settings.language"].exists)
        app.buttons["reader.settings.done"].tap()

        XCUIDevice.shared.orientation = .landscapeLeft
        XCTAssertTrue(app.collectionViews["book.sidebar"].waitForExistence(timeout: 10))
        XCTAssertTrue(app.webViews["reader.webview"].exists)
        XCUIDevice.shared.orientation = .portrait
        XCTAssertTrue(app.webViews["reader.webview"].waitForExistence(timeout: 10))

        app.terminate()
        let restoredApp = XCUIApplication()
        restoredApp.launchEnvironment["BOOKMD_UI_TEST_IMPORT_PATH"] = sampleBookURL.path
        restoredApp.launchEnvironment["BOOKMD_UI_TEST_SUPPORT_ROOT"] = sandbox.path
        restoredApp.launchEnvironment["BOOKMD_UI_TEST_MODE"] = "1"
        XCUIDevice.shared.orientation = .landscapeLeft
        restoredApp.launch()

        let restoredShelfTitle = restoredApp.staticTexts["DC-DC Converter Topologies Basic to Advanced"]
        XCTAssertTrue(restoredShelfTitle.waitForExistence(timeout: 20))
        restoredShelfTitle.tap()
        XCTAssertTrue(restoredApp.webViews["reader.webview"].waitForExistence(timeout: 20))
        XCTAssertTrue(restoredApp.buttons["reader.test.sourceMap"].waitForExistence(timeout: 10))
    }
}
