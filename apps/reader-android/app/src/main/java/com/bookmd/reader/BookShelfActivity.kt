package com.bookmd.reader

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import com.bookmd.reader.data.BookRepository

class BookShelfActivity : Activity() {
    private lateinit var repository: BookRepository
    private lateinit var list: LinearLayout

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        repository = BookRepository(filesDir)
        list = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
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
                addView(list)
            }
        )
    }

    override fun onResume() {
        super.onResume()
        refreshBooks()
    }

    private fun refreshBooks() {
        list.removeAllViews()
        val books = repository.listBooks()
        if (books.isEmpty()) {
            list.addView(TextView(this).apply { text = "No local books yet." })
            return
        }
        books.forEach { bookDir ->
            val manifest = repository.readManifest(bookDir)
            list.addView(TextView(this).apply {
                text = manifest.title.ifBlank { bookDir.name }
                textSize = 20f
                setPadding(0, 28, 0, 28)
                setOnClickListener {
                    startActivity(Intent(this@BookShelfActivity, TocActivity::class.java).apply {
                        putExtra(EXTRA_BOOK_DIR, bookDir.absolutePath)
                    })
                }
            })
        }
    }
}
