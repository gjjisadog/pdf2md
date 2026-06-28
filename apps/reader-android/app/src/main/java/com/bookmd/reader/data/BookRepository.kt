package com.bookmd.reader.data

import java.io.File
import java.util.zip.ZipFile

class BookRepository(private val rootDir: File) {
    fun importBook(bookmd: File): File {
        val target = File(rootDir, bookmd.nameWithoutExtension)
        target.mkdirs()
        ZipFile(bookmd).use { zip ->
            zip.entries().asSequence().forEach { entry ->
                val output = File(target, entry.name)
                if (entry.isDirectory) {
                    output.mkdirs()
                } else {
                    output.parentFile?.mkdirs()
                    zip.getInputStream(entry).use { input ->
                        output.outputStream().use { input.copyTo(it) }
                    }
                }
            }
        }
        require(File(target, "book.json").exists()) { "book.json is missing" }
        return target
    }

    fun readManifest(bookDir: File): String {
        return File(bookDir, "book.json").readText()
    }
}
