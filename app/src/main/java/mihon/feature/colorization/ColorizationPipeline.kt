package mihon.feature.colorization

import kotlin.math.ceil
import kotlin.math.floor
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt

/**
 * Android-free image math around the manga colorization model (manga-colorization-v2 generator, INT8 ONNX export).
 *
 * Mirrors the reference pipeline of the model ("gray-area-whitepad32-inkratio-v1"): the page is converted to
 * grayscale, area-downscaled so its longest side matches the inference size, padded with white to a multiple of 32,
 * colorized at that low resolution, then the prediction is upscaled and re-inked with the original line art so the
 * output keeps the source resolution and sharpness.
 */
object ColorizationPipeline {

    const val PAD_MULTIPLE = 32
    const val INPUT_CHANNELS = 5

    private const val INK_EPSILON = 0.02f
    private const val INK_MAX_RATIO = 2f
    private const val INK_DARK_THRESHOLD = 0.07f

    // Pages taller (or wider) than this ratio, like webtoon strips, are colorized in several parts
    private const val MAX_TILE_RATIO = 2.5
    private const val TARGET_TILE_RATIO = 1.5

    // JPEG artifacts give grayscale scans some chroma noise; real color pages have far more and stronger chroma
    private const val COLOR_CHROMA_THRESHOLD = 40
    private const val COLOR_PIXELS_FRACTION = 0.05

    data class Tile(val left: Int, val top: Int, val width: Int, val height: Int)

    /** Splits a page whose aspect ratio is too extreme for the model into parts of a more usual shape. */
    fun tiles(width: Int, height: Int): List<Tile> {
        val long = max(width, height)
        val short = min(width, height)
        if (long <= short * MAX_TILE_RATIO) return listOf(Tile(0, 0, width, height))
        val count = ceil(long / (short * TARGET_TILE_RATIO)).toInt()
        return (0 until count).map { i ->
            val start = long * i / count
            val end = long * (i + 1) / count
            if (height >= width) Tile(0, start, width, end - start) else Tile(start, 0, end - start, height)
        }
    }

    /** Whether the page already has colors, in which case it's kept as is. */
    fun isAlreadyColored(argb: IntArray): Boolean {
        val step = max(1, argb.size / 200_000)
        var sampled = 0
        var colored = 0
        for (i in argb.indices step step) {
            val c = argb[i]
            val r = c shr 16 and 0xFF
            val g = c shr 8 and 0xFF
            val b = c and 0xFF
            if (max(r, max(g, b)) - min(r, min(g, b)) > COLOR_CHROMA_THRESHOLD) colored++
            sampled++
        }
        return colored > sampled * COLOR_PIXELS_FRACTION
    }

    /** Luminance (ITU-R 601, like PIL "L") of a non-premultiplied ARGB pixel composited onto white, in [0,255]. */
    fun luminance(argb: Int): Int {
        val alpha = argb ushr 24
        val r = argb shr 16 and 0xFF
        val g = argb shr 8 and 0xFF
        val b = argb and 0xFF
        val l = (r * 299 + g * 587 + b * 114 + 500) / 1000
        return (l * alpha + 255 * (255 - alpha) + 127) / 255
    }

    /** Size of the image fed to the model: same aspect ratio, longest side equal to [longSide]. */
    fun contentSize(width: Int, height: Int, longSide: Int): Pair<Int, Int> {
        val scale = longSide.toDouble() / max(width, height)
        return max(1, (width * scale).roundToInt()) to max(1, (height * scale).roundToInt())
    }

    /** Grayscale [0,1] content-size image used both as model input and as low-resolution ink reference. */
    fun prepareGray(argb: IntArray, width: Int, height: Int, contentWidth: Int, contentHeight: Int): FloatArray {
        val gray = FloatArray(argb.size) { luminance(argb[it]).toFloat() }
        val resized = resizeArea(gray, width, height, contentWidth, contentHeight)
        // Quantize like the reference (uint8 resize) to stay close to the calibration data
        for (i in resized.indices) resized[i] = resized[i].roundToInt().coerceIn(0, 255) / 255f
        return resized
    }

