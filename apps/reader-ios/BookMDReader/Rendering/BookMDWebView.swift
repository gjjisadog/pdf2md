import SwiftUI
import WebKit
import BookMDReaderCore

struct BookMDWebProgress: Equatable {
    let blockId: String
    let scrollY: Int
    let scrollX: Int
    let pageIndex: Int
    let pageCount: Int
}

struct BookMDWebView: UIViewRepresentable {
    let markdown: String
    let config: ReadingConfig
    let targetBlockId: String?
    let restoredProgress: ReadingProgress?
    let onSourceMapRequested: (String) -> Void
    let onProgressChanged: (BookMDWebProgress) -> Void

    func makeCoordinator() -> Coordinator {
        Coordinator(self)
    }

    func makeUIView(context: Context) -> WKWebView {
        let controller = WKUserContentController()
        controller.add(context.coordinator, name: "sourceMapRequested")
        controller.add(context.coordinator, name: "progressChanged")
        controller.addUserScript(WKUserScript(
            source: Self.bridgeScript,
            injectionTime: .atDocumentStart,
            forMainFrameOnly: true
        ))

        let configuration = WKWebViewConfiguration()
        configuration.userContentController = controller

        let webView = WKWebView(frame: .zero, configuration: configuration)
        webView.accessibilityIdentifier = "reader.webview"
        webView.navigationDelegate = context.coordinator
        webView.isOpaque = false
        webView.scrollView.contentInsetAdjustmentBehavior = .never
        let tapRecognizer = UITapGestureRecognizer(target: context.coordinator, action: #selector(Coordinator.handleTap(_:)))
        tapRecognizer.cancelsTouchesInView = false
        tapRecognizer.delegate = context.coordinator
        webView.addGestureRecognizer(tapRecognizer)
        let scrollTapRecognizer = UITapGestureRecognizer(
            target: context.coordinator,
            action: #selector(Coordinator.handleTap(_:))
        )
        scrollTapRecognizer.cancelsTouchesInView = false
        scrollTapRecognizer.delegate = context.coordinator
        webView.scrollView.addGestureRecognizer(scrollTapRecognizer)
        context.coordinator.loadShell(in: webView)
        return webView
    }

    func updateUIView(_ webView: WKWebView, context: Context) {
        context.coordinator.parent = self
        context.coordinator.pendingMarkdown = markdown
        context.coordinator.loadChapterIfReady(in: webView)
    }

    static func dismantleUIView(_ webView: WKWebView, coordinator: Coordinator) {
        webView.stopLoading()
        webView.navigationDelegate = nil
        webView.configuration.userContentController.removeScriptMessageHandler(forName: "sourceMapRequested")
        webView.configuration.userContentController.removeScriptMessageHandler(forName: "progressChanged")
    }

    final class Coordinator: NSObject, WKNavigationDelegate, WKScriptMessageHandler, UIGestureRecognizerDelegate {
        var parent: BookMDWebView
        var isReady = false
        var pendingMarkdown = ""
        private var lastLoadedMarkdown = ""
        private var lastConfigSignature = ""
        private var lastAppliedTargetBlockId: String?
        private var lastAppliedProgressSignature: String?

        init(_ parent: BookMDWebView) {
            self.parent = parent
        }

        func loadShell(in webView: WKWebView) {
            let html = Self.rendererHTML()
            webView.loadHTMLString(html, baseURL: Bundle.main.resourceURL)
        }

        func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
            isReady = true
            loadChapterIfReady(in: webView)
        }

        func webView(
            _ webView: WKWebView,
            decidePolicyFor navigationAction: WKNavigationAction,
            decisionHandler: @escaping (WKNavigationActionPolicy) -> Void
        ) {
            if let scheme = navigationAction.request.url?.scheme?.lowercased(),
               scheme == "bookmd-source" {
                if let blockId = navigationAction.request.url?.host?.removingPercentEncoding, !blockId.isEmpty {
                    parent.onSourceMapRequested(blockId)
                }
                decisionHandler(.cancel)
                return
            }
            if let scheme = navigationAction.request.url?.scheme?.lowercased(),
               scheme == "http" || scheme == "https" {
                decisionHandler(.cancel)
                return
            }
            decisionHandler(.allow)
        }

        func loadChapterIfReady(in webView: WKWebView) {
            let configSignature = Self.configSignature(parent.config)
            guard isReady, !pendingMarkdown.isEmpty else { return }
            let needsReload = pendingMarkdown != lastLoadedMarkdown || configSignature != lastConfigSignature
            guard needsReload else {
                applyPendingPosition(in: webView, force: false)
                return
            }

            lastLoadedMarkdown = pendingMarkdown
            lastConfigSignature = configSignature

            let payload: [String: Any] = [
                "markdown": pendingMarkdown,
                "config": [
                    "font_size": parent.config.fontSize,
                    "line_height": parent.config.lineHeight,
                    "theme": parent.config.theme,
                    "layout": parent.config.layout,
                    "language_mode": parent.config.defaultMode,
                    "native_source_links": true,
                ],
            ]
            guard let json = Self.jsonLiteral(payload) else { return }
            webView.evaluateJavaScript("window.BookMDReader.loadChapter(\(json));") { [weak self, weak webView] _, _ in
                guard let self, let webView else { return }
                self.applyPendingPosition(in: webView, force: true)
            }
        }

        private func applyPendingPosition(in webView: WKWebView, force: Bool) {
            if let target = parent.targetBlockId, !target.isEmpty {
                guard force || target != lastAppliedTargetBlockId else { return }
                lastAppliedTargetBlockId = target
                lastAppliedProgressSignature = nil
                webView.evaluateJavaScript("window.BookMDReader.jumpToBlock(\(Self.quoted(target)));")
                return
            }

            lastAppliedTargetBlockId = nil
            guard let progress = parent.restoredProgress else { return }
            let progressSignature = [
                progress.chapterPath,
                progress.blockId,
                "\(progress.scrollY)",
                "\(progress.scrollX)",
                "\(progress.pageIndex)",
                "\(progress.pageCount)",
            ].joined(separator: "|")
            guard force || progressSignature != lastAppliedProgressSignature else { return }
            lastAppliedProgressSignature = progressSignature
            let restore: [String: Any] = [
                "block_id": progress.blockId,
                "scroll_y": progress.scrollY,
                "scroll_x": progress.scrollX,
                "page_index": progress.pageIndex,
                "page_count": progress.pageCount,
            ]
            if let restoreJSON = Self.jsonLiteral(restore) {
                webView.evaluateJavaScript("window.BookMDReader.restoreProgress(\(restoreJSON));")
            }
        }

        func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
            switch message.name {
            case "sourceMapRequested":
                if let blockId = message.body as? String {
                    parent.onSourceMapRequested(blockId)
                }
            case "progressChanged":
                guard let body = message.body as? [String: Any] else { return }
                parent.onProgressChanged(BookMDWebProgress(
                    blockId: body["block_id"] as? String ?? "",
                    scrollY: Self.intValue(body["scroll_y"]),
                    scrollX: Self.intValue(body["scroll_x"]),
                    pageIndex: Self.intValue(body["page_index"]),
                    pageCount: Self.intValue(body["page_count"])
                ))
            default:
                break
            }
        }

