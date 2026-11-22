package mihon.feature.colorization

import com.hippo.unifile.UniFile
import dev.zacsweers.metro.AppScope
import dev.zacsweers.metro.Inject
import dev.zacsweers.metro.SingleIn
import eu.kanade.domain.chapter.model.toSChapter
import eu.kanade.tachiyomi.data.download.DownloadProvider
import eu.kanade.tachiyomi.source.Source
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.withContext
import tachiyomi.domain.chapter.model.Chapter
import tachiyomi.domain.manga.model.Manga
import tachiyomi.domain.storage.service.StorageManager
import tachiyomi.source.local.LocalSource
import tachiyomi.source.local.io.Format
import java.util.TreeSet
import java.util.concurrent.ConcurrentHashMap

/**
 * Locates the chapters to colorize and their colorized copies.
 *
 * Colorized copies are CBZ archives kept apart from the downloads, so the originals are never modified and the
 * download cache doesn't see them: `/<root>/colorized/<source>/<manga>/<chapter>.cbz`, using the same names as the
 * downloads.
 */
@Inject
@SingleIn(AppScope::class)
class ColorizationStore(
    private val storageManager: StorageManager,
    private val downloadProvider: DownloadProvider,
    private val preferences: ColorizationPreferences,
) {

    private val _changes = MutableStateFlow(0)

    /** Changes whenever colorized copies are added or removed. */
    val changes: StateFlow<Int> = _changes.asStateFlow()

    // Names of the colorized copies of a manga, so the chapter list doesn't list its directory on every update
    private val colorizedNames = ConcurrentHashMap<String, Set<String>>()

    /**
     * Returns the downloaded chapter directory or archive, or the chapter file for the local source.
     */
    suspend fun findOriginalChapter(chapter: Chapter, manga: Manga, source: Source): UniFile? =
        withContext(Dispatchers.IO) {
            if (source is LocalSource) {
                when (val format = runCatching { source.getFormat(chapter.toSChapter()) }.getOrNull()) {
                    is Format.Directory -> format.file
                    is Format.Archive -> format.file
                    is Format.Epub, null -> null
                }
            } else {
                downloadProvider.findChapterDir(chapter.name, chapter.scanlator, chapter.url, manga.title, source)
            }
        }

    /**
     * Returns the colorized copy of a chapter the reader should open instead of the original, if any.
     */
    suspend fun findColorizedChapterToRead(chapter: Chapter, manga: Manga, source: Source): UniFile? {
        if (!preferences.showColorized.get()) return null
        return withContext(Dispatchers.IO) {
            findMangaDir(manga, source)?.findFile(getFileName(chapter))?.takeIf { it.isFile }
        }
    }

    suspend fun getColorizedChapterIds(chapters: List<Chapter>, manga: Manga, source: Source): Set<Long> {
        val names = colorizedNames.getOrPut(cacheKey(manga, source)) {
            withContext(Dispatchers.IO) {
                findMangaDir(manga, source)?.listFiles().orEmpty()
                    .mapNotNullTo(TreeSet(String.CASE_INSENSITIVE_ORDER)) { file -> file.name?.takeIf { file.isFile } }
            }
        }
        if (names.isEmpty()) return emptySet()
        return chapters.filter { getFileName(it) in names }.mapTo(HashSet()) { it.id }
    }

    /**
     * Creates an empty archive for the colorized copy of a chapter, to be renamed with [commit] once written.
     */
    suspend fun createTempFile(chapter: Chapter, manga: Manga, source: Source): UniFile? =
        withContext(Dispatchers.IO) {
            val mangaDir = storageManager.getColorizedDirectory()
                ?.createDirectory(downloadProvider.getSourceDirName(source))
                ?.createDirectory(downloadProvider.getMangaDirName(manga.title))
                ?: return@withContext null
            val name = getFileName(chapter) + TMP_SUFFIX
            mangaDir.findFile(name)?.delete()
            mangaDir.createFile(name)
        }

    suspend fun commit(tmpFile: UniFile, chapter: Chapter, manga: Manga, source: Source): Boolean =
        withContext(Dispatchers.IO) {
            val name = getFileName(chapter)
            tmpFile.parentFile?.findFile(name)?.delete()
            tmpFile.renameTo(name).also { notifyChanged() }
        }

    suspend fun deleteChapters(chapters: List<Chapter>, manga: Manga, source: Source) {
        withContext(Dispatchers.IO) {
            val mangaDir = findMangaDir(manga, source) ?: return@withContext
            chapters.forEach { mangaDir.findFile(getFileName(it))?.delete() }
            if (mangaDir.listFiles().isNullOrEmpty()) mangaDir.delete()
            notifyChanged()
        }
    }

    suspend fun deleteManga(manga: Manga, source: Source) {
        withContext(Dispatchers.IO) {
            findMangaDir(manga, source)?.delete() ?: return@withContext
            notifyChanged()
        }
    }

    private fun findMangaDir(manga: Manga, source: Source): UniFile? {
        return storageManager.getColorizedDirectory()
            ?.findFile(downloadProvider.getSourceDirName(source))
            ?.findFile(downloadProvider.getMangaDirName(manga.title))
    }

    private fun getFileName(chapter: Chapter): String {
        return downloadProvider.getChapterDirName(chapter.name, chapter.scanlator, chapter.url) + ".cbz"
    }

    private fun cacheKey(manga: Manga, source: Source) = "${source.id}/${manga.title}"

    private fun notifyChanged() {
        colorizedNames.clear()
        _changes.update { it + 1 }
    }

    private companion object {
        const val TMP_SUFFIX = "_tmp"
    }
}
