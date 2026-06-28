package com.bookmd.reader

import android.app.Activity
import android.os.Bundle
import android.widget.TextView

class TocActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(TextView(this).apply { text = "Table of Contents" })
    }
}
