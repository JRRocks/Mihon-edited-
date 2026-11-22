package mihon.feature.colorization

import android.content.Context
import dev.zacsweers.metro.AppScope
import dev.zacsweers.metro.Inject
import dev.zacsweers.metro.SingleIn
import eu.kanade.tachiyomi.network.GET
import eu.kanade.tachiyomi.network.NetworkHelper
import eu.kanade.tachiyomi.network.ProgressListener
import eu.kanade.tachiyomi.network.awaitSuccess
import eu.kanade.tachiyomi.network.newCachelessCallWithProgress
import eu.kanade.tachiyomi.util.storage.saveTo
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.withContext
import java.io.File
import java.io.IOException
import java.security.MessageDigest
import java.util.concurrent.TimeUnit

/**
 * Downloads and keeps the on-device colorization model in the app's private storage. The model isn't bundled with
 * the app: it's only downloaded the first time the user asks for an on-device colorization.
 */
@Inject
@SingleIn(AppScope::class)
class ColorizationModelManager(
    context: Context,
    private val networkHelper: NetworkHelper,
) {

    val modelFile = File(context.filesDir, "colorization/$MODEL_FILE_NAME")

    private val _isDownloaded = MutableStateFlow(isValidSize())
    val isDownloaded: StateFlow<Boolean> = _isDownloaded.asStateFlow()

    private fun isValidSize() = modelFile.length() == MODEL_BYTES

    /**
     * Downloads the model if it's missing, reporting the progress in percent.
     *
     * @throws IOException if the download fails or the file doesn't match the expected checksum.
     */
    suspend fun ensureDownloaded(onProgress: (Int) -> Unit = {}): File = withContext(Dispatchers.IO) {
        if (isValidSize()) return@withContext modelFile

        modelFile.parentFile?.mkdirs()
        val tmpFile = File(modelFile.path + ".tmp")
        try {
            val listener = object : ProgressListener {
                override fun update(bytesRead: Long, contentLength: Long, done: Boolean) {
                    val total = contentLength.takeIf { it > 0 } ?: MODEL_BYTES
                    onProgress((100 * bytesRead / total).toInt().coerceIn(0, 100))
                }
            }
            val client = networkHelper.client.newBuilder()
                .callTimeout(30, TimeUnit.MINUTES)
                .build()
            client.newCachelessCallWithProgress(GET(MODEL_URL), listener)
                .awaitSuccess()
                .body.source()
                .saveTo(tmpFile)

            if (tmpFile.length() != MODEL_BYTES || tmpFile.sha256() != MODEL_SHA256) {
                throw IOException("Corrupted colorization model download")
            }
            if (!tmpFile.renameTo(modelFile)) throw IOException("Couldn't save the colorization model")
        } finally {
            tmpFile.delete()
            _isDownloaded.value = isValidSize()
        }
        modelFile
    }

    fun delete() {
        modelFile.delete()
        _isDownloaded.value = false
    }

    private fun File.sha256(): String {
        val digest = MessageDigest.getInstance("SHA-256")
        inputStream().use { input ->
            val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
            while (true) {
                val read = input.read(buffer)
                if (read < 0) break
                digest.update(buffer, 0, read)
            }
        }
        return digest.digest().joinToString("") { "%02x".format(it) }
    }

    companion object {
        /**
         * INT8 ONNX export of the manga-colorization-v2 generator (https://github.com/qweasdd/manga-colorization-v2),
         * pinned to a commit and verified after download.
         */
        private const val MODEL_URL = "https://huggingface.co/lookx2/manga-colorization/resolve/" +
            "9b421e3e89598aa3563be53f94cfd58b65b49702/manga-colorizer-int8.onnx"
        private const val MODEL_FILE_NAME = "manga-colorizer-int8.onnx"
        private const val MODEL_SHA256 = "cbf5f19c289107f37de2add52b03c6ed713800a33ac2baf80ad3188c22c152f3"
        const val MODEL_BYTES = 32_536_990L
    }
}
