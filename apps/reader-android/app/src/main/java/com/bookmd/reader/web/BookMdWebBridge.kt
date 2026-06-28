package com.bookmd.reader.web

import android.app.Activity
import android.webkit.JavascriptInterface
import com.bookmd.reader.ui.SourceMapDialog

class BookMdWebBridge(private val activity: Activity) {
    @JavascriptInterface
    fun onBlockSelected(blockId: String) {
        onSourceMapRequested(blockId)
    }

    @JavascriptInterface
    fun onSourceMapRequested(blockId: String) {
        activity.runOnUiThread {
            SourceMapDialog.show(activity, blockId, "")
        }
    }

    @JavascriptInterface
    fun onImageSelected(src: String?) {
        activity.runOnUiThread {
            SourceMapDialog.show(activity, "image", src ?: "")
        }
    }
}
