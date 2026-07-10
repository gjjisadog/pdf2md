package com.bookmd.reader.data

import android.content.Context

data class ReadingProgress(
    val chapterPath: String,
    val blockId: String,
    val scrollY: Int,
    val scrollX: Int = 0,
    val pageIndex: Int = 0,
    val pageCount: Int = 0,
    val updatedAtMillis: Long = 0L,
)

class ReadingProgressStore(context: Context) {
    private val preferences = context.getSharedPreferences("bookmd_progress", Context.MODE_PRIVATE)

    fun saveProgress(bookId: String, progress: ReadingProgress) {
        val updatedAtMillis = progress.updatedAtMillis.takeIf { it > 0L } ?: System.currentTimeMillis()
        preferences.edit()
            .putString("${bookId}:chapter_path", progress.chapterPath)
            .putString("${bookId}:block", progress.blockId)
            .putInt("${bookId}:scroll_y", progress.scrollY)
            .putInt("${bookId}:scroll_x", progress.scrollX)
            .putInt("${bookId}:page_index", progress.pageIndex)
            .putInt("${bookId}:page_count", progress.pageCount)
            .putLong("${bookId}:updated_at", updatedAtMillis)
            .apply()
    }

    fun readProgress(bookId: String): ReadingProgress {
        val pageCount = safeNonNegativeInt("${bookId}:page_count", 0)
        return ReadingProgress(
            chapterPath = safeString("${bookId}:chapter_path", ""),
            blockId = safeString("${bookId}:block", ""),
            scrollY = safeNonNegativeInt("${bookId}:scroll_y", 0),
            scrollX = safeNonNegativeInt("${bookId}:scroll_x", 0),
            pageIndex = safePageIndex("${bookId}:page_index", pageCount),
            pageCount = pageCount,
            updatedAtMillis = safeLong("${bookId}:updated_at", 0L),
        )
    }

    fun saveBookProgress(bookName: String, progress: ReadingProgress) = saveProgress(bookName, progress)

    fun clearBookProgress(bookName: String) {
        val editor = preferences.edit()
        preferences.all.keys
            .filter { it.startsWith("$bookName:") }
            .forEach { editor.remove(it) }
        editor.apply()
    }

    fun save(bookId: String, progress: ReadingProgress) = saveProgress(bookId, progress)

    fun load(bookId: String): ReadingProgress = readProgress(bookId)

    private fun safeString(key: String, default: String): String {
        return runCatching { preferences.getString(key, default) ?: default }.getOrDefault(default)
    }

    private fun safeInt(key: String, default: Int): Int {
        return runCatching { preferences.getInt(key, default) }.getOrDefault(default)
    }

    private fun safeNonNegativeInt(key: String, default: Int): Int {
        return safeInt(key, default).coerceAtLeast(0)
    }

    private fun safePageIndex(key: String, pageCount: Int): Int {
        if (pageCount <= 0) return 0
        return safeNonNegativeInt(key, 0).coerceAtMost(pageCount - 1)
    }

    private fun safeLong(key: String, default: Long): Long {
        return runCatching { preferences.getLong(key, default) }.getOrDefault(default)
    }
}
