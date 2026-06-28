package com.bookmd.reader

import android.annotation.SuppressLint
import android.app.Activity
import android.os.Bundle
import android.webkit.WebView
import android.webkit.WebViewClient
import com.bookmd.reader.settings.ReaderSettings

class ReaderActivity : Activity() {
    private lateinit var webView: WebView
    private val settings = ReaderSettings()

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        webView = WebView(this)
        webView.webViewClient = WebViewClient()
        webView.settings.javaScriptEnabled = true
        webView.settings.allowFileAccess = true
        setContentView(webView)
        webView.loadUrl("file:///android_asset/bookmd-renderer.html")
    }
}
