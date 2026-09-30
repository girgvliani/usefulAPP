package com.liferpg.sync.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.FilterChip
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.liferpg.sync.Api
import com.liferpg.sync.DayLog
import com.liferpg.sync.widget.WidgetCache
import kotlinx.coroutines.launch
import org.json.JSONObject
import java.time.LocalDate

private enum class Kind { Decimal, Whole, YesNo }

private data class Field(val section: String, val key: String, val label: String, val kind: Kind) {
    val id = "$section.$key"
}

/** What the check-in asks, grouped by the server's daily-log sections. */
private val FIELDS = listOf(
    Field("sleep", "hours", "Hours slept", Kind.Decimal),
    Field("sleep", "alcohol", "Alcoholic drinks the evening before", Kind.Whole),
    Field("sleep", "late_caffeine", "Caffeine within 6h of bedtime", Kind.YesNo),
    Field("work", "total", "Hours worked (job, freelance, uni)", Kind.Decimal),
    Field("work", "deep", "Of those, deep-focus hours", Kind.Decimal),
    Field("mind", "learning_min", "Minutes learning something new", Kind.Whole),
    Field("mind", "meditation_min", "Minutes of meditation", Kind.Whole),
    Field("body", "pushups", "Push-ups today", Kind.Whole),
    Field("body", "max_pushups", "Max push-ups in one set (test days)", Kind.Whole),
    Field("body", "strength", "Other strength training", Kind.YesNo),
    Field("body", "outdoor_min", "Minutes outdoors", Kind.Whole),
    Field("body", "shower", "Showered", Kind.YesNo),
    Field("body", "weight_kg", "Weight (kg)", Kind.Decimal),
    Field("social", "interactions", "Meaningful contacts (30+ min)", Kind.Whole),
)

private val SECTION_TITLES = mapOf(
    "sleep" to "😴 Sleep", "work" to "💼 Work", "mind" to "🧠 Mind", "body" to "🏃 Body", "social" to "👥 Social",
)

@Composable
fun CheckInScreen(api: Api) {
    var yesterday by remember { mutableStateOf(false) }
    fun date(): LocalDate = LocalDate.now().let { if (yesterday) it.minusDays(1) else it }
    val log = rememberLoader { api.day(date()) }

    Column {
        Row(Modifier.padding(16.dp, 16.dp, 16.dp, 0.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            listOf(false to "Today", true to "Yesterday").forEach { (isYesterday, label) ->
                FilterChip(
                    selected = yesterday == isYesterday,
                    onClick = { yesterday = isYesterday; log.reload() },
                    label = { Text(label) },
                )
            }
        }
        Box(Modifier.weight(1f)) {
            LoadView(log) { day -> CheckInForm(api, date(), day, onSaved = log::reload) }
        }
    }
}

@Composable
private fun CheckInForm(api: Api, date: LocalDate, log: DayLog?, onSaved: () -> Unit) {
    val manualBefore = remember(log) { FIELDS.associate { it.id to valueOf(log?.manual, it) }.filterValues { it != null } }
    val values = remember(log) { mutableStateMapOf<String, String>().apply { manualBefore.forEach { (id, v) -> put(id, v!!) } } }
    var message by remember(log) { mutableStateOf<String?>(null) }
    var saving by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    val context = LocalContext.current
    val levelState = LocalLevel.current

    Column(Modifier.verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        sleepEstimate(log)?.let { Text(it, color = Rpg.Muted, fontSize = 13.sp) }

        FIELDS.groupBy { it.section }.forEach { (section, fields) ->
            HudCard {
                SectionTitle(SECTION_TITLES.getValue(section))
                fields.forEach { field ->
                    val phone = valueOf(log?.auto, field)
                    when (field.kind) {
                        Kind.YesNo -> YesNoRow(field.label, values[field.id]) { values[field.id] = it }
                        else -> OutlinedTextField(
                            value = values[field.id].orEmpty(),
                            onValueChange = { values[field.id] = it },
                            label = { Text(field.label) },
                            placeholder = phone?.let { { Text("Phone: $it") } },
                            supportingText = phone?.let { { Text("Phone says $it; type to correct it") } },
                            singleLine = true,
                            keyboardOptions = KeyboardOptions(
                                keyboardType = if (field.kind == Kind.Decimal) KeyboardType.Decimal else KeyboardType.Number,
                            ),
                            modifier = Modifier.fillMaxWidth(),
                        )
                    }
                }
            }
        }

        Button(
            onClick = {
                saving = true
                scope.launch {
                    message = try {
                        save(api, date, values, manualBefore.keys)
                        runCatching { WidgetCache.refresh(context) }  // kept streaks turn green on the home screen
                        levelState?.refresh()
                        onSaved()
                        "✅ Saved"
                    } catch (e: Exception) {
                        "❌ ${e.message}"
                    }
                    saving = false
                }
            },
            enabled = !saving,
            modifier = Modifier.fillMaxWidth(),
        ) { Text(if (saving) "Saving…" else "Save check-in") }
        message?.let { Text(it, color = if (it.startsWith("✅")) Rpg.Good else Rpg.Bad) }
    }
}

@Composable
private fun YesNoRow(label: String, value: String?, onChange: (String) -> Unit) {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(label, Modifier.weight(1f))
        FilterChip(selected = value == "true", onClick = { onChange("true") }, label = { Text("Yes") })
        FilterChip(selected = value == "false", onClick = { onChange("false") }, label = { Text("No") })
    }
}

/** Sends every filled-in value as the day's check-in; fields you emptied go back to the phone's value. */
private suspend fun save(api: Api, date: LocalDate, values: Map<String, String>, hadManual: Set<String>) {
    val body = JSONObject()
    for (field in FIELDS) {
        val raw = values[field.id]?.trim().orEmpty()
        if (raw.isEmpty()) continue
        val value: Any = when (field.kind) {
            Kind.Decimal -> raw.replace(',', '.').toDoubleOrNull() ?: error("${field.label}: enter a number")
            Kind.Whole -> raw.toIntOrNull() ?: error("${field.label}: enter a whole number")
            Kind.YesNo -> raw.toBoolean()
        }
        (body.optJSONObject(field.section) ?: JSONObject().also { body.put(field.section, it) }).put(field.key, value)
    }
    if (body.length() > 0) api.saveManual(date, body)
    for (id in hadManual) {
        if (values[id].isNullOrBlank()) {
            val (section, key) = id.split('.')
            api.clearManual(date, section, key)
        }
    }
}

private fun valueOf(section: JSONObject?, field: Field): String? {
    val value = section?.optJSONObject(field.section)?.opt(field.key) ?: return null
    return when (value) {
        is Double -> if (value % 1.0 == 0.0) value.toLong().toString() else value.toString()
        JSONObject.NULL -> null
        else -> value.toString()
    }
}

private fun sleepEstimate(log: DayLog?): String? {
    val sleep = log?.auto?.optJSONObject("sleep") ?: return null
    if (!sleep.has("bed")) return null
    val kind = if (sleep.optBoolean("estimated")) "Phone estimate" else "Measured"
    return "$kind: asleep ${sleep.getString("bed")} → ${sleep.getString("wake")} (${sleep.optDouble("hours")}h)"
}
