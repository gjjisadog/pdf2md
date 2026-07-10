package com.bookmd.reader

import android.app.Activity
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.os.Bundle
import android.text.TextUtils
import android.view.Gravity
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import com.bookmd.reader.data.BookChapter
import com.bookmd.reader.data.BookManifest
import com.bookmd.reader.data.BookRepository
import com.bookmd.reader.data.ReadingProgressStore
import java.io.File

class TocActivity : Activity() {
    private lateinit var repository: BookRepository
    private lateinit var progressStore: ReadingProgressStore
    private lateinit var bookDir: File
    private var currentChapterRow: TextView? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        currentChapterRow = null
        repository = BookRepository(filesDir)
        progressStore = ReadingProgressStore(this)
        val bookDirPath = intent.getStringExtra(EXTRA_BOOK_DIR)
        if (bookDirPath.isNullOrBlank()) {
            setContentView(statusText("Book unavailable."))
            return
        }
        bookDir = File(bookDirPath)
        val manifest = repository.readManifestOrNull(bookDir)
        if (manifest == null) {
            setContentView(statusText("Book unavailable."))
            return
        }
        val currentChapterPath = currentChapterPath()
        val scrollView = ScrollView(this)
        scrollView.addView(buildTocContent(manifest, currentChapterPath))
        setContentView(scrollView)
        scrollCurrentChapterIntoView(scrollView)
    }

    private fun buildTocContent(manifest: BookManifest, currentChapterPath: String): LinearLayout {
        return LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(32, 32, 32, 32)
                addView(TextView(this@TocActivity).apply {
                    text = displayBookTitle(manifest)
                    textSize = 22f
                })
                addView(Button(this@TocActivity).apply {
                    text = "Search"
                    setOnClickListener {
                        startActivity(Intent(this@TocActivity, SearchActivity::class.java).apply {
                            putExtra(EXTRA_BOOK_DIR, bookDir.absolutePath)
                        })
                    }
                })
                addView(Button(this@TocActivity).apply {
                    text = "Settings"
                    setOnClickListener {
                        startActivity(Intent(this@TocActivity, SettingsActivity::class.java))
                    }
                })
                manifest.chapters.forEach { chapter ->
                    addView(chapterRow(chapter, chapter.path == currentChapterPath))
                }
                if (manifest.chapters.isEmpty()) {
                    addView(statusText("No chapters available."))
                }
            }
    }

    private fun currentChapterPath(): String {
        val explicitPath = intent.getStringExtra(EXTRA_CURRENT_CHAPTER_PATH).orEmpty()
        return explicitPath.ifBlank {
            progressStore.readProgress(bookDir.name).chapterPath
        }
    }

    private fun chapterRow(chapter: BookChapter, isCurrent: Boolean): TextView {
        return TextView(this).apply {
            text = displayChapterTitle(chapter)
            textSize = if (isCurrent) 19f else 18f
            maxLines = 2
            ellipsize = TextUtils.TruncateAt.END
            setPadding(12, 24, 12, 24)
            if (isCurrent) {
                currentChapterRow = this
                setTypeface(typeface, Typeface.BOLD)
                setBackgroundColor(Color.rgb(232, 240, 254))
            }
            setOnClickListener {
                startActivity(Intent(this@TocActivity, ReaderActivity::class.java).apply {
                    putExtra(EXTRA_BOOK_DIR, bookDir.absolutePath)
                    putExtra(EXTRA_CHAPTER_ID, chapter.id)
                    putExtra(EXTRA_CHAPTER_PATH, chapter.path)
                })
            }
        }
    }

    private fun displayBookTitle(manifest: BookManifest): String {
        return flattenDisplayTitle(manifest.title.ifBlank { bookDir.name })
    }

    private fun displayChapterTitle(chapter: BookChapter): String {
        return flattenDisplayTitle(chapter.title.ifBlank {
            chapter.path.substringAfterLast('/').ifBlank {
                chapter.id.ifBlank { "Untitled chapter" }
            }
        })
    }

    private fun flattenDisplayTitle(title: String): String {
        return title
            .replace("\n", " ")
            .replace("\r", " ")
    }

    private fun statusText(message: String): TextView {
        return TextView(this).apply {
            text = message
            textSize = 18f
            setPadding(32, 32, 32, 32)
            gravity = Gravity.CENTER_VERTICAL
        }
    }

    private fun scrollCurrentChapterIntoView(scrollView: ScrollView) {
        val row = currentChapterRow ?: return
        scrollView.post {
            scrollView.smoothScrollTo(0, (row.top - CURRENT_CHAPTER_SCROLL_MARGIN_PX).coerceAtLeast(0))
        }
    }

    companion object {
        private const val CURRENT_CHAPTER_SCROLL_MARGIN_PX = 96
    }
}
