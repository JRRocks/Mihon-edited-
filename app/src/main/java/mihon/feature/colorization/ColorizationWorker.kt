package mihon.feature.colorization

import android.content.Context
import android.content.pm.ServiceInfo
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.work.CoroutineWorker
import androidx.work.ExistingWorkPolicy
import androidx.work.ForegroundInfo
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import androidx.work.workDataOf
import com.hippo.unifile.UniFile
import dev.zacsweers.metro.Inject
import eu.kanade.tachiyomi.R
import eu.kanade.tachiyomi.data.notification.Notifications
import eu.kanade.tachiyomi.network.NetworkHelper
import eu.kanade.tachiyomi.util.lang.compareToCaseInsensitiveNaturalOrder
import eu.kanade.tachiyomi.util.system.cancelNotification
import eu.kanade.tachiyomi.util.system.notificationBuilder
import eu.kanade.tachiyomi.util.system.notify
import eu.kanade.tachiyomi.util.system.setForegroundSafely
import eu.kanade.tachiyomi.util.system.workManager
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.withContext
import logcat.LogPriority
import mihon.app.di.AppGraph
import mihon.core.archive.archiveReader
import mihon.core.metro.metroGraph
import tachiyomi.core.common.i18n.stringResource
import tachiyomi.core.common.util.system.ImageUtil
import tachiyomi.core.common.util.system.logcat
import tachiyomi.domain.chapter.interactor.GetChapter
import tachiyomi.domain.chapter.model.Chapter
import tachiyomi.domain.manga.interactor.GetManga
import tachiyomi.domain.source.service.SourceManager
import tachiyomi.i18n.MR
import java.io.File
import java.util.zip.CRC32
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream
import kotlin.time.measureTimedValue
import mihon.icons.materialsymbols.R as MaterialSymbolsR

/**
 * Colorizes downloaded chapters, one after the other, into separate archives.
 */
