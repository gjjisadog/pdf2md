package com.bookmd.reader

import android.app.Activity
import android.os.Bundle
import android.widget.TextView
import com.bookmd.reader.data.BookRepository

class BookImportActivity : Activity() {
    private lateinit var repository: BookRepository

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        repository = BookRepository(filesDir)
        setContentView(TextView(this).apply { text = "Import local .bookmd" })
    }
}
