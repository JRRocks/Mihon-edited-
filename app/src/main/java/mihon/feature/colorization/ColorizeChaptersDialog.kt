package mihon.feature.colorization

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.unit.dp
import mihon.icons.materialsymbols.MaterialSymbols
import mihon.icons.materialsymbols.rounded.Palette
import tachiyomi.i18n.MR
import tachiyomi.presentation.core.i18n.pluralStringResource
import tachiyomi.presentation.core.i18n.stringResource

@Composable
fun ColorizeChaptersDialog(
    chapterCount: Int,
    colorizedCount: Int,
    engine: ColorizationPreferences.Engine,
    needsModelDownload: Boolean,
    isServerMissing: Boolean,
    onDismissRequest: () -> Unit,
    onColorize: () -> Unit,
    onRemoveColorization: () -> Unit,
    onOpenSettings: () -> Unit,
) {
    AlertDialog(
        onDismissRequest = onDismissRequest,
        icon = { Icon(imageVector = MaterialSymbols.Rounded.Palette, contentDescription = null) },
        title = { Text(text = stringResource(MR.strings.colorization_dialog_title)) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(text = pluralStringResource(MR.plurals.colorization_dialog_chapters, chapterCount, chapterCount))
                Text(
                    text = stringResource(
                        MR.strings.colorization_dialog_engine,
                        stringResource(
                            when (engine) {
                                ColorizationPreferences.Engine.ON_DEVICE -> MR.strings.colorization_engine_on_device
                                ColorizationPreferences.Engine.SERVER -> MR.strings.colorization_engine_server
                            },
                        ),
                    ),
                    style = MaterialTheme.typography.bodySmall,
                )
                if (needsModelDownload) {
                    Text(
                        text = stringResource(MR.strings.colorization_dialog_model_download),
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
                if (colorizedCount > 0) {
                    Text(
                        text = pluralStringResource(
                            MR.plurals.colorization_dialog_already_colorized,
                            colorizedCount,
                            colorizedCount,
                        ),
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
                if (isServerMissing) {
                    Text(
                        text = stringResource(MR.strings.colorization_server_url_missing),
                        color = MaterialTheme.colorScheme.error,
                    )
                }
            }
        },
        dismissButton = {
            Row {
                if (colorizedCount > 0) {
                    TextButton(
                        onClick = {
                            onDismissRequest()
                            onRemoveColorization()
                        },
                    ) {
                        Text(text = stringResource(MR.strings.action_remove_colorization))
                    }
                }
                TextButton(onClick = onDismissRequest) {
                    Text(text = stringResource(MR.strings.action_cancel))
                }
            }
        },
        confirmButton = {
            if (isServerMissing) {
                TextButton(
                    onClick = {
                        onDismissRequest()
                        onOpenSettings()
                    },
                ) {
                    Text(text = stringResource(MR.strings.label_settings))
                }
            } else {
                TextButton(
                    onClick = {
                        onDismissRequest()
                        onColorize()
                    },
                ) {
                    Text(text = stringResource(MR.strings.action_colorize))
                }
            }
        },
    )
}
