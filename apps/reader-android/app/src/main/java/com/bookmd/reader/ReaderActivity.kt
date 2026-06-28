package com.bookmd.reader

import android.annotation.SuppressLint
import android.app.Activity
import android.os.Bundle
import android.webkit.WebView
import android.webkit.WebViewClient
import com.bookmd.reader.data.BookRepository
import com.bookmd.reader.settings.ReaderSettings
import com.bookmd.reader.web.BookMdWebBridge
import java.io.File
import org.json.JSONObject

class ReaderActivity : Activity() {
    private lateinit var webView: WebView
    private lateinit var repository: BookRepository
    private lateinit var bookDir: File
    private lateinit var chapterPath: String
    private var targetBlockId: String = ""
    private val settings = ReaderSettings()

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        repository = BookRepository(filesDir)
        bookDir = File(requireNotNull(intent.getStringExtra(EXTRA_BOOK_DIR)))
        chapterPath = requireNotNull(intent.getStringExtra(EXTRA_CHAPTER_PATH))
        targetBlockId = intent.getStringExtra(EXTRA_TARGET_BLOCK_ID) ?: ""
        webView = WebView(this)
        webView.webViewClient = object : WebViewClient() {
            override fun onPageFinished(view: WebView, url: String) {
                loadChapter()
            }
        }
        webView.settings.javaScriptEnabled = true
        webView.settings.allowFileAccess = true
        webView.addJavascriptInterface(BookMdWebBridge(this, bookDir), "AndroidBookMD")
        setContentView(webView)
        webView.loadUrl("file:///android_asset/bookmd-renderer.html")
    }

    private fun loadChapter() {
        val markdown = rewriteAssetPaths(repository.readChapterMarkdown(bookDir, chapterPath))
        val payload = JSONObject()
            .put("markdown", markdown)
            .put(
                "config",
                JSONObject()
                    .put("font_size", settings.fontSize)
                    .put("line_height", settings.lineHeight)
                    .put("theme", settings.theme)
                    .put("layout", settings.layout)
            )
        webView.evaluateJavascript("window.BookMDReader.loadChapter($payload);", null)
        if (targetBlockId.isNotBlank()) {
            webView.evaluateJavascript(
                "window.BookMDReader.jumpToBlock(${JSONObject.quote(targetBlockId)});",
                null,
            )
        }
    }

    private fun rewriteAssetPaths(markdown: String): String {
        val assetBase = "file://${bookDir.absolutePath}/assets/"
        return markdown.replace("../assets/", assetBase)
    }
}
