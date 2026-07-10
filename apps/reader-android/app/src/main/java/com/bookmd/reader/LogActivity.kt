package com.bookmd.reader

import android.app.Activity
import android.app.AlertDialog
import android.os.Bundle
import android.text.TextUtils
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import com.bookmd.reader.data.ReaderLogStore
import java.text.DateFormat
import java.util.Date

class LogActivity : Activity() {
    private lateinit var logStore: ReaderLogStore
    private lateinit var list: LinearLayout
    private lateinit var clearButton: Button
    private val timeFormatter = DateFormat.getDateTimeInstance(DateFormat.SHORT, DateFormat.SHORT)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        logStore = ReaderLogStore(this)
        list = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        setContentView(
            ScrollView(this).apply {
                addView(LinearLayout(this@LogActivity).apply {
                    orientation = LinearLayout.VERTICAL
                    setPadding(32, 32, 32, 32)
                    clearButton = Button(this@LogActivity).apply {
                        text = "Clear logs"
                        setOnClickListener {
                            confirmClearLogs()
                        }
                    }
                    addView(clearButton)
                    addView(list)
                })
            }
        )
        refreshLogs()
    }

    private fun confirmClearLogs() {
        AlertDialog.Builder(this)
            .setTitle("Clear logs?")
            .setMessage("Clear all local operation logs?")
            .setPositiveButton("Clear") { _, _ ->
                clearLogs()
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun clearLogs() {
        logStore.clear()
        refreshLogs()
    }

    private fun refreshLogs() {
        list.removeAllViews()
        val entries = logStore.entries()
        clearButton.isEnabled = entries.isNotEmpty()
        if (entries.isEmpty()) {
            list.addView(emptyLogText())
            return
        }
        entries.forEach { entry ->
            list.addView(TextView(this).apply {
                text = "${formatLogTime(entry.createdAtMillis)}\n[${displayLogCategory(entry.category)}] ${displayLogMessage(entry.message)}"
                textSize = 14f
                maxLines = MAX_LOG_ENTRY_LINES
                ellipsize = TextUtils.TruncateAt.END
                setPadding(0, 16, 0, 16)
            })
        }
    }

    private fun emptyLogText(): TextView {
        return TextView(this).apply {
            text = "No logs yet."
            textSize = 18f
            setPadding(0, 24, 0, 24)
        }
    }

    private fun formatLogTime(createdAtMillis: Long): String {
        if (createdAtMillis <= 0L) return "Unknown time"
        return timeFormatter.format(Date(createdAtMillis))
    }

    private fun displayLogMessage(message: String): String {
        return message
            .replace("\n", " ")
            .replace("\r", " ")
    }

    private fun displayLogCategory(category: String): String {
        return category.ifBlank { "unknown" }
            .replace("\n", " ")
            .replace("\r", " ")
    }

    companion object {
        private const val MAX_LOG_ENTRY_LINES = 4
    }
}
