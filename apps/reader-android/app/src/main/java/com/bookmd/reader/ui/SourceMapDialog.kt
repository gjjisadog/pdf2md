package com.bookmd.reader.ui

import android.app.AlertDialog
import android.content.Context
import android.content.Intent
import com.bookmd.reader.EXTRA_BOOK_DIR
import com.bookmd.reader.EXTRA_SOURCE_BBOX
import com.bookmd.reader.EXTRA_SOURCE_PAGE
import com.bookmd.reader.SourcePageActivity
import com.bookmd.reader.data.SourceMapBlock
import java.io.File

object SourceMapDialog {
    fun show(context: Context, bookDir: File, blockId: String, block: SourceMapBlock?) {
        val title = sourceTitlePreview(blockId).ifBlank { "Unknown block" }
        val message = if (block == null) {
            "No source text available."
        } else {
            val sourceType = block.type.ifBlank { "unknown" }
            val sourceText = sourceTextPreview(block.sourceText).ifBlank { "No source text available." }
            "Page: ${block.sourcePage}\nType: $sourceType\nBBox: ${block.bbox}\n\n$sourceText"
        }
        val builder = AlertDialog.Builder(context)
            .setTitle("Source: $title")
            .setMessage(message)
            .setPositiveButton("OK", null)
        if (block != null) {
            builder.setNeutralButton("Open PDF Page") { _, _ ->
                context.startActivity(Intent(context, SourcePageActivity::class.java).apply {
                    putExtra(EXTRA_BOOK_DIR, bookDir.absolutePath)
                    putExtra(EXTRA_SOURCE_PAGE, block.sourcePage)
                    putExtra(EXTRA_SOURCE_BBOX, block.bbox)
                })
            }
        }
        builder.show()
    }

    private fun sourceTextPreview(text: String): String {
        if (text.length <= MAX_SOURCE_TEXT_PREVIEW_LENGTH) return text
        return text.take(MAX_SOURCE_TEXT_PREVIEW_LENGTH) +
            "\n\nSource text truncated. Open PDF Page for full context."
    }

    private fun sourceTitlePreview(blockId: String): String {
        val normalized = blockId.trim()
            .replace("\n", " ")
            .replace("\r", " ")
        if (normalized.length <= MAX_SOURCE_TITLE_LENGTH) return normalized
        return normalized.take(MAX_SOURCE_TITLE_LENGTH) + "..."
    }

    private const val MAX_SOURCE_TEXT_PREVIEW_LENGTH = 1200
    private const val MAX_SOURCE_TITLE_LENGTH = 80
}
