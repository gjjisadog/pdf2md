package com.bookmd.reader

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import com.bookmd.reader.data.BookRepository
import java.io.File

class TocActivity : Activity() {
    private lateinit var repository: BookRepository
    private lateinit var bookDir: File

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        repository = BookRepository(filesDir)
        bookDir = File(requireNotNull(intent.getStringExtra(EXTRA_BOOK_DIR)))
        val manifest = repository.readManifest(bookDir)
        setContentView(
            LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(32, 32, 32, 32)
                addView(TextView(this@TocActivity).apply {
                    text = manifest.title
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
                    addView(TextView(this@TocActivity).apply {
                        text = chapter.title
                        textSize = 18f
                        setPadding(0, 24, 0, 24)
                        setOnClickListener {
                            startActivity(Intent(this@TocActivity, ReaderActivity::class.java).apply {
                                putExtra(EXTRA_BOOK_DIR, bookDir.absolutePath)
                                putExtra(EXTRA_CHAPTER_ID, chapter.id)
                                putExtra(EXTRA_CHAPTER_PATH, chapter.path)
                            })
                        }
                    })
                }
            }
        )
    }
}
