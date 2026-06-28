package com.bookmd.reader

import android.annotation.SuppressLint
import android.app.Activity
import android.os.Bundle
import android.webkit.WebView

class ImageViewerActivity : Activity() {
    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val mediaUri = intent.getStringExtra(EXTRA_MEDIA_URI) ?: intent.getStringExtra("media_uri") ?: ""
        setContentView(
            WebView(this).apply {
                settings.allowFileAccess = true
                settings.javaScriptEnabled = false
                setBackgroundColor(android.graphics.Color.BLACK)
                loadDataWithBaseURL(
                    "file:///",
                    renderMediaHtml(mediaUri),
                    "text/html",
                    "UTF-8",
                    null,
                )
            }
        )
    }

    private fun renderMediaHtml(mediaUri: String): String {
        val safeUri = mediaUri
            .replace("&", "&amp;")
            .replace("\"", "&quot;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
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
                    background: #000;
                  }
                  body {
                    display: grid;
                    place-items: center;
                  }
                  img {
                    max-width: 100vw;
                    max-height: 100vh;
                  }
                </style>
              </head>
              <body><img src="$safeUri"></body>
            </html>
        """.trimIndent()
    }
}
