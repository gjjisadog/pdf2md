package com.bookmd.reader.data

import java.io.File

class SourceMapRepository(private val bookDir: File) {
    fun readSourceMap(): String {
        return File(bookDir, "source_map.json").readText()
    }
}
