package com.bookmd.reader.data

import android.content.Context

data class ReadingProgress(
    val chapterId: String,
    val blockId: String,
    val pageIndex: Int,
)

class ReadingProgressStore(context: Context) {
    private val preferences = context.getSharedPreferences("bookmd_progress", Context.MODE_PRIVATE)

    fun save(bookId: String, progress: ReadingProgress) {
        preferences.edit()
            .putString("${bookId}:chapter", progress.chapterId)
            .putString("${bookId}:block", progress.blockId)
            .putInt("${bookId}:page", progress.pageIndex)
            .apply()
    }

    fun load(bookId: String): ReadingProgress {
        return ReadingProgress(
            chapterId = preferences.getString("${bookId}:chapter", "") ?: "",
            blockId = preferences.getString("${bookId}:block", "") ?: "",
            pageIndex = preferences.getInt("${bookId}:page", 0),
        )
    }
}
