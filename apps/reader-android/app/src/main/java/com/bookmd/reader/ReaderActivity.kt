package com.bookmd.reader

import android.annotation.SuppressLint
import android.app.Activity
import android.os.Bundle
import android.webkit.WebView
import android.webkit.WebViewClient
import com.bookmd.reader.data.BookRepository
import com.bookmd.reader.data.ReadingProgress
import com.bookmd.reader.data.ReadingProgressStore
import com.bookmd.reader.settings.ReaderSettings
import com.bookmd.reader.web.BookMdWebBridge
import java.io.File
import org.json.JSONObject

class ReaderActivity : Activity() {
    private lateinit var webView: WebView
    private lateinit var repository: BookRepository
    private lateinit var progressStore: ReadingProgressStore
    private lateinit var bookDir: File
    private lateinit var chapterPath: String
    private var targetBlockId: String = ""
    private lateinit var settings: ReaderSettings

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        repository = BookRepository(filesDir)
        progressStore = ReadingProgressStore(this)
        bookDir = File(requireNotNull(intent.getStringExtra(EXTRA_BOOK_DIR)))
        chapterPath = requireNotNull(intent.getStringExtra(EXTRA_CHAPTER_PATH))
        targetBlockId = intent.getStringExtra(EXTRA_TARGET_BLOCK_ID) ?: ""
        settings = ReaderSettings.load(this, readBookDefaults())
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
        val progress = progressStore.readProgress(progressKey())
        val payload = JSONObject()
            .put("markdown", markdown)
            .put(
                "config",
                JSONObject()
                    .put("font_size", settings.fontSize)
                    .put("line_height", settings.lineHeight)
                    .put("theme", settings.theme)
                    .put("layout", settings.layout)
                    .put("language_mode", settings.languageMode)
            )
        webView.evaluateJavascript("window.BookMDReader.loadChapter($payload);", null)
        if (targetBlockId.isNotBlank()) {
            webView.evaluateJavascript(
                "window.BookMDReader.jumpToBlock(${JSONObject.quote(targetBlockId)});",
                null,
            )
        } else if (progress.chapterPath == chapterPath) {
            val restorePayload = JSONObject()
                .put("block_id", progress.blockId)
                .put("scroll_y", progress.scrollY)
            webView.evaluateJavascript(
                "window.BookMDReader.restoreProgress($restorePayload);",
                null,
            )
        }
    }

    override fun onPause() {
        super.onPause()
        if (!::webView.isInitialized || !::chapterPath.isInitialized) return
        webView.evaluateJavascript("window.BookMDReader.currentProgress();") { value ->
            val progress = parseProgress(value)
            progressStore.saveProgress(progressKey(), progress)
        }
    }

    private fun rewriteAssetPaths(markdown: String): String {
        val assetBase = "file://${bookDir.absolutePath}/assets/"
        return markdown.replace("../assets/", assetBase)
    }

    private fun readBookDefaults(): ReaderSettings {
        val configFile = File(bookDir, "reading_config.json")
        if (!configFile.exists()) return ReaderSettings()
        val config = JSONObject(configFile.readText())
        return ReaderSettings(
            fontSize = config.optInt("font_size", 18),
            lineHeight = config.optDouble("line_height", 1.75),
            theme = config.optString("theme", "light"),
            layout = config.optString("layout", "paged"),
            languageMode = config.optString("default_mode", "zh"),
        )
    }

    private fun parseProgress(value: String?): ReadingProgress {
        val progress = runCatching {
            JSONObject(value ?: "{}")
        }.getOrElse { JSONObject() }
        return ReadingProgress(
            chapterPath = chapterPath,
            blockId = progress.optString("block_id", ""),
            scrollY = progress.optInt("scroll_y", 0),
        )
    }

    private fun progressKey(): String = "${bookDir.name}:$chapterPath"
}
