package com.bookmd.reader

import android.annotation.SuppressLint
import android.app.Activity
import android.net.Uri
import android.os.Bundle
import android.webkit.WebResourceRequest
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
        webView.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                return !isRendererUrl(request.url?.toString().orEmpty())
            }

            @Suppress("DEPRECATION")
            override fun shouldOverrideUrlLoading(view: WebView, url: String): Boolean {
                return !isRendererUrl(url)
            }
        }
        webView.settings.javaScriptEnabled = true
        webView.settings.allowFileAccess = true
        webView.settings.allowContentAccess = false
        webView.settings.allowFileAccessFromFileURLs = false
        webView.settings.allowUniversalAccessFromFileURLs = false
        setContentView(webView)
        webView.loadUrl(RENDERER_URL)
    }

    override fun onDestroy() {
        if (::webView.isInitialized) {
            webView.destroy()
        }
        super.onDestroy()
    }

    private fun isRendererUrl(url: String): Boolean {
        val normalized = runCatching {
            Uri.parse(url).buildUpon().fragment(null).build().toString()
        }.getOrDefault("")
        return normalized == RENDERER_URL
    }

    companion object {
        private const val RENDERER_URL = "file:///android_asset/bookmd-renderer.html"
    }
}
