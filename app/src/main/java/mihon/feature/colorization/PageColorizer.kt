package mihon.feature.colorization

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.ByteArrayOutputStream

/**
 * Colorizes whole pages with an [ColorizationEngine], keeping their original resolution.
 */
class PageColorizer(private val engine: ColorizationEngine) {

    /**
     * Returns the colorized page as a JPEG, or null when the page should be kept as is: it couldn't be decoded, it's
     * too big to be held in memory or it already has colors.
     */
    suspend fun colorize(image: ByteArray, series: String? = null): ByteArray? {
        val bitmap = withContext(Dispatchers.Default) { decode(image) } ?: return null
        try {
            for (tile in ColorizationPipeline.tiles(bitmap.width, bitmap.height)) {
                val pixels = IntArray(tile.width * tile.height)
                bitmap.getPixels(pixels, 0, tile.width, tile.left, tile.top, tile.width, tile.height)
                if (ColorizationPipeline.isAlreadyColored(pixels)) return null
                colorizeTile(pixels, tile.width, tile.height, series)
                bitmap.setPixels(pixels, 0, tile.width, tile.left, tile.top, tile.width, tile.height)
            }
            return withContext(Dispatchers.Default) {
                ByteArrayOutputStream().use {
                    bitmap.compress(Bitmap.CompressFormat.JPEG, JPEG_QUALITY, it)
                    it.toByteArray()
                }
            }
        } finally {
            bitmap.recycle()
        }
    }

    private suspend fun colorizeTile(pixels: IntArray, width: Int, height: Int, series: String?) {
        val (contentWidth, contentHeight) = ColorizationPipeline.contentSize(width, height, engine.longSide)
        val gray = withContext(Dispatchers.Default) {
            ColorizationPipeline.prepareGray(pixels, width, height, contentWidth, contentHeight)
        }
        val prediction = engine.predict(gray, contentWidth, contentHeight, series)
        withContext(Dispatchers.Default) {
            ColorizationPipeline.retainInk(pixels, width, height, gray, prediction, contentWidth, contentHeight)
        }
    }

    private fun decode(image: ByteArray): Bitmap? {
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        BitmapFactory.decodeByteArray(image, 0, image.size, bounds)
        if (bounds.outWidth <= 0 || bounds.outHeight <= 0) return null
        if (bounds.outWidth.toLong() * bounds.outHeight > MAX_PIXELS) return null
        val options = BitmapFactory.Options().apply {
            inMutable = true
            inPreferredConfig = Bitmap.Config.ARGB_8888
        }
        return BitmapFactory.decodeByteArray(image, 0, image.size, options)
    }

    private companion object {
        const val JPEG_QUALITY = 92
        const val MAX_PIXELS = 30_000_000L
    }
}
