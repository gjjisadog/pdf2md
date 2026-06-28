package com.bookmd.reader

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.TextView
import com.bookmd.reader.data.SearchRepository
import java.io.File

class SearchActivity : Activity() {
    private lateinit var repository: SearchRepository
    private lateinit var results: LinearLayout
    private lateinit var bookDir: File

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        bookDir = File(requireNotNull(intent.getStringExtra(EXTRA_BOOK_DIR)))
        repository = SearchRepository(bookDir)
        val query = EditText(this).apply { hint = "Search Chinese text" }
        results = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        setContentView(
            LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(32, 32, 32, 32)
                addView(query)
                addView(Button(this@SearchActivity).apply {
                    text = "Search"
                    setOnClickListener { renderResults(query.text.toString()) }
                })
                addView(results)
            }
        )
    }

    private fun renderResults(query: String) {
        results.removeAllViews()
        repository.search(query).forEach { result ->
            results.addView(TextView(this).apply {
                text = "${result.chapterTitle}\n${result.text}"
                setPadding(0, 20, 0, 20)
                setOnClickListener {
                    startActivity(Intent(this@SearchActivity, ReaderActivity::class.java).apply {
                        putExtra(EXTRA_BOOK_DIR, bookDir.absolutePath)
                        putExtra(EXTRA_CHAPTER_ID, result.chapterId)
                        putExtra(EXTRA_CHAPTER_PATH, result.chapterPath)
                        putExtra(EXTRA_TARGET_BLOCK_ID, result.blockId)
                        putExtra("target_block_id", result.blockId)
                    })
                }
            })
        }
    }
}
