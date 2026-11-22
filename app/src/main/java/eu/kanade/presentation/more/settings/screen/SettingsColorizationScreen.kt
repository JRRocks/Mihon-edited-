package eu.kanade.presentation.more.settings.screen

import androidx.compose.runtime.Composable
import androidx.compose.runtime.ReadOnlyComposable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import eu.kanade.presentation.more.settings.Preference
import eu.kanade.tachiyomi.util.system.toast
import kotlinx.coroutines.launch
import logcat.LogPriority
import mihon.app.di.appGraph
import mihon.feature.colorization.ColorizationPreferences
import mihon.feature.colorization.RemoteColorizationEngine
import tachiyomi.core.common.i18n.stringResource
import tachiyomi.core.common.util.system.logcat
import tachiyomi.i18n.MR
import tachiyomi.presentation.core.i18n.stringResource
import tachiyomi.presentation.core.util.collectAsState

object SettingsColorizationScreen : SearchableSettings {

    @ReadOnlyComposable
    @Composable
    override fun getTitleRes() = MR.strings.pref_category_colorization

    @Composable
    override fun getPreferences(): List<Preference> {
        val context = LocalContext.current
        val preferences = remember { context.appGraph.colorizationPreferences }
        val engine by preferences.engine.collectAsState()

        return listOf(
            Preference.PreferenceItem.InfoPreference(stringResource(MR.strings.pref_colorization_info)),
            Preference.PreferenceItem.SwitchPreference(
                preference = preferences.showColorized,
                title = stringResource(MR.strings.pref_colorization_show_colorized),
                subtitle = stringResource(MR.strings.pref_colorization_show_colorized_summary),
            ),
            Preference.PreferenceItem.ListPreference(
                preference = preferences.engine,
                entries = mapOf(
                    ColorizationPreferences.Engine.ON_DEVICE to stringResource(
                        MR.strings.colorization_engine_on_device,
                    ),
                    ColorizationPreferences.Engine.SERVER to stringResource(MR.strings.colorization_engine_server),
                ),
                title = stringResource(MR.strings.pref_colorization_engine),
            ),
            getOnDeviceGroup(preferences, visible = engine == ColorizationPreferences.Engine.ON_DEVICE),
            getServerGroup(preferences, visible = engine == ColorizationPreferences.Engine.SERVER),
        )
    }

    @Composable
    private fun getOnDeviceGroup(preferences: ColorizationPreferences, visible: Boolean): Preference.PreferenceGroup {
        val context = LocalContext.current
        val scope = rememberCoroutineScope()
        val modelManager = remember { context.appGraph.colorizationModelManager }
        val isDownloaded by modelManager.isDownloaded.collectAsState()
        var downloadProgress by remember { mutableStateOf<Int?>(null) }

        return Preference.PreferenceGroup(
            title = stringResource(MR.strings.colorization_engine_on_device),
            visible = visible,
            preferenceItems = listOf(
                Preference.PreferenceItem.ListPreference(
                    preference = preferences.onDeviceResolution,
                    entries = mapOf(
                        384 to stringResource(MR.strings.colorization_resolution_fast, 384),
                        576 to stringResource(MR.strings.colorization_resolution_balanced, 576),
                        768 to stringResource(MR.strings.colorization_resolution_detailed, 768),
                    ),
                    title = stringResource(MR.strings.pref_colorization_resolution),
                ),
                Preference.PreferenceItem.TextPreference(
                    title = stringResource(MR.strings.pref_colorization_model),
                    subtitle = when {
                        downloadProgress != null -> {
                            stringResource(MR.strings.colorization_model_downloading, downloadProgress!!)
                        }
                        isDownloaded -> stringResource(MR.strings.colorization_model_downloaded)
                        else -> stringResource(MR.strings.colorization_model_not_downloaded)
                    },
                    onClick = {
                        when {
                            downloadProgress != null -> {}
                            isDownloaded -> modelManager.delete()
                            else -> scope.launch {
                                downloadProgress = 0
                                try {
                                    modelManager.ensureDownloaded { downloadProgress = it }
                                } catch (e: Exception) {
                                    logcat(LogPriority.ERROR, e)
                                    context.toast(e.message ?: e.javaClass.simpleName)
                                } finally {
                                    downloadProgress = null
                                }
                            }
                        }
                    },
                ),
            ),
        )
    }

    @Composable
    private fun getServerGroup(preferences: ColorizationPreferences, visible: Boolean): Preference.PreferenceGroup {
        val context = LocalContext.current
        val scope = rememberCoroutineScope()
        val serverUrl by preferences.serverUrl.collectAsState()

        return Preference.PreferenceGroup(
            title = stringResource(MR.strings.colorization_engine_server),
            visible = visible,
            preferenceItems = listOf(
                Preference.PreferenceItem.EditTextPreference(
                    preference = preferences.serverUrl,
                    title = stringResource(MR.strings.pref_colorization_server_url),
                    subtitle = if (serverUrl.isBlank()) {
                        stringResource(MR.strings.pref_colorization_server_url_empty)
                    } else {
                        "%s"
                    },
                    onValueChanged = { url ->
                        url.isBlank() || url.trim().startsWith("http://") || url.trim().startsWith("https://")
                    },
                ),
                Preference.PreferenceItem.ListPreference(
                    preference = preferences.serverResolution,
                    entries = mapOf(
                        576 to stringResource(MR.strings.colorization_resolution_fast, 576),
                        768 to stringResource(MR.strings.colorization_resolution_balanced, 768),
                        1024 to stringResource(MR.strings.colorization_resolution_detailed, 1024),
                    ),
                    title = stringResource(MR.strings.pref_colorization_resolution),
                ),
                Preference.PreferenceItem.TextPreference(
                    title = stringResource(MR.strings.pref_colorization_server_test),
                    onClick = {
                        scope.launch {
                            try {
                                RemoteColorizationEngine.ping(context.appGraph.networkHelper.client, serverUrl)
                                context.toast(MR.strings.colorization_server_ok)
                            } catch (e: Exception) {
                                context.toast(
                                    context.stringResource(
                                        MR.strings.colorization_server_error,
                                        e.message ?: e.javaClass.simpleName,
                                    ),
                                )
                            }
                        }
                    },
                ),
                Preference.PreferenceItem.InfoPreference(stringResource(MR.strings.pref_colorization_server_info)),
            ),
        )
    }
}