        @objc func handleTap(_ recognizer: UITapGestureRecognizer) {
            guard recognizer.state == .ended else { return }
            let webView: WKWebView?
            if let directWebView = recognizer.view as? WKWebView {
                webView = directWebView
            } else {
                webView = recognizer.view?.superview as? WKWebView
            }
            guard let webView else { return }
            let point = recognizer.location(in: webView)
            let script = "window.BookMDReader.blockIdAtPoint(\(Double(point.x)), \(Double(point.y)));"
            webView.evaluateJavaScript(script) { [weak self] result, _ in
                guard let self, let blockId = result as? String, !blockId.isEmpty else { return }
                self.parent.onSourceMapRequested(blockId)
            }
        }

        func gestureRecognizer(
            _ gestureRecognizer: UIGestureRecognizer,
            shouldRecognizeSimultaneouslyWith otherGestureRecognizer: UIGestureRecognizer
        ) -> Bool {
            true
        }

        private static func rendererHTML() -> String {
            let css = resourceText("bookmd-renderer", extension: "css")
            let js = resourceText("bookmd-renderer", extension: "js")
            return """
            <!doctype html>
            <html lang="zh-CN">
            <head>
              <meta charset="utf-8">
              <meta name="viewport" content="width=device-width, initial-scale=1">
              <style>\(css)</style>
            </head>
            <body>
              <main id="bookmd-content" class="bookmd-content" data-layout="paged"></main>
              <script>\(js)</script>
            </body>
            </html>
            """
        }

        private static func resourceText(_ name: String, extension ext: String) -> String {
            let url = Bundle.main.url(forResource: name, withExtension: ext, subdirectory: "renderer")
                ?? Bundle.main.url(forResource: name, withExtension: ext)
            guard let url, let text = try? String(contentsOf: url, encoding: .utf8) else {
                return ""
            }
            return text
        }

        private static func jsonLiteral(_ value: Any) -> String? {
            guard JSONSerialization.isValidJSONObject(value),
                  let data = try? JSONSerialization.data(withJSONObject: value),
                  let text = String(data: data, encoding: .utf8)
            else {
                return nil
            }
            return text
        }

        private static func quoted(_ value: String) -> String {
            let data = try? JSONSerialization.data(withJSONObject: [value])
            let array = data.flatMap { String(data: $0, encoding: .utf8) } ?? "[\"\"]"
            return String(array.dropFirst().dropLast())
        }

        private static func intValue(_ value: Any?) -> Int {
            if let value = value as? Int {
                return value
            }
            if let value = value as? NSNumber {
                return value.intValue
            }
            if let value = value as? Double {
                return Int(value)
            }
            if let value = value as? String, let parsed = Int(value) {
                return parsed
            }
            return 0
        }

        private static func configSignature(_ config: ReadingConfig) -> String {
            [
                "\(config.fontSize)",
                "\(config.lineHeight)",
                config.theme,
                config.layout,
                config.defaultMode,
            ].joined(separator: "|")
        }
    }

    static let bridgeScript = """
    window.AndroidBookMD = {
      onSourceMapRequested: function(blockId) {
        window.webkit.messageHandlers.sourceMapRequested.postMessage(blockId || "");
      },
      onBlockSelected: function(blockId) {
        window.webkit.messageHandlers.sourceMapRequested.postMessage(blockId || "");
      },
      onImageSelected: function(src) {},
      onReadingProgressChanged: function(blockId, scrollY) {
        window.webkit.messageHandlers.progressChanged.postMessage({
          block_id: blockId || "",
          scroll_y: scrollY || 0,
          scroll_x: 0,
          page_index: 0,
          page_count: 0
        });
      },
      onReadingProgressChangedPayload: function(payload) {
        try {
          window.webkit.messageHandlers.progressChanged.postMessage(JSON.parse(payload || "{}"));
        } catch (error) {
          window.webkit.messageHandlers.progressChanged.postMessage({
            block_id: "",
            scroll_y: 0,
            scroll_x: 0,
            page_index: 0,
            page_count: 0
          });
        }
      }
    };
    """
}
