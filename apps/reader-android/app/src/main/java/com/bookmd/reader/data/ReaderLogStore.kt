package com.bookmd.reader.data

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

data class ReaderLogEntry(
    val category: String,
    val message: String,
    val createdAtMillis: Long,
)

class ReaderLogStore(context: Context) {
    private val preferences = context.getSharedPreferences("bookmd_logs", Context.MODE_PRIVATE)

    fun append(category: String, message: String) {
        val entries = readEntriesArray()
        entries.put(
            JSONObject()
                .put("category", category)
                .put("message", trimMessage(message))
                .put("created_at", System.currentTimeMillis())
        )
        val trimmed = JSONArray()
        val start = (entries.length() - MAX_ENTRIES).coerceAtLeast(0)
        for (index in start until entries.length()) {
            trimmed.put(entries.optJSONObject(index) ?: continue)
        }
        preferences.edit().putString(KEY_ENTRIES, trimmed.toString()).apply()
    }

    fun entries(): List<ReaderLogEntry> {
        val entries = readEntriesArray()
        val result = mutableListOf<ReaderLogEntry>()
        for (index in 0 until entries.length()) {
            val item = entries.optJSONObject(index) ?: continue
            result.add(
                ReaderLogEntry(
                    category = item.optString("category"),
                    message = item.optString("message"),
                    createdAtMillis = item.optLong("created_at"),
                )
            )
        }
        return result.asReversed()
    }

    fun clear() {
        preferences.edit().remove(KEY_ENTRIES).apply()
    }

    private fun trimMessage(message: String): String {
        if (message.length <= MAX_MESSAGE_LENGTH) return message
        return message.take(MAX_MESSAGE_LENGTH) + " ... message truncated"
    }

    private fun readEntriesArray(): JSONArray {
        return runCatching {
            JSONArray(preferences.getString(KEY_ENTRIES, "[]") ?: "[]")
        }.getOrElse { JSONArray() }
    }

    companion object {
        private const val KEY_ENTRIES = "entries"
        private const val MAX_ENTRIES = 100
        private const val MAX_MESSAGE_LENGTH = 1000
    }
}
