package com.bookmd.reader

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.text.TextUtils
import android.util.Log
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import com.bookmd.reader.data.BookChapter
import com.bookmd.reader.data.BookRepository
import com.bookmd.reader.data.ReadingProgress
import com.bookmd.reader.data.ReadingProgressStore
import com.bookmd.reader.data.ReaderLogStore
import java.io.File

class BookShelfActivity : Activity() {
    private lateinit var repository: BookRepository
    private lateinit var progressStore: ReadingProgressStore
    private lateinit var logStore: ReaderLogStore
    private lateinit var list: LinearLayout
    private lateinit var listScroll: ScrollView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        repository = BookRepository(filesDir)
        progressStore = ReadingProgressStore(this)
        logStore = ReaderLogStore(this)
        if (launchVisualAssetSmokeIfRequested()) return
        list = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        listScroll = ScrollView(this)
        listScroll.addView(list)
        setContentView(
            LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(32, 32, 32, 32)
                addView(Button(this@BookShelfActivity).apply {
                    text = "Import .bookmd"
                    setOnClickListener {
                        startActivity(Intent(this@BookShelfActivity, BookImportActivity::class.java))
                    }
                })
                addView(Button(this@BookShelfActivity).apply {
                    text = "Logs"
                    setOnClickListener {
                        startActivity(Intent(this@BookShelfActivity, LogActivity::class.java))
                    }
                })
                addView(
                    listScroll,
                    LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f),
                )
            }
        )
    }

    override fun onNewIntent(intent: Intent?) {
        super.onNewIntent(intent)
        if (intent != null) {
            setIntent(intent)
            launchVisualAssetSmokeIfRequested()
        }
    }

    private fun launchVisualAssetSmokeIfRequested(): Boolean {
        val requested = intent.getBooleanExtra(SMOKE_VISUAL_ASSET, false)
        if (!requested) return false
        if (!BuildConfig.DEBUG) {
            Log.w("BookMDSmoke", "visual asset smoke rejected outside debug build")
            return false
        }
        val rawBookDir = intent.getStringExtra(EXTRA_BOOK_DIR).orEmpty()
        val rawMediaUri = intent.getStringExtra(EXTRA_MEDIA_URI).orEmpty()
        val bookDir = runCatching { File(rawBookDir).canonicalFile }.getOrNull()
        val filesRoot = runCatching { filesDir.canonicalFile }.getOrNull()
        val mediaFile = runCatching { File(Uri.parse(rawMediaUri).path.orEmpty()).canonicalFile }.getOrNull()
        val assetsRoot = bookDir?.resolve("assets")?.canonicalFile
        if (
            bookDir != null &&
            filesRoot != null &&
            mediaFile != null &&
            assetsRoot != null &&
            isInside(bookDir, filesRoot) &&
            isInside(mediaFile, assetsRoot) &&
            mediaFile.isFile
        ) {
            startActivity(Intent(this, ImageViewerActivity::class.java).apply {
                putExtra(EXTRA_BOOK_DIR, bookDir.absolutePath)
                putExtra(EXTRA_MEDIA_URI, rawMediaUri)
                putExtra("media_uri", rawMediaUri)
            })
        } else {
            Log.w(
                "BookMDSmoke",
                "visual asset smoke rejected: bookDir=$bookDir filesRoot=$filesRoot mediaFile=$mediaFile assetsRoot=$assetsRoot exists=${mediaFile?.isFile}",
            )
        }
        finish()
        return true
    }

    private fun isInside(path: File, root: File): Boolean {
        val pathValue = path.absolutePath
        val rootValue = root.absolutePath
        return pathValue == rootValue || pathValue.startsWith(rootValue + File.separator)
    }

    override fun onResume() {
        super.onResume()
        refreshBooks()
    }

    private fun refreshBooks() {
        list.removeAllViews()
        val books = repository.listBooks()
        if (books.isEmpty()) {
            list.addView(emptyShelfText())
            return
        }
        books.forEach { bookDir ->
            val manifest = repository.readManifestOrNull(bookDir)
            if (manifest == null) {
                list.addView(unavailableBookRow(bookDir))
                return@forEach
            }
            val progress = progressStore.readProgress(bookDir.name)
            list.addView(LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(0, 28, 0, 28)
                addView(TextView(this@BookShelfActivity).apply {
                    text = displayBookTitle(manifest.title.ifBlank { bookDir.name })
                    textSize = 20f
                    applyShelfTextOverflow()
                    setOnClickListener {
                        openBook(bookDir, manifest.chapters)
                    }
                })
                addView(TextView(this@BookShelfActivity).apply {
                    text = formatLastRead(progress)
                    textSize = 14f
                    applyShelfTextOverflow()
                })
                addView(TextView(this@BookShelfActivity).apply {
                    text = formatChapterProgress(manifest.chapters, progress)
                    textSize = 14f
                    applyShelfTextOverflow()
                })
                addView(Button(this@BookShelfActivity).apply {
                    text = "TOC"
                    setOnClickListener {
                        openToc(bookDir)
                    }
                })
                addView(Button(this@BookShelfActivity).apply {
                    text = "Delete"
                    setOnClickListener {
                        confirmDeleteBook(bookDir)
                    }
                })
            })
        }
    }

    private fun displayBookTitle(title: String): String {
        return title
            .replace("\n", " ")
            .replace("\r", " ")
    }

    private fun displayBookName(bookDir: File): String {
        return displayBookTitle(bookDir.name)
    }

    private fun unavailableBookRow(bookDir: File): LinearLayout {
        return LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(0, 28, 0, 28)
            addView(TextView(this@BookShelfActivity).apply {
                text = "Book unavailable: ${displayBookName(bookDir)}"
                textSize = 20f
                applyShelfTextOverflow()
            })
            addView(Button(this@BookShelfActivity).apply {
                text = "Delete"
                setOnClickListener {
                    confirmDeleteBook(bookDir)
                }
            })
        }
    }

    private fun emptyShelfText(): TextView {
        return TextView(this).apply {
            text = "No local books yet. Import a .bookmd package to start reading."
            textSize = 18f
            setPadding(0, 24, 0, 24)
        }
    }

    private fun confirmDeleteBook(bookDir: File) {
        AlertDialog.Builder(this)
            .setTitle("Delete book?")
            .setMessage("Delete ${displayBookName(bookDir)} from this device?")
            .setPositiveButton("Delete") { _, _ ->
                deleteBook(bookDir)
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun deleteBook(bookDir: File) {
        val bookName = displayBookName(bookDir)
        val deleted = repository.deleteBook(bookDir)
        if (deleted) {
            progressStore.clearBookProgress(bookDir.name)
        }
        logStore.append("delete", if (deleted) "Deleted $bookName" else "Delete failed: $bookName")
        refreshBooks()
    }

    private fun formatLastRead(progress: ReadingProgress): String {
        if (progress.updatedAtMillis <= 0L) return "Last read: never"
        val chapter = displayProgressChapterName(progress.chapterPath)
        return "Last read: $chapter · ${formatPageProgress(progress)}"
    }

    private fun displayProgressChapterName(chapterPath: String): String {
        return chapterPath
            .substringAfterLast('/')
            .ifBlank { chapterPath }
            .replace("\n", " ")
            .replace("\r", " ")
    }

    private fun formatPageProgress(progress: ReadingProgress): String {
        if (progress.pageCount > 1) {
            return "Page ${progress.pageIndex + 1}/${progress.pageCount}"
        }
        return "Scroll ${progress.scrollY}"
    }

    private fun formatChapterProgress(chapters: List<BookChapter>, progress: ReadingProgress): String {
        val chapterIndex = chapters.indexOfFirst { it.path == progress.chapterPath }
        if (chapterIndex < 0 || chapters.isEmpty()) return "Not started"
        return "Chapter ${chapterIndex + 1}/${chapters.size}"
    }

    private fun openBook(bookDir: File, chapters: List<BookChapter>) {
        val lastProgress = progressStore.readProgress(bookDir.name)
        val lastChapter = chapters.firstOrNull { it.path == lastProgress.chapterPath }
        if (lastChapter != null && repository.chapterFileExists(bookDir, lastChapter.path)) {
            startActivity(Intent(this, ReaderActivity::class.java).apply {
                putExtra(EXTRA_BOOK_DIR, bookDir.absolutePath)
                putExtra(EXTRA_CHAPTER_ID, lastChapter.id)
                putExtra(EXTRA_CHAPTER_PATH, lastChapter.path)
            })
            return
        }
        openToc(bookDir)
    }

    private fun openToc(bookDir: File) {
        startActivity(Intent(this, TocActivity::class.java).apply {
            putExtra(EXTRA_BOOK_DIR, bookDir.absolutePath)
        })
    }

    private fun TextView.applyShelfTextOverflow(lineLimit: Int = 2) {
        maxLines = lineLimit
        ellipsize = TextUtils.TruncateAt.END
    }

    companion object {
        private const val SMOKE_VISUAL_ASSET = "smoke_visual_asset"
    }
}
