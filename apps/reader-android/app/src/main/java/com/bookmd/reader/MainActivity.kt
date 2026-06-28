package com.bookmd.reader

import android.annotation.SuppressLint
import android.app.Activity
import android.os.Bundle
import android.webkit.WebView
import android.webkit.WebViewClient
import com.bookmd.reader.data.BookRepository

class MainActivity : Activity() {
    private lateinit var webView: WebView
    private lateinit var repository: BookRepository

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        repository = BookRepository(filesDir)
        webView = WebView(this)
        webView.webViewClient = WebViewClient()
        webView.settings.javaScriptEnabled = true
        webView.settings.allowFileAccess = true
        setContentView(webView)
        webView.loadUrl("file:///android_asset/bookmd-renderer.html")
    }
}
