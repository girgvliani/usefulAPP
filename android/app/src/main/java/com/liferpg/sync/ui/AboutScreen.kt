package com.liferpg.sync.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.key
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.liferpg.sync.Api
import com.liferpg.sync.AppCategories
import com.liferpg.sync.CharacterSheet
import com.liferpg.sync.DayLog
import com.liferpg.sync.FieldCatalog
import com.liferpg.sync.Income
import com.liferpg.sync.LogField
import com.liferpg.sync.Profile
import com.liferpg.sync.widget.WidgetCache
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.launch
import org.json.JSONObject
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.util.Locale

/** Days shown in the strip above a day's values */
private const val STRIP_DAYS = 14

/** Everything the screen needs besides the open day */
internal data class AboutData(
    val catalog: FieldCatalog,
    val profile: Profile,
    val income: Income,
    val sheet: CharacterSheet?,
    val recent: Map<String, DayLog>,
)

/**
 * Everything your stats are built from: your profile, and every value of every day, where it came
 * from (phone or typed in) and which stats read it. Tap a value to correct it, give the phone's back,
 * or delete it.
 */
@Composable
fun AboutScreen(api: Api, onOpen: (Dest) -> Unit) {
    val today = remember { LocalDate.now() }
    val data = rememberLoader {
        coroutineScope {
            val catalog = async { api.fields() }
            val profile = async { api.profile() }
            val income = async { api.income() }
            val sheet = async { runCatching { api.character() }.getOrNull() }
            val recent = async { api.days(today.minusDays(STRIP_DAYS - 1L), today) }
            AboutData(catalog.await(), profile.await(), income.await(), sheet.await(), recent.await())
        }
    }
    var day by rememberSaveable { mutableStateOf(today.toString()) }

    LoadView(data) { about ->
        Column(Modifier.verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Text("ABOUT YOU", style = MaterialTheme.typography.headlineLarge, color = Rpg.Accent)
            Text("Everything your stats are built from. Tap any value to correct it.", color = Rpg.Muted, fontSize = 13.sp)
            ProfileSummary(about, onEdit = { onOpen(Dest.Profile) })

            SectionTitle("Your days")
            DayStrip(LocalDate.parse(day), today, about.recent, onPick = { day = it.toString() })
            key(day) { DayValues(api, about, LocalDate.parse(day), onChanged = data::reload) }
        }
    }
}

@Composable
internal fun ProfileSummary(about: AboutData, onEdit: () -> Unit) {
    val p = about.profile
    val weight = about.recent.toSortedMap().values.reversed()
        .firstNotNullOfOrNull { (it.raw("body", "weight_kg") as? Number)?.toDouble() }
    HudCard {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(p.displayName ?: "Your profile", Modifier.weight(1f), fontWeight = FontWeight.Black, fontSize = 18.sp)
            TextButton(onClick = onEdit) { Text("Edit") }
        }
        InfoGrid(
            listOf(
                "Age" to (p.birthYear?.let { "${LocalDate.now().year - it}" } ?: "–"),
                "Height" to (p.heightCm?.let { "${it.toInt()} cm" } ?: "–"),
                "Weight" to (weight?.let { "${fmtNumber(it)} kg" } ?: "–"),
                "Sex" to (p.sex?.replaceFirstChar { it.uppercase() } ?: "–"),
                "Push-ups / day" to "${p.pushupTarget}",
                "Steps / day" to "%,d".format(p.stepsTarget),
                "Sleep" to "${fmtNumber(p.sleepTarget)} h",
                "Income goal" to (if (about.income.monthlyGoal > 0) "%,d %s".format(about.income.monthlyGoal, p.currency) else "–"),
                "Earned this month" to "%,d %s".format(about.income.earned, p.currency),
            ),
        )
        val missing = listOfNotNull(
            "height".takeIf { p.heightCm == null }, "birth year".takeIf { p.birthYear == null }, "sex".takeIf { p.sex == null },
        )
        if (missing.isNotEmpty()) {
            Text("Add your ${missing.joinToString(", ")} for a calorie target (Health).", color = Rpg.Bad, fontSize = 12.sp)
        }
    }
}