    fun paddedSize(size: Int): Int = (size + PAD_MULTIPLE - 1) / PAD_MULTIPLE * PAD_MULTIPLE

    /** NCHW `[1, 5, H, W]` input: white-padded grayscale followed by four empty color hint channels. */
    fun buildInputTensor(gray: FloatArray, contentWidth: Int, contentHeight: Int): FloatArray {
        val paddedWidth = paddedSize(contentWidth)
        val paddedHeight = paddedSize(contentHeight)
        val tensor = FloatArray(INPUT_CHANNELS * paddedWidth * paddedHeight)
        for (y in 0 until paddedHeight) {
            for (x in 0 until paddedWidth) {
                tensor[y * paddedWidth + x] = if (x < contentWidth && y < contentHeight) {
                    gray[y * contentWidth + x]
                } else {
                    1f
                }
            }
        }
        return tensor
    }

    /** Crops the NCHW `[1, 3, H, W]` model output (RGB in [-1,1]) to the content area as opaque ARGB pixels. */
    fun decodeOutput(
        output: FloatArray,
        paddedWidth: Int,
        paddedHeight: Int,
        contentWidth: Int,
        contentHeight: Int,
    ): IntArray {
        val plane = paddedWidth * paddedHeight
        require(output.size == 3 * plane) { "Unexpected model output size ${output.size}" }
        return IntArray(contentWidth * contentHeight) { i ->
            val index = (i / contentWidth) * paddedWidth + i % contentWidth
            argb(toByte(output[index]), toByte(output[plane + index]), toByte(output[2 * plane + index]))
        }
    }

    private fun toByte(value: Float): Int {
        check(!value.isNaN() && !value.isInfinite()) { "Model output contains NaN or infinity" }
        return ((value * 0.5f + 0.5f) * 255f).roundToInt().coerceIn(0, 255)
    }

    /**
     * Upscales the low-resolution [prediction] to the original size and multiplies it by the ratio between the
     * original grayscale and its low-resolution version, which restores line art and screentones lost by the
     * downscale. Very dark pixels keep their original ink. Writes the result into [pixels] (the original page).
     */
    fun retainInk(
        pixels: IntArray,
        width: Int,
        height: Int,
        lowGray: FloatArray,
        prediction: IntArray,
        contentWidth: Int,
        contentHeight: Int,
    ) {
        val xs = BilinearAxis(contentWidth, width)
        val ys = BilinearAxis(contentHeight, height)
        for (y in 0 until height) {
            val y0 = ys.index0[y] * contentWidth
            val y1 = ys.index1[y] * contentWidth
            val wy = ys.weight[y]
            for (x in 0 until width) {
                val i = y * width + x
                val gray = luminance(pixels[i]) / 255f
                if (gray < INK_DARK_THRESHOLD) {
                    val v = (gray * 255f).roundToInt()
                    pixels[i] = argb(v, v, v)
                    continue
                }
                val x0 = xs.index0[x]
                val x1 = xs.index1[x]
                val wx = xs.weight[x]
                val low = lerp(
                    lerp(lowGray[y0 + x0], lowGray[y0 + x1], wx),
                    lerp(lowGray[y1 + x0], lowGray[y1 + x1], wx),
                    wy,
                )
                val ratio = ((gray + INK_EPSILON) / (low + INK_EPSILON)).coerceIn(0f, INK_MAX_RATIO)
                val p00 = prediction[y0 + x0]
                val p01 = prediction[y0 + x1]
                val p10 = prediction[y1 + x0]
                val p11 = prediction[y1 + x1]
                pixels[i] = argb(
                    channel(p00, p01, p10, p11, 16, wx, wy, ratio),
                    channel(p00, p01, p10, p11, 8, wx, wy, ratio),
                    channel(p00, p01, p10, p11, 0, wx, wy, ratio),
                )
            }
        }
    }

