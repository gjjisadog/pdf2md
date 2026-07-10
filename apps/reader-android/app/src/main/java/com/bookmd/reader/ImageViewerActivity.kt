package com.bookmd.reader

import android.annotation.SuppressLint
import android.app.Activity
import android.net.Uri
import android.os.Bundle
import android.webkit.WebView
import java.io.File

class ImageViewerActivity : Activity() {
    private lateinit var webView: WebView

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val rawMediaUri = intent.getStringExtra(EXTRA_MEDIA_URI) ?: intent.getStringExtra("media_uri") ?: ""
        val bookDirPath = intent.getStringExtra(EXTRA_BOOK_DIR).orEmpty()
        val mediaUri = normalizeMediaUri(rawMediaUri, bookDirPath)
        webView = WebView(this).apply {
            settings.allowFileAccess = true
            settings.allowContentAccess = false
            settings.allowFileAccessFromFileURLs = false
            settings.allowUniversalAccessFromFileURLs = false
            settings.javaScriptEnabled = false
            settings.setSupportZoom(true)
            settings.builtInZoomControls = true
            settings.displayZoomControls = false
            settings.useWideViewPort = true
            settings.loadWithOverviewMode = true
            setBackgroundColor(android.graphics.Color.WHITE)
            loadDataWithBaseURL(
                "file:///",
                renderMediaHtml(mediaUri),
                "text/html",
                "UTF-8",
                null,
            )
        }
        setContentView(webView)
    }

    override fun onDestroy() {
        if (::webView.isInitialized) {
            webView.destroy()
        }
        super.onDestroy()
    }

    private fun normalizeMediaUri(mediaUri: String, bookDirPath: String): String {
        return runCatching {
            if (bookDirPath.isBlank()) return ""
            val uri = Uri.parse(mediaUri)
            if (uri.scheme != "file") return ""
            val assetRoot = File(bookDirPath, "assets").canonicalFile
            val mediaFile = File(uri.path ?: return "").canonicalFile
            val isInsideAssets = mediaFile.path == assetRoot.path || mediaFile.path.startsWith(assetRoot.path + File.separator)
            if (!isInsideAssets || !mediaFile.isFile) return ""
            mediaFile.toURI().toString()
        }.getOrDefault("")
    }

    private fun renderMediaHtml(mediaUri: String): String {
        val safeUri = mediaUri
            .replace("&", "&amp;")
            .replace("\"", "&quot;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        val body = if (mediaUri.isBlank()) {
            """<div class="bookmd-media-missing">Media unavailable.</div>"""
        } else {
            """<img src="$safeUri" alt="Book media">"""
        }
        return """
            <!doctype html>
            <html>
              <head>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                  html, body {
                    margin: 0;
                    width: 100%;
                    height: 100%;
                    background: #fff;
                  }
                  body {
                    display: grid;
                    place-items: center;
                  }
                  img {
                    max-width: 100vw;
                    max-height: 100vh;
                    object-fit: contain;
                  }
                  .bookmd-media-missing {
                    color: #111;
                    font: 16px sans-serif;
                    padding: 24px;
                    text-align: center;
                  }
                </style>
              </head>
              <body>$body</body>
            </html>
        """.trimIndent()
    }
}
