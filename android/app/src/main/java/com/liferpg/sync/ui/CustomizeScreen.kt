package com.liferpg.sync.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.liferpg.sync.Api
import com.liferpg.sync.Customization
import kotlinx.coroutines.launch

/**
 * Customization, earned by level: the ladder of what each level unlocks, and the settings for what
 * you've unlocked. Your own screens use your settings; comparisons with others use the standard stats.
 */
@Composable
fun CustomizeScreen(api: Api) {
    val levelState = LocalLevel.current
    val data = rememberLoader { api.customization() }
    var shown by remember { mutableStateOf<Customization?>(null) }
    val scope = rememberCoroutineScope()
    var error by remember { mutableStateOf<String?>(null) }
    var confirmReset by remember { mutableStateOf(false) }

    fun apply(action: suspend () -> Customization) {
        scope.launch {
            runCatching { action() }
                .onSuccess { shown = it; error = null; scope.launch { levelState?.refresh() } }
                .onFailure { error = it.message }
        }
    }

    LoadView(data) { loaded ->
        CustomizeContent(
            shown ?: loaded, error,
            onPartOff = { stat, part, off -> apply { api.setPartOff(stat, part, off) } },
            onReset = { confirmReset = true },
        )
    }
    if (confirmReset) {
        ConfirmDialog(
            "Back to the standard stats?", "Every part you turned off counts again. Your unlocks stay.", "Reset",
            onConfirm = { confirmReset = false; apply { api.resetCustomization() } }, onDismiss = { confirmReset = false },
        )
    }
}

@Composable
internal fun CustomizeContent(
    custom: Customization,
    error: String?,
    onPartOff: (stat: String, part: String, off: Boolean) -> Unit,
    onReset: () -> Unit,
) {
    val partsOff = custom.ladder.firstOrNull { it.key == "parts_off" }
    Column(Modifier.verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Text("CUSTOMIZE", style = MaterialTheme.typography.headlineLarge, color = Rpg.Accent)
        Text(
            "Shape your stats your way. Each level milestone unlocks something new. Leaderboards always use the standard stats, so comparisons stay fair.",
            color = Rpg.Muted, fontSize = 13.sp,
        )
        HudCard {
            Row(verticalAlignment = Alignment.CenterVertically) {
                LvBadge(custom.level, size = 44)
                Column(Modifier.weight(1f).padding(start = 12.dp)) {
                    Text("You're LV ${custom.level}", fontWeight = FontWeight.Black, fontSize = 17.sp)
                    Text(
                        custom.next?.let { "Next unlock at LV ${it.level}: ${it.title}" } ?: "Everything is unlocked",
                        color = Rpg.Muted, fontSize = 13.sp,
                    )
                }
            }
        }

        if (partsOff?.unlocked == true) {
            SectionTitle("Turn parts off · a stat is judged on the parts you keep")
            error?.let { Text("❌ $it", color = Rpg.Bad, fontSize = 13.sp) }
            custom.stats.forEach { stat ->
                val off = custom.off[stat.code].orEmpty()
                HudCard {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(stat.code, Modifier.width(44.dp), color = statColor(stat.code), fontWeight = FontWeight.Black)
                        Text(stat.name, Modifier.weight(1f), fontWeight = FontWeight.Black)
                        if (off.isNotEmpty()) Text("${off.size} off", color = Rpg.Accent, fontSize = 12.sp)
                    }
                    stat.parts.forEach { (part, weight) ->
                        val isOn = part !in off
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Column(Modifier.weight(1f)) {
                                Text(part, fontSize = 14.sp, color = if (isOn) Rpg.Text else Rpg.Muted)
                                Text("counts ${weight.toInt()}", color = Rpg.Muted, fontSize = 11.sp)
                            }
                            Switch(
                                checked = isOn,
                                onCheckedChange = { onPartOff(stat.code, part, !it) },
                                enabled = !isOn || stat.parts.size - off.size > 1,
                                colors = SwitchDefaults.colors(checkedTrackColor = Rpg.Accent),
                            )
                        }
                    }
                }
            }
            if (custom.off.isNotEmpty()) TextButton(onClick = onReset) { Text("Back to the standard stats", color = Rpg.Bad) }
        }

        SectionTitle("Unlocks")
        HudCard {
            custom.ladder.forEach { u ->
                Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.fillMaxWidth()) {
                    Text(if (u.unlocked) "✅" else "🔒", Modifier.width(30.dp), fontSize = 18.sp)
                    Text("LV ${u.level}", Modifier.width(78.dp), fontWeight = FontWeight.Black, color = if (u.unlocked) Rpg.Accent else Rpg.Muted)
                    Column(Modifier.weight(1f)) {
                        Text(u.title, fontWeight = FontWeight.Bold, color = if (u.unlocked) Rpg.Text else Rpg.Muted)
                        Text(
                            u.description + if (u.unlocked && !u.ready) " Arrives in an update." else "",
                            color = Rpg.Muted, fontSize = 12.sp,
                        )
                    }
                }
            }
        }
    }
}
