package com.bookmd.reader

import android.app.Activity
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.pdf.PdfRenderer
import android.os.Bundle
import android.os.ParcelFileDescriptor
import android.view.Gravity
import android.view.View
import android.widget.HorizontalScrollView
import android.widget.ScrollView
import android.widget.TextView
import java.io.File
import kotlin.math.roundToInt
import org.json.JSONArray

class SourcePageActivity : Activity() {
    private var renderedBitmap: Bitmap? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val bookDirPath = intent.getStringExtra(EXTRA_BOOK_DIR)
        if (bookDirPath.isNullOrBlank()) {
            showSourcePageError("Original PDF unavailable.")
            return
        }
        val bookDir = File(bookDirPath)
        val sourcePage = intent.getIntExtra(EXTRA_SOURCE_PAGE, 1)
        val bbox = intent.getStringExtra(EXTRA_SOURCE_BBOX).orEmpty()
        val pdfFile = File(bookDir, "source/original.pdf")
        if (!pdfFile.exists()) {
            showSourcePageError("Original PDF unavailable.")
            return
        }
        val sourcePageRender = runCatching {
            renderSourcePage(pdfFile, sourcePage)
        }.getOrElse {
            showSourcePageError("Original PDF unavailable.")
            return
        }
        renderedBitmap = sourcePageRender.bitmap
        val parsedBbox = parseBbox(bbox)
        val horizontalScroll = HorizontalScrollView(this)
        val verticalScroll = ScrollView(this)
        verticalScroll.addView(
            SourcePageView(
                this@SourcePageActivity,
                sourcePageRender.bitmap,
                parsedBbox,
                sourcePageRender.renderScale,
            ).apply {
                contentDescription = "Page $sourcePage $bbox"
            }
        )
        horizontalScroll.addView(verticalScroll)
        setContentView(horizontalScroll)
        scrollToSourceBbox(horizontalScroll, verticalScroll, parsedBbox, sourcePageRender.renderScale)
    }

    override fun onDestroy() {
        renderedBitmap?.recycle()
        renderedBitmap = null
        super.onDestroy()
    }

    private fun renderSourcePage(pdfFile: File, sourcePage: Int): SourcePageRender {
        val descriptor = ParcelFileDescriptor.open(pdfFile, ParcelFileDescriptor.MODE_READ_ONLY)
        try {
            val renderer = PdfRenderer(descriptor)
            try {
                if (sourcePage < 1 || sourcePage > renderer.pageCount) {
                    throw IllegalArgumentException("Invalid source page")
                }
                val pageIndex = sourcePage - 1
                val page = renderer.openPage(pageIndex)
                try {
                    val renderScale = pageRenderScale(page.width, page.height)
                    val renderWidth = (page.width * renderScale).roundToInt().coerceAtLeast(1)
                    val renderHeight = (page.height * renderScale).roundToInt().coerceAtLeast(1)
                    val bitmap = Bitmap.createBitmap(renderWidth, renderHeight, Bitmap.Config.ARGB_8888)
                    bitmap.eraseColor(Color.WHITE)
                    page.render(bitmap, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)
                    return SourcePageRender(bitmap, renderScale)
                } finally {
                    page.close()
                }
            } finally {
                renderer.close()
            }
        } finally {
            descriptor.close()
        }
    }

    private fun pageRenderScale(pageWidth: Int, pageHeight: Int): Float {
        val widthScale = MAX_SOURCE_PAGE_BITMAP_SIDE.toFloat() / pageWidth.coerceAtLeast(1).toFloat()
        val heightScale = MAX_SOURCE_PAGE_BITMAP_SIDE.toFloat() / pageHeight.coerceAtLeast(1).toFloat()
        return minOf(widthScale, heightScale).coerceAtMost(SOURCE_PAGE_BASE_RENDER_SCALE)
    }

    private fun showSourcePageError(message: String) {
        setContentView(TextView(this).apply {
            text = message
            textSize = 18f
            setPadding(32, 32, 32, 32)
            gravity = Gravity.CENTER_VERTICAL
        })
    }

    private fun scrollToSourceBbox(
        horizontalScroll: HorizontalScrollView,
        verticalScroll: ScrollView,
        bbox: RectF?,
        renderScale: Float,
    ) {
        if (bbox == null) return
        horizontalScroll.post {
            val scrollX = ((bbox.left * renderScale).roundToInt() - SOURCE_BBOX_SCROLL_MARGIN_PX).coerceAtLeast(0)
            val scrollY = ((bbox.top * renderScale).roundToInt() - SOURCE_BBOX_SCROLL_MARGIN_PX).coerceAtLeast(0)
            horizontalScroll.scrollTo(scrollX, 0)
            verticalScroll.scrollTo(0, scrollY)
        }
    }

    private fun parseBbox(bbox: String): RectF? {
        val values = runCatching { JSONArray(bbox) }.getOrNull() ?: return null
        if (values.length() != 4) return null
        val left = bboxValueOrNull(values, 0) ?: return null
        val top = bboxValueOrNull(values, 1) ?: return null
        val right = bboxValueOrNull(values, 2) ?: return null
        val bottom = bboxValueOrNull(values, 3) ?: return null
        if (right <= left || bottom <= top) return null
        return RectF(left, top, right, bottom)
    }

    private fun bboxValueOrNull(values: JSONArray, index: Int): Float? {
        val value = values.optDouble(index)
        if (!value.isFinite()) return null
        return value.toFloat()
    }

    private class SourcePageView(
        context: android.content.Context,
        private val bitmap: Bitmap,
        private val bbox: RectF?,
        private val renderScale: Float,
    ) : View(context) {
        private val bboxPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.rgb(255, 176, 0)
            style = Paint.Style.STROKE
            strokeWidth = 6f
        }

        override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
            val width = bitmap.width
            val height = bitmap.height
            setMeasuredDimension(width, height)
        }

        override fun onDraw(canvas: Canvas) {
            super.onDraw(canvas)
            canvas.drawBitmap(bitmap, 0f, 0f, null)
            val rect = bbox ?: return
            canvas.drawRect(
                RectF(
                    rect.left * renderScale,
                    rect.top * renderScale,
                    rect.right * renderScale,
                    rect.bottom * renderScale,
                ),
                bboxPaint,
            )
        }
    }

    private data class SourcePageRender(
        val bitmap: Bitmap,
        val renderScale: Float,
    )

    companion object {
        private const val SOURCE_PAGE_BASE_RENDER_SCALE = 2f
        private const val MAX_SOURCE_PAGE_BITMAP_SIDE = 4096
        private const val SOURCE_BBOX_SCROLL_MARGIN_PX = 96
    }
}
