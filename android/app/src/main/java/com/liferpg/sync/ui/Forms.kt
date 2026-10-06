package com.liferpg.sync.ui

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.DatePicker
import androidx.compose.material3.DatePickerDialog
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.SelectableDates
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberDatePickerState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.launch
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter
import java.time.temporal.ChronoUnit
import java.util.Locale

/** A Plan screen: big title, an add button, a one-line explanation, then [content]. */
@Composable
internal fun PlanPage(title: String, subtitle: String, addLabel: String?, onAdd: () -> Unit, content: @Composable ColumnScope.() -> Unit) {
    Column(Modifier.verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(title.uppercase(), Modifier.weight(1f), style = MaterialTheme.typography.headlineLarge, color = Rpg.Accent)
            if (addLabel != null) Button(onClick = onAdd) { Text(addLabel) }
        }
        Text(subtitle, color = Rpg.Muted, fontSize = 13.sp)
        content()
    }
}

/** One-of-many chips that scroll sideways. */
@Composable
internal fun <T> ChoiceChips(options: List<Pair<T, String>>, selected: T?, onSelect: (T) -> Unit) {
    Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
        options.forEach { (value, label) ->
            FilterChip(selected = selected == value, onClick = { onSelect(value) }, label = { Text(label) })
        }
    }
}

@Composable
internal fun TextInput(value: String, onChange: (String) -> Unit, label: String, numeric: Boolean = false) {
    OutlinedTextField(
        value, onChange, label = { Text(label) }, singleLine = true, modifier = Modifier.fillMaxWidth(),
        keyboardOptions = if (numeric) KeyboardOptions(keyboardType = KeyboardType.Decimal) else KeyboardOptions.Default,
    )
}

/** XP presets plus a field for any other amount. */
@Composable
internal fun XpPicker(xp: String, onChange: (String) -> Unit, presets: List<Pair<Int, String>>) {
    ChoiceChips(presets.map { (amount, label) -> amount.toString() to "$label · $amount" }, xp, onChange)
    TextInput(xp, onChange, "XP", numeric = true)
}

/** Quick due dates plus a calendar; [optional] adds "No deadline" (null). */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun DeadlinePicker(date: LocalDate?, onChange: (LocalDate?) -> Unit, optional: Boolean = false) {
    var picking by remember { mutableStateOf(false) }
    val today = LocalDate.now()
    val quick = buildList {
        if (optional) add(null to "No deadline")
        add(today to "Today")
        add(today.plusDays(1) to "Tomorrow")
        add(today.plusWeeks(1) to "In a week")
        add(today.plusMonths(1) to "In a month")
        add(today.plusMonths(3) to "3 months")
    }
    Text(date?.let { "Due ${longDate(it)} · ${relative(it)}" } ?: "No deadline", fontSize = 13.sp, color = Rpg.Muted)
    Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
        quick.forEach { (value, label) -> FilterChip(selected = date == value, onClick = { onChange(value) }, label = { Text(label) }) }
        FilterChip(selected = date != null && quick.none { it.first == date }, onClick = { picking = true }, label = { Text("📅 Pick") })
    }
    if (picking) {
        val state = rememberDatePickerState(initialSelectedDateMillis = (date ?: today).atStartOfDay(ZoneOffset.UTC).toInstant().toEpochMilli())
        DatePickerDialog(
            onDismissRequest = { picking = false },
            confirmButton = {
                TextButton(onClick = {
                    state.selectedDateMillis?.let { onChange(Instant.ofEpochMilli(it).atZone(ZoneOffset.UTC).toLocalDate()) }
                    picking = false
                }) { Text("OK") }
            },
            dismissButton = { TextButton(onClick = { picking = false }) { Text("Cancel") } },
        ) { DatePicker(state) }
    }
}

/** A calendar for picking a past day: nothing after [latest] can be chosen. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun DatePick(initial: LocalDate, latest: LocalDate, onPick: (LocalDate) -> Unit, onDismiss: () -> Unit) {
    val last = latest.atStartOfDay(ZoneOffset.UTC).toInstant().toEpochMilli()
    val state = rememberDatePickerState(
        initialSelectedDateMillis = initial.atStartOfDay(ZoneOffset.UTC).toInstant().toEpochMilli(),
        selectableDates = object : SelectableDates {
            override fun isSelectableDate(utcTimeMillis: Long) = utcTimeMillis <= last
            override fun isSelectableYear(year: Int) = year <= latest.year
        },
    )
    DatePickerDialog(
        onDismissRequest = onDismiss,
        confirmButton = {
            TextButton(onClick = {
                state.selectedDateMillis?.let { onPick(Instant.ofEpochMilli(it).atZone(ZoneOffset.UTC).toLocalDate()) } ?: onDismiss()
            }) { Text("OK") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } },
    ) { DatePicker(state) }
}

/** "Delete X?" and the like, with the confirm button in [color]. */
@Composable
internal fun ConfirmDialog(title: String, text: String, confirm: String, color: Color = Rpg.Bad, onConfirm: () -> Unit, onDismiss: () -> Unit) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(title) },
        text = { Text(text) },
        confirmButton = { TextButton(onClick = onConfirm) { Text(confirm, color = color) } },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } },
    )
}

/** A create/edit form in a dialog. [onSave] throws to show its message under the form; it closes the dialog itself. */
@Composable
internal fun FormDialog(title: String, saveLabel: String, onSave: suspend () -> Unit, onDismiss: () -> Unit, content: @Composable ColumnScope.() -> Unit) {
    var error by remember { mutableStateOf<String?>(null) }
    var saving by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(title) },
        text = {
            Column(Modifier.verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                content()
                error?.let { Text("❌ $it", color = Rpg.Bad, fontSize = 13.sp) }
            }
        },
        confirmButton = {
            TextButton(enabled = !saving, onClick = {
                saving = true
                scope.launch {
                    error = runCatching { onSave() }.exceptionOrNull()?.let { it.message ?: "Something went wrong" }
                    saving = false
                }
            }) { Text(if (saving) "Saving…" else saveLabel) }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } },
    )
}

internal fun wholeNumber(raw: String, label: String): Int = raw.trim().toIntOrNull() ?: error("$label: enter a whole number")

internal fun required(raw: String, label: String): String = raw.trim().ifEmpty { error("$label can't be empty") }

private val LONG_DATE = DateTimeFormatter.ofPattern("EEE d MMM", Locale.ENGLISH)

internal fun longDate(date: LocalDate): String = date.format(LONG_DATE)

/** "today", "tomorrow", "in 5 days", "2 days late" */
internal fun relative(date: LocalDate, today: LocalDate = LocalDate.now()): String {
    val days = ChronoUnit.DAYS.between(today, date)
    return when {
        days == 0L -> "today"
        days == 1L -> "tomorrow"
        days == -1L -> "yesterday"
        days > 1 -> "in $days days"
        else -> "${-days} days late"
    }
}

/** Says what didn't work, instead of a button that seems to do nothing */
internal fun failed(context: android.content.Context, action: String, error: Throwable) {
    android.widget.Toast.makeText(context, "Couldn't $action: ${error.message ?: "something went wrong"}", android.widget.Toast.LENGTH_LONG).show()
}
