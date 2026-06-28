package com.bookmd.reader.web

import android.app.Activity
import android.content.Intent
import android.webkit.JavascriptInterface
import com.bookmd.reader.EXTRA_MEDIA_URI
import com.bookmd.reader.ImageViewerActivity
import com.bookmd.reader.data.SourceMapRepository
import com.bookmd.reader.ui.SourceMapDialog
import java.io.File

class BookMdWebBridge(
    private val activity: Activity,
    bookDir: File,
) {
    private val sourceMapRepository = SourceMapRepository(bookDir)

    @JavascriptInterface
    fun onBlockSelected(blockId: String) {
        onSourceMapRequested(blockId)
    }

    @JavascriptInterface
    fun onSourceMapRequested(blockId: String) {
        val block = sourceMapRepository.findBlock(blockId)
        activity.runOnUiThread {
            SourceMapDialog.show(
                activity,
                blockId,
                if (block == null) {
                    ""
                } else {
                    "Page: ${block.sourcePage}\nType: ${block.type}\nBBox: ${block.bbox}\n\n${block.sourceText}"
                },
            )
        }
    }

    @JavascriptInterface
    fun onImageSelected(src: String?) {
        activity.runOnUiThread {
            activity.startActivity(Intent(activity, ImageViewerActivity::class.java).apply {
                putExtra(EXTRA_MEDIA_URI, src ?: "")
                putExtra("media_uri", src ?: "")
            })
        }
    }
}