    private fun channel(p00: Int, p01: Int, p10: Int, p11: Int, shift: Int, wx: Float, wy: Float, ratio: Float): Int {
        val top = lerp((p00 shr shift and 0xFF).toFloat(), (p01 shr shift and 0xFF).toFloat(), wx)
        val bottom = lerp((p10 shr shift and 0xFF).toFloat(), (p11 shr shift and 0xFF).toFloat(), wx)
        return (lerp(top, bottom, wy) * ratio).roundToInt().coerceIn(0, 255)
    }

    private fun lerp(a: Float, b: Float, t: Float) = a + (b - a) * t

    fun argb(r: Int, g: Int, b: Int): Int = (0xFF shl 24) or (r shl 16) or (g shl 8) or b

    /** Area (box filter) resampling, the equivalent of OpenCV's INTER_AREA, done separably. */
    fun resizeArea(src: FloatArray, srcWidth: Int, srcHeight: Int, dstWidth: Int, dstHeight: Int): FloatArray {
        val xs = AreaAxis(srcWidth, dstWidth)
        val rows = FloatArray(dstWidth * srcHeight)
        for (y in 0 until srcHeight) {
            val srcRow = y * srcWidth
            val dstRow = y * dstWidth
            for (x in 0 until dstWidth) {
                var sum = 0f
                for (k in xs.start[x] until xs.start[x + 1]) sum += src[srcRow + xs.index[k]] * xs.weight[k]
                rows[dstRow + x] = sum
            }
        }
        val ys = AreaAxis(srcHeight, dstHeight)
        val dst = FloatArray(dstWidth * dstHeight)
        for (y in 0 until dstHeight) {
            val dstRow = y * dstWidth
            for (k in ys.start[y] until ys.start[y + 1]) {
                val srcRow = ys.index[k] * dstWidth
                val weight = ys.weight[k]
                for (x in 0 until dstWidth) dst[dstRow + x] += rows[srcRow + x] * weight
            }
        }
        return dst
    }

    /** Source cells and normalized coverage weights of each destination cell along one axis. */
    private class AreaAxis(srcSize: Int, dstSize: Int) {
        val start = IntArray(dstSize + 1)
        val index: IntArray
        val weight: FloatArray

        init {
            val scale = srcSize.toDouble() / dstSize
            val indices = ArrayList<Int>(srcSize + 2 * dstSize)
            val weights = ArrayList<Float>(srcSize + 2 * dstSize)
            for (d in 0 until dstSize) {
                start[d] = indices.size
                val from = d * scale
                val to = min((d + 1) * scale, srcSize.toDouble())
                var s = floor(from).toInt()
                val end = ceil(to).toInt()
                while (s < end) {
                    val coverage = min(to, s + 1.0) - max(from, s.toDouble())
                    if (coverage > 0) {
                        indices.add(min(s, srcSize - 1))
                        weights.add((coverage / (to - from)).toFloat())
                    }
                    s++
                }
            }
            start[dstSize] = indices.size
            index = indices.toIntArray()
            weight = weights.toFloatArray()
        }
    }

    /** Neighbors and weight of each destination cell for bilinear upscaling with half-pixel centers. */
    private class BilinearAxis(srcSize: Int, dstSize: Int) {
        val index0 = IntArray(dstSize)
        val index1 = IntArray(dstSize)
        val weight = FloatArray(dstSize)

        init {
            val scale = srcSize.toFloat() / dstSize
            for (d in 0 until dstSize) {
                val position = ((d + 0.5f) * scale - 0.5f).coerceIn(0f, (srcSize - 1).toFloat())
                val i0 = position.toInt()
                index0[d] = i0
                index1[d] = min(i0 + 1, srcSize - 1)
                weight[d] = position - i0
            }
        }
    }
}
