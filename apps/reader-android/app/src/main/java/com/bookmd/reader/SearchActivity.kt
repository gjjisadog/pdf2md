package com.bookmd.reader

import android.app.Activity
import android.os.Bundle
import android.widget.TextView
import com.bookmd.reader.data.SearchRepository

class SearchActivity : Activity() {
    private var repository: SearchRepository? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(TextView(this).apply { text = "Search BookMD" })
    }
}
