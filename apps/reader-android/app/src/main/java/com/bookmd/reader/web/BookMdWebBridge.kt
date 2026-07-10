package com.bookmd.reader.web

import android.app.Activity
import android.content.Intent
import com.bookmd.reader.EXTRA_BOOK_DIR
import android.webkit.JavascriptInterface
import com.bookmd.reader.EXTRA_MEDIA_URI
import com.bookmd.reader.ImageViewerActivity
import com.bookmd.reader.data.SourceMapRepository
import com.bookmd.reader.ui.SourceMapDialog
import java.io.File
import org.json.JSONObject

class BookMdWebBridge(
    private val activity: Activity,
    private val bookDir: File,
    private val onProgressChanged: (String, Int, Int, Int, Int) -> Unit = { _, _, _, _, _ -> },
) {
    private val sourceMapRepository = SourceMapRepository(bookDir)

    @JavascriptInterface
    fun onBlockSelected(blockId: String) {
        onSourceMapRequested(blockId)
    }

    @JavascriptInterface
    fun onSourceMapRequested(blockId: String) {
        val block = runCatching { sourceMapRepository.findBlockOrNull(blockId) }.getOrNull()
        val bbox = block?.bbox.orEmpty()
        activity.runOnUiThread {
            SourceMapDialog.show(
                activity,
                bookDir,
                blockId,
                block?.copy(bbox = bbox),
            )
        }
    }

    @JavascriptInterface
    fun onImageSelected(src: String?) {
        activity.runOnUiThread {
            activity.startActivity(Intent(activity, ImageViewerActivity::class.java).apply {
                putExtra(EXTRA_BOOK_DIR, bookDir.absolutePath)
                putExtra(EXTRA_MEDIA_URI, src ?: "")
                putExtra("media_uri", src ?: "")
            })
        }
    }

    @JavascriptInterface
    fun onReadingProgressChanged(blockId: String?, scrollY: Int) {
        onProgressChanged(blockId ?: "", scrollY, 0, 0, 0)
    }

    @JavascriptInterface
    fun onReadingProgressChangedPayload(payload: String?) {
        val progress = runCatching {
            JSONObject(payload ?: "{}")
        }.getOrElse { JSONObject() }
        onProgressChanged(
            progress.optString("block_id", ""),
            progress.optInt("scroll_y", 0),
            progress.optInt("scroll_x", 0),
            progress.optInt("page_index", 0),
            progress.optInt("page_count", 0),
        )
    }
}
