package com.bookmd.reader

import android.app.Activity
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.text.InputFilter
import android.os.Bundle
import android.text.Spannable
import android.text.SpannableString
import android.text.TextUtils
import android.text.style.ForegroundColorSpan
import android.text.style.StyleSpan
import android.view.Gravity
import android.view.inputmethod.EditorInfo
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import com.bookmd.reader.data.SearchResult
import com.bookmd.reader.data.SearchRepository
import java.io.File

class SearchActivity : Activity() {
    private lateinit var repository: SearchRepository
    private lateinit var results: LinearLayout
    private lateinit var resultsScroll: ScrollView
    private lateinit var bookDir: File

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val bookDirPath = intent.getStringExtra(EXTRA_BOOK_DIR)
        if (bookDirPath.isNullOrBlank()) {
            showSearchUnavailable()
            return
        }
        bookDir = File(bookDirPath)
        repository = SearchRepository(bookDir)
        val query = EditText(this).apply {
            hint = "Search Chinese text"
            filters = arrayOf(InputFilter.LengthFilter(SearchRepository.MAX_SEARCH_QUERY_LENGTH))
            setSingleLine(true)
            imeOptions = EditorInfo.IME_ACTION_SEARCH
            setOnEditorActionListener { _, actionId, _ ->
                if (actionId == EditorInfo.IME_ACTION_SEARCH) {
                    renderResults(text.toString())
                    true
                } else {
                    false
                }
            }
        }
        results = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        resultsScroll = ScrollView(this)
        resultsScroll.addView(results)
        showInitialSearchPrompt()
        setContentView(
            LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(32, 32, 32, 32)
                addView(query)
                addView(Button(this@SearchActivity).apply {
                    text = "Search"
                    setOnClickListener { renderResults(query.text.toString()) }
                })
                addView(
                    resultsScroll,
                    LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f),
                )
            }
        )
    }

    private fun showSearchUnavailable() {
        setContentView(TextView(this).apply {
            text = "Search unavailable."
            textSize = 18f
            setPadding(32, 32, 32, 32)
            gravity = Gravity.CENTER_VERTICAL
        })
    }

    private fun showInitialSearchPrompt() {
        results.addView(statusText("Type a search term."))
    }

    private fun renderResults(query: String) {
        results.removeAllViews()
        val trimmedQuery = query.trim()
        if (trimmedQuery.isBlank()) {
            results.addView(statusText("Type a search term."))
            return
        }
        if (trimmedQuery.length > SearchRepository.MAX_SEARCH_QUERY_LENGTH) {
            results.addView(statusText("Search term is too long."))
            return
        }
        val matches = repository.searchOrEmpty(trimmedQuery)
        if (matches.isEmpty()) {
            results.addView(statusText("No results."))
            return
        }
        matches.forEach { result ->
            results.addView(renderHighlightedResult(result))
        }
        if (matches.size >= SearchRepository.MAX_SEARCH_RESULTS) {
            results.addView(statusText("Showing first ${SearchRepository.MAX_SEARCH_RESULTS} results."))
        }
    }

    private fun renderHighlightedResult(result: SearchResult): TextView {
        return TextView(this).apply {
            text = highlightedResultText(result)
            textSize = 16f
            maxLines = MAX_SEARCH_RESULT_LINES
            ellipsize = TextUtils.TruncateAt.END
            setPadding(0, 20, 0, 20)
            setOnClickListener {
                startActivity(Intent(this@SearchActivity, ReaderActivity::class.java).apply {
                    putExtra(EXTRA_BOOK_DIR, bookDir.absolutePath)
                    putExtra(EXTRA_CHAPTER_ID, result.chapterId)
                    putExtra(EXTRA_CHAPTER_PATH, result.chapterPath)
                    putExtra(EXTRA_TARGET_BLOCK_ID, result.blockId)
                })
            }
        }
    }

    private fun highlightedResultText(result: SearchResult): SpannableString {
        val chapterTitle = flattenSearchRowText(result.chapterTitle)
        val snippet = flattenSearchRowText(result.snippet)
        val fullText = "$chapterTitle\n$snippet"
        val snippetOffset = chapterTitle.length + 1
        val highlightStart = snippetOffset + result.matchStart
        val highlightEnd = snippetOffset + result.matchEnd
        return SpannableString(fullText).apply {
            if (highlightStart in 0 until highlightEnd && highlightEnd <= fullText.length) {
                setSpan(
                    ForegroundColorSpan(Color.rgb(176, 61, 0)),
                    highlightStart,
                    highlightEnd,
                    Spannable.SPAN_EXCLUSIVE_EXCLUSIVE,
                )
                setSpan(
                    StyleSpan(Typeface.BOLD),
                    highlightStart,
                    highlightEnd,
                    Spannable.SPAN_EXCLUSIVE_EXCLUSIVE,
                )
            }
        }
    }

    private fun flattenSearchRowText(text: String): String {
        return text
            .replace("\n", " ")
            .replace("\r", " ")
    }

    private fun statusText(message: String): TextView {
        return TextView(this).apply {
            text = message
            textSize = 16f
            setPadding(0, 20, 0, 20)
            gravity = Gravity.CENTER_VERTICAL
        }
    }

    companion object {
        private const val MAX_SEARCH_RESULT_LINES = 4
    }
}
