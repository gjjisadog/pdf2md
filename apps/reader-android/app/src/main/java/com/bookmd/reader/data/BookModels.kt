package com.bookmd.reader.data

data class BookChapter(
    val id: String,
    val title: String,
    val path: String,
    val order: Int,
)

data class BookManifest(
    val bookId: String,
    val title: String,
    val formatVersion: String?,
    val chapters: List<BookChapter>,
)