class ColorizationWorker(private val context: Context, workerParams: WorkerParameters) :
    CoroutineWorker(context, workerParams) {

    private val graph: AppGraph = context.metroGraph()

    @Inject private lateinit var preferences: ColorizationPreferences

    @Inject private lateinit var store: ColorizationStore

    @Inject private lateinit var modelManager: ColorizationModelManager

    @Inject private lateinit var networkHelper: NetworkHelper

    @Inject private lateinit var getChapter: GetChapter

    @Inject private lateinit var getManga: GetManga

    @Inject private lateinit var sourceManager: SourceManager

    private val progressNotificationBuilder by lazy {
        context.notificationBuilder(Notifications.CHANNEL_COLORIZATION) {
            setSmallIcon(R.drawable.ic_mihon)
            setContentTitle(context.stringResource(MR.strings.colorization_notification_title))
            setOngoing(true)
            setOnlyAlertOnce(true)
            addAction(
                MaterialSymbolsR.drawable.rounded_close,
                context.stringResource(MR.strings.action_cancel),
                WorkManager.getInstance(context).createCancelPendingIntent(id),
            )
        }
    }

    override suspend fun doWork(): Result {
        graph.inject(this)
        val chapterIds = inputData.getLongArray(KEY_CHAPTER_IDS) ?: return Result.success()

        setForegroundSafely()

        return withContext(Dispatchers.IO) {
            var colorizedCount = 0
            try {
                createEngine().use { engine ->
                    val pageColorizer = PageColorizer(engine)
                    chapterIds.forEachIndexed { index, chapterId ->
                        ensureActive()
                        if (colorizeChapter(pageColorizer, chapterId, index, chapterIds.size)) colorizedCount++
                    }
                }
                context.cancelNotification(Notifications.ID_COLORIZATION_PROGRESS)
                showCompleteNotification(colorizedCount)
                Result.success()
            } catch (e: Throwable) {
                context.cancelNotification(Notifications.ID_COLORIZATION_PROGRESS)
                if (e is CancellationException) {
                    Result.success()
                } else {
                    logcat(LogPriority.ERROR, e) { "Colorization failed" }
                    showErrorNotification(e)
                    Result.failure()
                }
            }
        }
    }

    override suspend fun getForegroundInfo(): ForegroundInfo {
        return ForegroundInfo(
            Notifications.ID_COLORIZATION_PROGRESS,
            progressNotificationBuilder.build(),
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC
            } else {
                0
            },
        )
    }

    private suspend fun createEngine(): ColorizationEngine {
        return when (preferences.engine.get()) {
            ColorizationPreferences.Engine.ON_DEVICE -> {
                val model = modelManager.ensureDownloaded { percent ->
                    showProgress(context.stringResource(MR.strings.colorization_downloading_model), percent, 100)
                }
                val (engine, duration) = measureTimedValue {
                    OnDeviceColorizationEngine(model, preferences.onDeviceResolution.get())
                }
                logcat { "Colorization model loaded in $duration" }
                engine
            }
            ColorizationPreferences.Engine.SERVER -> {
                val url = preferences.serverUrl.get()
                require(url.isNotBlank()) { context.stringResource(MR.strings.colorization_server_url_missing) }
                RemoteColorizationEngine(networkHelper.client, url, preferences.serverResolution.get())
            }
        }
    }

    /**
     * Returns whether the chapter was colorized; chapters no longer downloaded are skipped.
     */
    private suspend fun colorizeChapter(colorizer: PageColorizer, chapterId: Long, index: Int, total: Int): Boolean {
        val chapter = getChapter.await(chapterId) ?: return false
        val manga = getManga.await(chapter.mangaId) ?: return false
        val source = sourceManager.getOrStub(manga.source)
        val original = store.findOriginalChapter(chapter, manga, source) ?: return false
        val tmpFile = store.createTempFile(chapter, manga, source)
            ?: throw IllegalStateException(context.stringResource(MR.strings.colorization_storage_error))

        val title = context.stringResource(MR.strings.colorization_chapter_progress, index + 1, total, manga.title)
        try {
            showProgress(title + "\n" + chapter.name, 0, 1)
            readPages(original) { pages ->
                writeArchive(tmpFile, pages.size) { addPage ->
                    pages.forEachIndexed { pageIndex, (name, readBytes) ->
                        currentCoroutineContext().ensureActive()
                        showProgress(title + "\n" + chapter.name, pageIndex, pages.size)
                        val bytes = readBytes()
                        val (colorized, duration) = measureTimedValue { colorizer.colorize(bytes, manga.title) }
                        logcat { "Colorized $name in $duration" }
                        if (colorized != null) {
                            addPage(File(name).nameWithoutExtension + ".jpg", colorized)
                        } else {
                            addPage(name, bytes)
                        }
                    }
                }
            }
        } catch (e: Throwable) {
            tmpFile.delete()
            throw e
        }
        if (!store.commit(tmpFile, chapter, manga, source)) {
            tmpFile.delete()
            throw IllegalStateException(context.stringResource(MR.strings.colorization_storage_error))
        }
        return true
    }

    /**
     * Gives the images of a chapter directory or archive, in reading order, as name and content.
     */
    private suspend fun <T> readPages(
        chapter: UniFile,
        block: suspend (List<Pair<String, () -> ByteArray>>) -> T,
    ): T {
        // Same order as the reader's page loaders
        val order = Comparator<String> { a, b -> a.compareToCaseInsensitiveNaturalOrder(b) }
        if (chapter.isDirectory) {
            val pages = chapter.listFiles().orEmpty()
                .filter { it.isFile && ImageUtil.isImage(it.name) { it.openInputStream() } }
                .sortedWith(compareBy(order) { it.name.orEmpty() })
                .map { file -> file.name.orEmpty() to { file.openInputStream().use { it.readBytes() } } }
            return block(pages)
        }
        return chapter.archiveReader(context).use { reader ->
            val entryNames = reader.useEntries { entries ->
                entries
                    .filter { it.isFile && ImageUtil.isImage(it.name) { reader.getInputStream(it.name)!! } }
                    .map { it.name }
                    .toList()
            }
            val pages = entryNames
                .sortedWith(order)
                .map { name ->
                    name.substringAfterLast('/') to { reader.getInputStream(name)!!.use { it.readBytes() } }
                }
            block(pages)
        }
    }

    /**
     * Writes an uncompressed zip, as images don't compress further.
     */
    private suspend fun writeArchive(
        file: UniFile,
        pageCount: Int,
        block: suspend (addPage: (String, ByteArray) -> Unit) -> Unit,
    ) {
        val usedNames = HashSet<String>(pageCount)
        ZipOutputStream(file.openOutputStream().buffered()).use { zip ->
            block { name, bytes ->
                // Two originals can end up with the same name once converted to JPEG
                var entryName = name
                var suffix = 1
                while (!usedNames.add(entryName.lowercase())) {
                    entryName = File(name).nameWithoutExtension + "_${suffix++}." + File(name).extension
                }
                val entry = ZipEntry(entryName).apply {
                    method = ZipEntry.STORED
                    size = bytes.size.toLong()
                    compressedSize = bytes.size.toLong()
                    crc = CRC32().apply { update(bytes) }.value
                }
                zip.putNextEntry(entry)
                zip.write(bytes)
                zip.closeEntry()
            }
        }
    }

    private fun showProgress(text: String, current: Int, total: Int) {
        context.notify(
            Notifications.ID_COLORIZATION_PROGRESS,
            progressNotificationBuilder
                .setContentText(text)
                .setStyle(NotificationCompat.BigTextStyle().bigText(text))
                .setProgress(total, current, false)
                .build(),
        )
    }

    private fun showCompleteNotification(count: Int) {
        context.notify(Notifications.ID_COLORIZATION_COMPLETE, Notifications.CHANNEL_COLORIZATION) {
            setSmallIcon(R.drawable.ic_mihon)
            setContentTitle(context.stringResource(MR.strings.colorization_notification_title))
            setContentText(context.stringResource(MR.strings.colorization_complete, count))
            setAutoCancel(true)
        }
    }

    private fun showErrorNotification(error: Throwable) {
        context.notify(Notifications.ID_COLORIZATION_COMPLETE, Notifications.CHANNEL_COLORIZATION) {
            setSmallIcon(MaterialSymbolsR.drawable.rounded_filled_warning)
            setContentTitle(context.stringResource(MR.strings.colorization_error))
            setContentText(error.message ?: error.javaClass.simpleName)
            setAutoCancel(true)
        }
    }

    companion object {
        private const val TAG = "Colorization"
        private const val KEY_CHAPTER_IDS = "chapter_ids"

        // Work data is limited to 10 KB
        private const val CHAPTERS_PER_REQUEST = 500

        /**
         * Queues the colorization of the given chapters after any colorization already running.
         */
        fun start(context: Context, chapters: List<Chapter>) {
            chapters.map { it.id }.chunked(CHAPTERS_PER_REQUEST).forEach { ids ->
                val request = OneTimeWorkRequestBuilder<ColorizationWorker>()
                    .addTag(TAG)
                    .setInputData(workDataOf(KEY_CHAPTER_IDS to ids.toLongArray()))
                    .build()
                context.workManager.enqueueUniqueWork(TAG, ExistingWorkPolicy.APPEND_OR_REPLACE, request)
            }
        }
    }
}
