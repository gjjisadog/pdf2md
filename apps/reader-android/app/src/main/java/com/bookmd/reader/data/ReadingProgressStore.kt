package com.bookmd.reader.data

import android.content.Context

data class ReadingProgress(
    val chapterPath: String,
    val blockId: String,
    val scrollY: Int,
)

class ReadingProgressStore(context: Context) {
    private val preferences = context.getSharedPreferences("bookmd_progress", Context.MODE_PRIVATE)

    fun saveProgress(bookId: String, progress: ReadingProgress) {
        preferences.edit()
            .putString("${bookId}:chapter_path", progress.chapterPath)
            .putString("${bookId}:block", progress.blockId)
            .putInt("${bookId}:scroll_y", progress.scrollY)
            .apply()
    }

    fun readProgress(bookId: String): ReadingProgress {
        return ReadingProgress(
            chapterPath = preferences.getString("${bookId}:chapter_path", "") ?: "",
            blockId = preferences.getString("${bookId}:block", "") ?: "",
            scrollY = preferences.getInt("${bookId}:scroll_y", 0),
        )
    }

    fun save(bookId: String, progress: ReadingProgress) = saveProgress(bookId, progress)

    fun load(bookId: String): ReadingProgress = readProgress(bookId)
}
