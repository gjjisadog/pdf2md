package com.bookmd.reader.ui

import android.app.AlertDialog
import android.content.Context

object SourceMapDialog {
    fun show(context: Context, blockId: String, sourceText: String) {
        AlertDialog.Builder(context)
            .setTitle("Source: $blockId")
            .setMessage(sourceText.ifBlank { "No source text available." })
            .setPositiveButton("OK", null)
            .show()
    }
}
