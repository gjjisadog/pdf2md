package com.bookmd.reader.data

import java.io.File
import org.json.JSONObject

data class SourceMapBlock(
    val blockId: String,
    val sourcePage: Int,
    val bbox: String,
    val sourceText: String,
    val type: String,
)

class SourceMapRepository(private val bookDir: File) {
    fun readSourceMap(): String {
        return File(bookDir, "source_map.json").readText()
    }

    fun findBlock(blockId: String): SourceMapBlock? {
        val root = JSONObject(readSourceMap())
        val blocks = root.optJSONArray("blocks") ?: return null
        for (index in 0 until blocks.length()) {
            val item = blocks.getJSONObject(index)
            if (item.optString("block_id") == blockId) {
                return SourceMapBlock(
                    blockId = item.optString("block_id"),
                    sourcePage = item.optInt("source_page"),
                    bbox = item.optJSONArray("bbox")?.toString() ?: "[]",
                    sourceText = item.optString("source_text"),
                    type = item.optString("type"),
                )
            }
        }
        return null
    }
}
