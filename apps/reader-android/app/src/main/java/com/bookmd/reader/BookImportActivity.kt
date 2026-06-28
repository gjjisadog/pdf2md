package com.bookmd.reader

import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import com.bookmd.reader.data.BookRepository
import java.io.File

class BookImportActivity : Activity() {
    private lateinit var repository: BookRepository
    private lateinit var status: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        repository = BookRepository(filesDir)
        status = TextView(this)
        val pick = Button(this).apply {
            text = "Import .bookmd"
            setOnClickListener { openBookPicker() }
        }
        setContentView(
            LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(32, 32, 32, 32)
                addView(pick)
                addView(status)
            }
        )
    }

    private fun openBookPicker() {
        val intent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            type = "*/*"
        }
        startActivityForResult(intent, REQUEST_BOOKMD)
    }

    @Deprecated("Kept for minSdk 26 without ActivityX dependency.")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != REQUEST_BOOKMD || resultCode != RESULT_OK) return
        val uri = data?.data ?: return
        val imported = copyUriToImportFile(uri)
        val bookDir = repository.importBook(imported)
        status.text = "Imported: ${bookDir.name}"
    }

    private fun copyUriToImportFile(uri: Uri): File {
        val target = File(cacheDir, "imported.bookmd")
        contentResolver.openInputStream(uri).use { input ->
            requireNotNull(input) { "Unable to open selected file" }
            target.outputStream().use { output -> input.copyTo(output) }
        }
        return target
    }

    companion object {
        private const val REQUEST_BOOKMD = 1001
    }
}
