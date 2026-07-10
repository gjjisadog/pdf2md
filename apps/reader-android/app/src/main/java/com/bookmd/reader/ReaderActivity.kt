package com.bookmd.reader

import android.annotation.SuppressLint
import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.net.Uri
import android.view.Gravity
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
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
    private var chapterId: String = ""
    private lateinit var chapterPath: String
    private var targetBlockId: String = ""
    private lateinit var settings: ReaderSettings
    private val progressHandler = Handler(Looper.getMainLooper())
    private var pendingProgress: ReadingProgress? = null
    private val progressFlushRunnable = Runnable { flushPendingProgress() }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        repository = BookRepository(filesDir)
        progressStore = ReadingProgressStore(this)
        val bookDirPath = intent.getStringExtra(EXTRA_BOOK_DIR)
        val requestedChapterPath = intent.getStringExtra(EXTRA_CHAPTER_PATH)
        if (bookDirPath.isNullOrBlank() || requestedChapterPath.isNullOrBlank()) {
            showReaderUnavailable()
            return
        }
        bookDir = File(bookDirPath)
        chapterId = intent.getStringExtra(EXTRA_CHAPTER_ID) ?: ""
        chapterPath = requestedChapterPath
        targetBlockId = intent.getStringExtra(EXTRA_TARGET_BLOCK_ID) ?: ""
        settings = ReaderSettings.load(this, readBookDefaultsOrDefault())
        webView = WebView(this)
        webView.webViewClient = object : WebViewClient() {
            override fun onPageFinished(view: WebView, url: String) {
                loadChapter()
            }

            override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                return !isReaderRendererUrl(request.url?.toString().orEmpty())
            }

            @Suppress("DEPRECATION")
            override fun shouldOverrideUrlLoading(view: WebView, url: String): Boolean {
                return !isReaderRendererUrl(url)
            }
        }
        webView.settings.javaScriptEnabled = true
        webView.settings.allowFileAccess = true
        webView.settings.allowContentAccess = false
        webView.settings.allowFileAccessFromFileURLs = false
        webView.settings.allowUniversalAccessFromFileURLs = false
        webView.addJavascriptInterface(
            BookMdWebBridge(this, bookDir) { blockId, scrollY, scrollX, pageIndex, pageCount ->
                saveReadingProgress(blockId, scrollY, scrollX, pageIndex, pageCount)
            },
            "AndroidBookMD",
        )
        setContentView(
            LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                addView(readerToolbar())
                addView(webView, LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT,
                    0,
                    1f,
                ))
            }
        )
        webView.loadUrl(READER_RENDERER_URL)
    }

    private fun showReaderUnavailable() {
        setContentView(TextView(this).apply {
            text = "Reader unavailable."
            textSize = 18f
            setPadding(32, 32, 32, 32)
            gravity = Gravity.CENTER_VERTICAL
        })
    }

    private fun readerToolbar(): LinearLayout {
        return LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            addView(readerToolbarRow("TOC", "Prev", "Next"))
            addView(readerToolbarRow("Search", "Settings"))
        }
    }

    private fun readerToolbarRow(vararg labels: String): LinearLayout {
        return LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            labels.forEach { label ->
                addView(
                    readerToolbarButton(label),
                    LinearLayout.LayoutParams(
                        0,
                        LinearLayout.LayoutParams.WRAP_CONTENT,
                        1f,
                    ),
                )
            }
        }
    }

    private fun readerToolbarButton(label: String): Button {
        return Button(this).apply {
            text = label
            setAllCaps(false)
            maxLines = 1
            when (label) {
                "Prev" -> isEnabled = hasAdjacentChapter(-1)
                "Next" -> isEnabled = hasAdjacentChapter(1)
            }
            setOnClickListener {
                when (label) {
                    "TOC" -> startActivity(Intent(this@ReaderActivity, TocActivity::class.java).apply {
                        putExtra(EXTRA_BOOK_DIR, bookDir.absolutePath)
                        putExtra(EXTRA_CURRENT_CHAPTER_PATH, chapterPath)
                    })
                    "Prev" -> openAdjacentChapter(-1)
                    "Next" -> openAdjacentChapter(1)
                    "Search" -> startActivity(Intent(this@ReaderActivity, SearchActivity::class.java).apply {
                        putExtra(EXTRA_BOOK_DIR, bookDir.absolutePath)
                    })
                    "Settings" -> startActivity(Intent(this@ReaderActivity, SettingsActivity::class.java))
                }
            }
        }
    }

    private fun hasAdjacentChapter(offset: Int): Boolean {
        val chapters = repository.readManifestOrNull(bookDir)?.chapters ?: return false
        val currentIndex = chapters.indexOfFirst { it.path == chapterPath }
        return currentIndex >= 0 && chapters.getOrNull(currentIndex + offset) != null
    }

    private fun openAdjacentChapter(offset: Int) {
        val chapters = repository.readManifestOrNull(bookDir)?.chapters ?: return
        val currentIndex = chapters.indexOfFirst { it.path == chapterPath }
        if (currentIndex < 0) return
        val target = chapters.getOrNull(currentIndex + offset) ?: return
        startActivity(Intent(this, ReaderActivity::class.java).apply {
            putExtra(EXTRA_BOOK_DIR, bookDir.absolutePath)
            putExtra(EXTRA_CHAPTER_ID, target.id)
            putExtra(EXTRA_CHAPTER_PATH, target.path)
        })
        finish()
    }

    private fun loadChapter() {
        val markdown = repository.readChapterMarkdownOrNull(bookDir, chapterPath)
            ?.let { rewriteAssetPaths(it) }
            ?: chapterUnavailableMarkdown(chapterPath)
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
                .put("scroll_x", progress.scrollX)
                .put("page_index", progress.pageIndex)
                .put("page_count", progress.pageCount)
            webView.evaluateJavascript(
                "window.BookMDReader.restoreProgress($restorePayload);",
                null,
            )
        }
    }

    private fun chapterUnavailableMarkdown(path: String): String {
        val safePath = safeMarkdownInlineCodeText(path.ifBlank { "unknown chapter" })
        return "# Chapter unavailable\n\nUnable to open `$safePath`."
    }

    private fun safeMarkdownInlineCodeText(text: String): String {
        return text
            .replace("`", "'")
            .replace("\n", " ")
            .replace("\r", " ")
    }

    override fun onResume() {
        super.onResume()
        if (!::webView.isInitialized || !::chapterPath.isInitialized) return
        val updatedSettings = ReaderSettings.load(this, readBookDefaultsOrDefault())
        if (updatedSettings != settings) {
            settings = updatedSettings
            loadChapter()
        }
    }

    override fun onPause() {
        super.onPause()
        if (!::webView.isInitialized || !::chapterPath.isInitialized) return
        webView.evaluateJavascript("window.BookMDReader.currentProgress();") { value ->
            pendingProgress = parseProgress(value)
            flushPendingProgress()
        }
    }

    override fun onDestroy() {
        flushPendingProgress()
        progressHandler.removeCallbacks(progressFlushRunnable)
        if (::webView.isInitialized) {
            webView.destroy()
        }
        super.onDestroy()
    }

    private fun rewriteAssetPaths(markdown: String): String {
        var inCodeFence = false
        return markdown.lineSequence().map { line ->
            if (isCodeFenceDelimiter(line)) {
                inCodeFence = !inCodeFence
                line
            } else {
                if (inCodeFence) line else rewriteSafeMarkdownLine(line)
            }
        }.joinToString("\n")
    }

    private fun isCodeFenceDelimiter(line: String): Boolean {
        val trimmed = line.trimStart()
        return trimmed.startsWith("```") || trimmed.startsWith("~~~")
    }

    private fun rewriteSafeMarkdownLine(line: String): String {
        var inlineCodeDelimiterLength = 0
        val result = StringBuilder()
        val current = StringBuilder()

        fun appendSegment() {
            val segment = current.toString()
            result.append(if (inlineCodeDelimiterLength > 0) segment else rewriteSafeMarkdownSegment(segment))
            current.clear()
        }

        var index = 0
        while (index < line.length) {
            if (line[index] == '`') {
                val delimiterLength = countBacktickRun(line, index)
                appendSegment()
                result.append(line.substring(index, index + delimiterLength))
                if (inlineCodeDelimiterLength == 0) {
                    inlineCodeDelimiterLength = delimiterLength
                } else if (delimiterLength == inlineCodeDelimiterLength) {
                    inlineCodeDelimiterLength = 0
                }
                index += delimiterLength
            } else {
                current.append(line[index])
                index += 1
            }
        }
        appendSegment()
        return result.toString()
    }

    private fun countBacktickRun(line: String, start: Int): Int {
        var end = start
        while (end < line.length && line[end] == '`') {
            end += 1
        }
        return end - start
    }

    private fun rewriteSafeMarkdownSegment(segment: String): String {
        val rewrittenMarkdownAssets = rewriteMarkdownAssetPaths(segment)
        val rewrittenHtmlAssets = rewriteHtmlAssetSrcValues(rewrittenMarkdownAssets)
        return MEDIA_SRC_PATTERN.replace(rewrittenHtmlAssets) { match ->
            val safeUri = safeMediaUri(decodeHtmlAssetPath(mediaSourceFromMatch(match)))
            "src=\"$safeUri\""
        }
    }

    private fun rewriteMarkdownAssetPaths(segment: String): String {
        val rewrittenAngleAssets = ANGLE_MARKDOWN_ASSET_PATH_PATTERN.replace(segment) { match ->
            rewriteMarkdownAssetMatch(match)
        }
        return MARKDOWN_ASSET_PATH_PATTERN.replace(rewrittenAngleAssets) { match ->
            rewriteMarkdownAssetMatch(match)
        }
    }

    private fun rewriteMarkdownAssetMatch(match: MatchResult): String {
        val source = match.groupValues[1]
        val title = match.groupValues[2]
        val assetPath = unescapeMarkdownAssetPath(source.removePrefix("../assets/"))
        val safeUri = safeAssetUri(assetPath)
        if (safeUri.isBlank()) return "]()"
        return "]($safeUri$title)"
    }

    private fun unescapeMarkdownAssetPath(path: String): String {
        return path
            .replace("\\(", "(")
            .replace("\\)", ")")
    }

    private fun rewriteHtmlAssetSrcValues(segment: String): String {
        return HTML_ASSET_SRC_PATTERN.replace(segment) { match ->
            val source = htmlAssetSourceFromMatch(match)
            val safeUri = safeAssetUri(decodeHtmlAssetPath(source).removePrefix("../assets/"))
            "src=\"$safeUri\""
        }
    }

    private fun decodeHtmlAssetPath(path: String): String {
        val decodedNamedEntities = HTML_NAMED_ENTITY_PATTERN.replace(path) { match ->
            when (match.groupValues[1].lowercase()) {
                "amp" -> "&"
                "quot" -> "\""
                "apos" -> "'"
                "lt" -> "<"
                "gt" -> ">"
                else -> match.value
            }
        }.replace("&#39;", "'")
        return HTML_NUMERIC_ENTITY_PATTERN.replace(decodedNamedEntities) { match ->
            val codePoint = if (match.groupValues[1].isNotBlank()) {
                match.groupValues[1].toIntOrNull(16)
            } else {
                match.groupValues[2].toIntOrNull(10)
            }
            if (codePoint == null) return@replace match.value
            runCatching {
                Character.toChars(codePoint).concatToString()
            }.getOrDefault(match.value)
        }
    }

    private fun htmlAssetSourceFromMatch(match: MatchResult): String {
        return match.groupValues.drop(1).firstOrNull { it.isNotBlank() }.orEmpty()
    }

    private fun mediaSourceFromMatch(match: MatchResult): String {
        return match.groupValues.drop(1).firstOrNull { it.isNotBlank() }.orEmpty()
    }

    private fun safeAssetUri(assetPath: String): String {
        return runCatching {
            val assetRoot = File(bookDir, "assets").canonicalFile
            val decodedAssetPath = Uri.decode(assetPath)
            val assetFile = File(assetRoot, decodedAssetPath).canonicalFile
            val isInsideAssets = assetFile.path == assetRoot.path || assetFile.path.startsWith(assetRoot.path + File.separator)
            if (!isInsideAssets || !assetFile.isFile) return ""
            assetFile.toURI().toString()
        }.getOrDefault("")
    }

    private fun safeMediaUri(mediaUri: String): String {
        return runCatching {
            val uri = Uri.parse(mediaUri)
            if (uri.scheme != "file") return ""
            val assetRoot = File(bookDir, "assets").canonicalFile
            val mediaFile = File(uri.path ?: return "").canonicalFile
            val isInsideAssets = mediaFile.path == assetRoot.path || mediaFile.path.startsWith(assetRoot.path + File.separator)
            if (!isInsideAssets || !mediaFile.isFile) return ""
            mediaFile.toURI().toString()
        }.getOrDefault("")
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

    private fun readBookDefaultsOrDefault(): ReaderSettings {
        return runCatching { readBookDefaults() }.getOrElse { ReaderSettings() }
    }

    private fun parseProgress(value: String?): ReadingProgress {
        val progress = runCatching {
            JSONObject(value ?: "{}")
        }.getOrElse { JSONObject() }
        val pageCount = nonNegativeProgressValue(progress.optInt("page_count", 0))
        return ReadingProgress(
            chapterPath = chapterPath,
            blockId = progress.optString("block_id", ""),
            scrollY = nonNegativeProgressValue(progress.optInt("scroll_y", 0)),
            scrollX = nonNegativeProgressValue(progress.optInt("scroll_x", 0)),
            pageIndex = normalizedPageIndex(progress.optInt("page_index", 0), pageCount),
            pageCount = pageCount,
        )
    }

    private fun nonNegativeProgressValue(value: Int): Int {
        return value.coerceAtLeast(0)
    }

    private fun normalizedPageIndex(pageIndex: Int, pageCount: Int): Int {
        if (pageCount <= 0) return 0
        return nonNegativeProgressValue(pageIndex).coerceAtMost(pageCount - 1)
    }

    private fun saveReadingProgress(
        blockId: String,
        scrollY: Int,
        scrollX: Int = 0,
        pageIndex: Int = 0,
        pageCount: Int = 0,
    ) {
        val normalizedPageCount = nonNegativeProgressValue(pageCount)
        pendingProgress = ReadingProgress(
            chapterPath = chapterPath,
            blockId = blockId,
            scrollY = nonNegativeProgressValue(scrollY),
            scrollX = nonNegativeProgressValue(scrollX),
            pageIndex = normalizedPageIndex(pageIndex, normalizedPageCount),
            pageCount = normalizedPageCount,
        )
        scheduleProgressFlush()
    }

    private fun scheduleProgressFlush() {
        progressHandler.removeCallbacks(progressFlushRunnable)
        progressHandler.postDelayed(progressFlushRunnable, PROGRESS_FLUSH_DELAY_MS)
    }

    private fun flushPendingProgress() {
        progressHandler.removeCallbacks(progressFlushRunnable)
        val progress = pendingProgress ?: return
        progressStore.saveProgress(progressKey(), progress)
        progressStore.saveBookProgress(bookDir.name, progress)
        pendingProgress = null
    }

    private fun progressKey(): String = "${bookDir.name}:$chapterPath"

    private fun isReaderRendererUrl(url: String): Boolean {
        val normalized = runCatching {
            Uri.parse(url).buildUpon().fragment(null).build().toString()
        }.getOrDefault("")
        return normalized == READER_RENDERER_URL
    }

    companion object {
        private val HTML_NAMED_ENTITY_PATTERN = Regex("""&(amp|quot|apos|lt|gt);""", RegexOption.IGNORE_CASE)
        private val HTML_NUMERIC_ENTITY_PATTERN = Regex("""&#(?:x([0-9A-Fa-f]+)|([0-9]+));""")
        private val ANGLE_MARKDOWN_ASSET_PATH_PATTERN = Regex("""\]\(<(\.\./assets/[^>]+)>(\s+["'][^"']*["'])?\)""")
        private val MARKDOWN_ASSET_PATH_PATTERN = Regex("""\]\((\.\./assets/(?:\\\)|[^)])*?)(\s+["'][^"']*["'])?\)""")
        private val HTML_ASSET_SRC_PATTERN = Regex(
            """(?<![\w:-])src\s*=\s*(?:"(\.\./assets/[^"]+)"|'(\.\./assets/[^']+)'|(\.\./assets/[^\s>"']+))""",
            RegexOption.IGNORE_CASE,
        )
        private val MEDIA_SRC_PATTERN = Regex(
            """(?<![\w:-])src\s*=\s*(?:"([^"]+)"|'([^']+)'|([^\s>"']+))""",
            RegexOption.IGNORE_CASE,
        )
        private const val READER_RENDERER_URL = "file:///android_asset/bookmd-renderer.html"
        private const val PROGRESS_FLUSH_DELAY_MS = 1000L
    }
}
