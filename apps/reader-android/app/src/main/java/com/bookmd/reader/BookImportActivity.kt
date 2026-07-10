package com.bookmd.reader

import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.provider.OpenableColumns
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import com.bookmd.reader.data.BookRepository
import com.bookmd.reader.data.ReaderLogStore
import java.io.File

class BookImportActivity : Activity() {
    private lateinit var repository: BookRepository
    private lateinit var logStore: ReaderLogStore
    private lateinit var status: TextView
    private lateinit var statusScroll: ScrollView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        repository = BookRepository(filesDir)
        logStore = ReaderLogStore(this)
        status = TextView(this).apply {
            text = "Choose a .bookmd package to import."
            textSize = 16f
            setPadding(0, 24, 0, 24)
        }
        statusScroll = ScrollView(this)
        statusScroll.addView(status)
        val pick = Button(this).apply {
            text = "Import .bookmd"
            setOnClickListener { openBookPicker() }
        }
        setContentView(
            LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(32, 32, 32, 32)
                addView(pick)
                addView(
                    statusScroll,
                    LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f),
                )
            }
        )
    }

    private fun openBookPicker() {
        val intent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            type = "*/*"
            putExtra(Intent.EXTRA_MIME_TYPES, BOOKMD_MIME_TYPES)
        }
        startActivityForResult(intent, REQUEST_BOOKMD)
    }

    @Deprecated("Kept for minSdk 26 without ActivityX dependency.")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != REQUEST_BOOKMD) return
        if (resultCode != RESULT_OK) {
            showNoFileSelected()
            return
        }
        val uri = data?.data ?: run {
            showNoFileSelected()
            return
        }
        var imported: File? = null
        try {
            runCatching {
                imported = copyUriToImportFile(uri, displayNameForUri(uri))
                repository.importBook(requireNotNull(imported))
            }.onSuccess { bookDir ->
                status.text = "Imported: ${bookDir.name}"
                logStore.append("import", "Imported ${bookDir.name}")
                finish()
            }.onFailure { error ->
                val message = error.message ?: error.javaClass.simpleName
                status.text = "Import failed: $message"
                logStore.append("import", "Import failed: $message")
            }
        } finally {
            imported?.delete()
        }
    }

    private fun showNoFileSelected() {
        status.text = "No file selected."
    }

    private fun copyUriToImportFile(uri: Uri, sourceName: String): File {
        val target = File(cacheDir, sanitizeImportName(sourceName))
        try {
            contentResolver.openInputStream(uri).use { input ->
                requireNotNull(input) { "Unable to open selected file" }
                target.outputStream().use { output -> input.copyTo(output) }
            }
        } catch (error: Exception) {
            target.delete()
            throw error
        }
        return target
    }

    private fun displayNameForUri(uri: Uri): String {
        contentResolver.query(
            uri,
            arrayOf(OpenableColumns.DISPLAY_NAME),
            null,
            null,
            null,
        )?.use { cursor ->
            if (cursor.moveToFirst()) {
                val displayNameColumn = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                if (displayNameColumn >= 0) {
                    val displayName = cursor.getString(displayNameColumn)
                    if (!displayName.isNullOrBlank()) return displayName
                }
            }
        }
        return uri.lastPathSegment?.substringAfterLast('/') ?: "imported.bookmd"
    }

    private fun sanitizeImportName(name: String): String {
        val cleaned = name
            .substringAfterLast('/')
            .replace(Regex("[^\\p{L}\\p{N}._-]+"), "_")
            .trim('_', '.', ' ')
            .ifBlank { "imported" }
        val suffix = ".bookmd"
        val base = if (cleaned.endsWith(suffix, ignoreCase = true)) {
            cleaned.dropLast(suffix.length)
        } else {
            cleaned
        }
        val cappedBase = base.take(MAX_IMPORT_CACHE_NAME_LENGTH - suffix.length).ifBlank { "imported" }
        return "$cappedBase$suffix"
    }

    companion object {
        private const val REQUEST_BOOKMD = 1001
        private const val MAX_IMPORT_CACHE_NAME_LENGTH = 120
        private val BOOKMD_MIME_TYPES = arrayOf(
            "application/zip",
            "application/octet-stream",
        )
    }
}
