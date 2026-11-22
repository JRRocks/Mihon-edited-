package mihon.feature.colorization

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import eu.kanade.tachiyomi.network.GET
import eu.kanade.tachiyomi.network.POST
import eu.kanade.tachiyomi.network.awaitSuccess
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.Headers
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.ByteArrayOutputStream
import java.io.Closeable
import java.io.File
import java.io.IOException
import java.net.URLEncoder
import java.nio.FloatBuffer
import java.util.concurrent.TimeUnit

/**
 * Runs the colorization model on a page already downscaled by [ColorizationPipeline].
 */
interface ColorizationEngine : Closeable {

    /** Longest side, in pixels, of the images given to [predict]. */
    val longSide: Int

    /**
     * Colorizes a grayscale image in [0,1] of [width]x[height] pixels and returns its opaque ARGB pixels.
     * [series] is the title of the manga, which the colorization server uses to keep one palette per series.
     */
    suspend fun predict(gray: FloatArray, width: Int, height: Int, series: String? = null): IntArray
}

/**
 * Runs the model on the device's CPU with ONNX Runtime.
 */
class OnDeviceColorizationEngine(modelFile: File, override val longSide: Int) : ColorizationEngine {

    private val environment = OrtEnvironment.getEnvironment()
    private val session = OrtSession.SessionOptions().use { options ->
        options.setIntraOpNumThreads(Runtime.getRuntime().availableProcessors().coerceIn(1, 4))
        options.setInterOpNumThreads(1)
        options.setExecutionMode(OrtSession.SessionOptions.ExecutionMode.SEQUENTIAL)
        options.setOptimizationLevel(OrtSession.SessionOptions.OptLevel.ALL_OPT)
        // Spinning threads only burn battery between pages
        options.addConfigEntry("session.intra_op.allow_spinning", "0")
        options.addConfigEntry("session.inter_op.allow_spinning", "0")
        environment.createSession(modelFile.absolutePath, options)
    }

    override suspend fun predict(gray: FloatArray, width: Int, height: Int, series: String?): IntArray = withContext(
        Dispatchers.Default,
    ) {
        val paddedWidth = ColorizationPipeline.paddedSize(width)
        val paddedHeight = ColorizationPipeline.paddedSize(height)
        val input = ColorizationPipeline.buildInputTensor(gray, width, height)
        val shape =
            longArrayOf(1, ColorizationPipeline.INPUT_CHANNELS.toLong(), paddedHeight.toLong(), paddedWidth.toLong())
        OnnxTensor.createTensor(environment, FloatBuffer.wrap(input), shape).use { tensor ->
            session.run(mapOf(INPUT_NAME to tensor)).use { result ->
                val buffer = (result[0] as OnnxTensor).floatBuffer
                val output = FloatArray(buffer.remaining()).also { buffer.get(it) }
                ColorizationPipeline.decodeOutput(output, paddedWidth, paddedHeight, width, height)
            }
        }
    }

    override fun close() {
        session.close()
    }

    private companion object {
        const val INPUT_NAME = "sketch_and_hints"
    }
}

/**
 * Sends the page to a colorization server (tools/colorization-server) on the local network or online, which
 * answers with the colorized image as a PNG of the same size.
 */
class RemoteColorizationEngine(
    client: OkHttpClient,
    baseUrl: String,
    override val longSide: Int,
) : ColorizationEngine {

    private val client = client.newBuilder()
        .readTimeout(2, TimeUnit.MINUTES)
        .callTimeout(5, TimeUnit.MINUTES)
        .build()

    private val url = baseUrl.trim().trimEnd('/') + "/colorize"

    override suspend fun predict(gray: FloatArray, width: Int, height: Int, series: String?): IntArray {
        val png = withContext(Dispatchers.Default) {
            val pixels = IntArray(gray.size) {
                val v = (gray[it] * 255f).toInt().coerceIn(0, 255)
                ColorizationPipeline.argb(v, v, v)
            }
            val bitmap = Bitmap.createBitmap(pixels, width, height, Bitmap.Config.ARGB_8888)
            ByteArrayOutputStream().use {
                bitmap.compress(Bitmap.CompressFormat.PNG, 100, it)
                bitmap.recycle()
                it.toByteArray()
            }
        }
        // Headers are ASCII only: the title is percent-encoded
        val headers = Headers.Builder().apply {
            if (!series.isNullOrBlank()) add(SERIES_HEADER, URLEncoder.encode(series, Charsets.UTF_8.name()))
        }.build()
        val bytes = withContext(Dispatchers.IO) {
            client.newCall(POST(url, headers, png.toRequestBody(PNG_MEDIA_TYPE)))
                .awaitSuccess()
                .use { it.body.bytes() }
        }
        return withContext(Dispatchers.Default) {
            val bitmap = BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
                ?: throw IOException("The colorization server returned an invalid image")
            try {
                if (bitmap.width != width || bitmap.height != height) {
                    throw IOException("The colorization server returned an image of the wrong size")
                }
                IntArray(width * height).also { bitmap.getPixels(it, 0, width, 0, 0, width, height) }
            } finally {
                bitmap.recycle()
            }
        }
    }

    override fun close() {}

    companion object {
        private val PNG_MEDIA_TYPE = "image/png".toMediaType()
        private const val SERIES_HEADER = "X-Series-Title"

        /** Checks that a colorization server answers at [baseUrl]. */
        suspend fun ping(client: OkHttpClient, baseUrl: String) {
            withContext(Dispatchers.IO) {
                client.newCall(GET(baseUrl.trim().trimEnd('/') + "/")).awaitSuccess().use { response ->
                    if ("manga-colorization" !in response.body.string()) {
                        throw IOException("Not a colorization server")
                    }
                }
            }
        }
    }
}
