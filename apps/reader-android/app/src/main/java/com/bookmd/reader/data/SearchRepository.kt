package com.bookmd.reader.data

import java.io.File
import org.json.JSONObject

data class SearchResult(
    val blockId: String,
    val chapterId: String,
    val chapterTitle: String,
    val text: String,
)

class SearchRepository(private val bookDir: File) {
    fun search(query: String): List<SearchResult> {
        if (query.isBlank()) return emptyList()
        val indexFile = File(bookDir, "search_index.json")
        if (!indexFile.exists()) return emptyList()
        val root = JSONObject(indexFile.readText())
        val items = root.optJSONArray("items") ?: return emptyList()
        val results = mutableListOf<SearchResult>()
        for (index in 0 until items.length()) {
            val item = items.getJSONObject(index)
            val text = item.optString("text")
            if (text.contains(query, ignoreCase = true)) {
                results.add(
                    SearchResult(
                        blockId = item.optString("block_id"),
                        chapterId = item.optString("chapter_id"),
                        chapterTitle = item.optString("chapter_title"),
                        text = text,
                    )
                )
            }
        }
        return results
    }
}
