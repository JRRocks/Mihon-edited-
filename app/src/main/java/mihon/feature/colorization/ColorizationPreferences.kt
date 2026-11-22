package mihon.feature.colorization

import dev.zacsweers.metro.AppScope
import dev.zacsweers.metro.Inject
import dev.zacsweers.metro.SingleIn
import tachiyomi.core.common.preference.Preference
import tachiyomi.core.common.preference.PreferenceStore
import tachiyomi.core.common.preference.getEnum

@Inject
@SingleIn(AppScope::class)
class ColorizationPreferences(preferenceStore: PreferenceStore) {

    val engine: Preference<Engine> = preferenceStore.getEnum("colorization_engine", Engine.ON_DEVICE)

    /** Longest side, in pixels, of the image fed to the on-device model. */
    val onDeviceResolution: Preference<Int> = preferenceStore.getInt("colorization_on_device_resolution", 576)

    /** Base URL of a colorization server, e.g. `http://192.168.1.10:8765`. */
    val serverUrl: Preference<String> = preferenceStore.getString("colorization_server_url", "")

    /** Longest side, in pixels, of the image sent to the colorization server. */
    val serverResolution: Preference<Int> = preferenceStore.getInt("colorization_server_resolution", 768)

    /** Whether the reader opens the colorized copy of a chapter instead of the original when there is one. */
    val showColorized: Preference<Boolean> = preferenceStore.getBoolean("colorization_show_colorized", true)

    enum class Engine {
        ON_DEVICE,
        SERVER,
    }
}