/** Label-value pairs, three to a row */
@Composable
private fun InfoGrid(items: List<Pair<String, String>>) {
    items.chunked(3).forEach { row ->
        Row(Modifier.fillMaxWidth()) {
            row.forEach { (label, value) ->
                Column(Modifier.weight(1f)) {
                    Text(label, color = Rpg.Muted, fontSize = 11.sp)
                    Text(value, fontWeight = FontWeight.Bold, fontSize = 15.sp)
                }
            }
            repeat(3 - row.size) { Box(Modifier.weight(1f)) }
        }
    }
}

/** ‹ date › with a calendar, and the last two weeks as chips (a dot = something logged). */
@Composable
internal fun DayStrip(day: LocalDate, today: LocalDate, recent: Map<String, DayLog>, onPick: (LocalDate) -> Unit) {
    var picking by remember { mutableStateOf(false) }
    Row(verticalAlignment = Alignment.CenterVertically) {
        TextButton(onClick = { onPick(day.minusDays(1)) }) { Text("‹", fontSize = 22.sp, fontWeight = FontWeight.Black) }
        Text(
            "${longDate(day)} · ${relative(day, today)}", Modifier.weight(1f).clickable { picking = true },
            textAlign = TextAlign.Center, fontWeight = FontWeight.Bold,
        )
        TextButton(onClick = { onPick(day.plusDays(1)) }, enabled = day < today) { Text("›", fontSize = 22.sp, fontWeight = FontWeight.Black) }
        TextButton(onClick = { picking = true }) { Text("📅") }
    }
    val dayFormat = remember { DateTimeFormatter.ofPattern("EEE", Locale.ENGLISH) }
    Row(Modifier.horizontalScroll(rememberScrollState(Int.MAX_VALUE)), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
        for (back in STRIP_DAYS - 1 downTo 0) {
            val date = today.minusDays(back.toLong())
            val logged = recent[date.toString()]?.isEmpty == false
            Column(
                Modifier
                    .width(44.dp)
                    .border(1.dp, if (date == day) Rpg.Accent else Rpg.Outline, RoundedCornerShape(12.dp))
                    .background(if (date == day) Rpg.SurfaceHigh else Rpg.Surface, RoundedCornerShape(12.dp))
                    .clickable { onPick(date) }
                    .padding(vertical = 6.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Text(date.format(dayFormat), color = Rpg.Muted, fontSize = 11.sp)
                Text("${date.dayOfMonth}", fontWeight = FontWeight.Black)
                Box(Modifier.size(5.dp).background(if (logged) Rpg.Good else Rpg.Outline, CircleShape))
            }
        }
    }
    if (picking) {
        DatePick(day, today, onPick = { onPick(it); picking = false }, onDismiss = { picking = false })
    }
}

/** One day's values by section; empty ones only on request. */
@Composable
private fun DayValues(api: Api, about: AboutData, day: LocalDate, onChanged: () -> Unit) {
    val context = LocalContext.current
    val levelState = LocalLevel.current
    val scope = rememberCoroutineScope()
    val log = rememberLoader { api.day(day) ?: DayLog(JSONObject(), JSONObject(), JSONObject(), day.toString()) }
    var showEmpty by remember { mutableStateOf(false) }
    var editing by remember { mutableStateOf<LogField?>(null) }
    val names = about.sheet?.stats?.associate { it.code to it.name }.orEmpty()

    LoadView(log) { entry ->
        DayValuesContent(about.catalog, entry, names, showEmpty, onToggleEmpty = { showEmpty = !showEmpty }, onEdit = { editing = it })
    }

    editing?.let { field ->
        val entry = (log.value as? Load.Ready)?.value ?: return@let
        FieldEditor(
            field, entry, day, names,
            onDone = { change ->
                editing = null
                scope.launch {
                    runCatching { change() }
                    log.reload()
                    onChanged()
                    levelState?.refresh()
                    runCatching { WidgetCache.refresh(context) }
                }
            },
            onDismiss = { editing = null },
            api = api,
        )
    }
}

/** A day's values grouped by section, with where each came from and which stats read it. */
@Composable
internal fun DayValuesContent(
    catalog: FieldCatalog,
    entry: DayLog,
    names: Map<String, String>,
    showEmpty: Boolean,
    onToggleEmpty: () -> Unit,
    onEdit: (LogField) -> Unit,
) {
    val context = LocalContext.current
    val categories = remember { AppCategories(context) }
    Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Text("📱 sent by the phone  ·  ✍ typed by you (yours wins)", color = Rpg.Muted, fontSize = 12.sp)
        FilterChip(selected = showEmpty, onClick = onToggleEmpty, label = { Text("Show empty values") })
        if (entry.isEmpty && !showEmpty) {
            HudCard { Text("Nothing logged for this day. Turn on \"Show empty values\" to add something.", color = Rpg.Muted) }
        }
        catalog.sections.forEach { (section, title) ->
            val fields = catalog.fields.filter { it.section == section && (showEmpty || entry.value(it) != null) }
            val apps = if (section == "screen") topApps(entry) { pkg -> runCatching { categories.label(pkg) }.getOrNull() } else emptyList()
            if (fields.isNotEmpty() || apps.isNotEmpty()) {
                HudCard {
                    SectionTitle(title)
                    fields.forEach { FieldRow(it, entry, names) { onEdit(it) } }
                    if (apps.isNotEmpty()) {
                        Text("Top apps", color = Rpg.Muted, fontSize = 12.sp, modifier = Modifier.padding(top = 4.dp))
                        apps.forEach { (app, minutes) ->
                            Row {
                                Text(app, Modifier.weight(1f), fontSize = 13.sp)
                                Text("$minutes min", color = Rpg.Muted, fontSize = 13.sp)
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun FieldRow(field: LogField, entry: DayLog, names: Map<String, String>, onEdit: () -> Unit) {
    val typed = entry.typed(field)
    val phone = entry.phone(field)
    val value = typed ?: phone
    Column(Modifier.fillMaxWidth().clickable(onClick = onEdit).padding(vertical = 4.dp), verticalArrangement = Arrangement.spacedBy(2.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(field.label, Modifier.weight(1f), fontSize = 14.sp)
            Text(
                value?.let { show(field, it) } ?: "–",
                fontWeight = FontWeight.Black, fontSize = 15.sp, color = if (value == null) Rpg.Muted else Rpg.Text,
            )
        }
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(
                when {
                    typed != null && phone != null && typed != phone -> "✍ you · 📱 phone said ${show(field, phone)}"
                    typed != null -> "✍ you"
                    phone != null -> if (field.source == "import") "💻 imported" else "📱 phone"
                    else -> "not logged"
                },
                Modifier.weight(1f), color = Rpg.Muted, fontSize = 11.sp,
            )
            if (field.feeds.isEmpty()) {
                Text("feeds no stat", color = Rpg.Muted, fontSize = 11.sp)
            } else {
                field.feeds.forEach { code ->
                    Text(code, Modifier.padding(start = 6.dp), color = statColor(code), fontSize = 11.sp, fontWeight = FontWeight.Black)
                }
            }
        }
    }
}

/**
 * Correct a value (saved as yours, so it beats the phone), give the phone's value back, or delete it.
 * [onDone] gets the server call to make.
 */
@Composable
private fun FieldEditor(
    field: LogField,
    entry: DayLog,
    day: LocalDate,
    names: Map<String, String>,
    onDone: (suspend () -> Unit) -> Unit,
    onDismiss: () -> Unit,
    api: Api,
) {
    val typed = entry.typed(field)
    val phone = entry.phone(field)
    var text by remember { mutableStateOf((typed ?: phone)?.let { if (field.kind == "yesno") it.toString() else show(field, it, unit = false) }.orEmpty()) }
    var error by remember { mutableStateOf<String?>(null) }
    var confirmDelete by remember { mutableStateOf(false) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(field.label) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(longDate(day), color = Rpg.Muted, fontSize = 13.sp)
                when (field.kind) {
                    "yesno" -> ChoiceChips(listOf("true" to "Yes", "false" to "No"), text) { text = it }
                    else -> TextInput(
                        text, { text = it },
                        when (field.kind) {
                            "time" -> "Time (HH:MM)"
                            else -> if (field.unit.isNotEmpty()) "Value (${field.unit})" else "Value"
                        },
                        numeric = field.kind != "time",
                    )
                }
                phone?.let { Text("📱 Phone: ${show(field, it)}", fontSize = 13.sp) }
                typed?.let { Text("✍ You: ${show(field, it)}", fontSize = 13.sp) }
                Text(
                    if (field.feeds.isEmpty()) "Kept for later; no stat reads it yet."
                    else "Feeds " + field.feeds.joinToString(", ") { names[it] ?: it },
                    color = Rpg.Muted, fontSize = 12.sp,
                )
                if (typed != null && phone != null) {
                    TextButton(onClick = { onDone { api.clearField(day, field.section, field.key, "manual") } }) {
                        Text("Use the phone's value (${show(field, phone)})")
                    }
                }
                if (typed != null || phone != null) {
                    TextButton(onClick = { confirmDelete = true }) { Text("Delete this value", color = Rpg.Bad) }
                }
                error?.let { Text("❌ $it", color = Rpg.Bad, fontSize = 13.sp) }
            }
        },
        confirmButton = {
            TextButton(onClick = {
                val parsed = runCatching { parse(field, text) }
                parsed.exceptionOrNull()?.let { error = it.message; return@TextButton }
                val body = JSONObject().put(field.section, JSONObject().put(field.key, parsed.getOrThrow()))
                onDone { api.saveManual(day, body) }
            }) { Text("Save") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } },
    )
    if (confirmDelete) {
        ConfirmDialog(
            "Delete ${field.label.lowercase()}?",
            "Removes it for ${longDate(day)}" +
                (if (phone != null) ". The phone sends the last two days again on its next sync, so a recent value can come back." else "."),
            "Delete",
            onConfirm = { confirmDelete = false; onDone { api.clearField(day, field.section, field.key, "all") } },
            onDismiss = { confirmDelete = false },
        )
    }
}

private val TIME = Regex("^([01]\\d|2[0-3]):[0-5]\\d$")

/** The typed text as the server wants it, or an error saying what's wrong */
internal fun parse(field: LogField, text: String): Any {
    val raw = text.trim().replace(',', '.')
    require(raw.isNotEmpty()) { "Enter a value, or delete it instead" }
    return when (field.kind) {
        "yesno" -> raw.toBooleanStrictOrNull() ?: error("Pick yes or no")
        "time" -> raw.takeIf { TIME.matches(it) } ?: error("Use HH:MM, e.g. 23:30")
        "whole" -> raw.toIntOrNull()?.takeIf { it >= 0 } ?: error("Enter a whole number")
        else -> raw.toDoubleOrNull()?.takeIf { it >= 0 } ?: error("Enter a number")
    }
}

/** A value as people read it: "Yes", "7.5 h", "9,214" */
internal fun show(field: LogField, value: Any, unit: Boolean = true): String {
    val text = when {
        field.kind == "yesno" -> if (value == true || value.toString() == "true") "Yes" else "No"
        value is Number && field.kind == "whole" -> if (unit) "%,d".format(value.toLong()) else value.toLong().toString()
        value is Number -> fmtNumber(value.toDouble())
        else -> value.toString()
    }
    return if (unit && field.unit.isNotEmpty() && field.kind != "yesno") "$text ${field.unit}" else text
}

private fun fmtNumber(value: Double) = if (value % 1.0 == 0.0) value.toLong().toString() else "%.1f".format(value).trimEnd('0').trimEnd('.')

/** The five apps with the most minutes that day, by name: the phone's label for it if it has one */
private fun topApps(entry: DayLog, label: (String) -> String?): List<Pair<String, Int>> {
    val apps = entry.raw("screen", "apps") as? JSONObject ?: return emptyList()
    return apps.keys().asSequence().map { it to apps.optInt(it) }.filter { it.second > 0 }
        .sortedByDescending { it.second }.take(5)
        .map { (pkg, minutes) -> (label(pkg) ?: appName(pkg)) to minutes }.toList()
}

/** Apps whose package names say little about them */
private val KNOWN_APPS = mapOf(
    "com.zhiliaoapp.musically" to "TikTok", "com.ss.android.ugc.trill" to "TikTok", "com.facebook.katana" to "Facebook",
    "com.facebook.orca" to "Messenger", "org.telegram.messenger" to "Telegram", "com.twitter.android" to "X",
    "com.google.android.youtube" to "YouTube", "com.android.chrome" to "Chrome", "com.whatsapp" to "WhatsApp",
    "com.snapchat.android" to "Snapchat", "com.reddit.frontpage" to "Reddit", "com.sec.android.app.sbrowser" to "Samsung Internet",
)

/**
 * A readable name for an app the phone can't name (e.g. uninstalled since):
 * com.instagram.android → Instagram
 */
internal fun appName(pkg: String): String {
    KNOWN_APPS[pkg]?.let { return it }
    val parts = pkg.split('.').filter { it !in setOf("com", "android", "app", "apps", "google", "org", "net", "mobile") }
    return (parts.lastOrNull() ?: pkg).replaceFirstChar { it.uppercase() }
}
