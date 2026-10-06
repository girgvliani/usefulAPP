package com.liferpg.sync.ui

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.FilterChip
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Slider
import androidx.compose.material3.SliderDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.liferpg.sync.Api
import com.liferpg.sync.Goal
import com.liferpg.sync.GogginsMode
import kotlinx.coroutines.launch
import org.json.JSONObject
import java.time.LocalDate

private val GOAL_TYPES = listOf(
    "weight" to "⚖️ Weight",
    "max_pushups" to "💪 Max push-ups",
    "steps" to "👟 Steps",
    "sleep" to "😴 Sleep",
    "income" to "💰 Income",
    "custom" to "✨ Custom",
)

/** A ready-made goal; empty fields are left for the user to fill in. */
internal data class GoalPreset(val label: String, val type: String, val target: String = "", val title: String = "", val unit: String = "", val start: String = "")

internal val GOAL_PRESETS = listOf(
    GoalPreset("⚖️ Lose weight", "weight"),
    GoalPreset("💪 50 push-ups in a row", "max_pushups", target = "50"),
    GoalPreset("👟 10,000 steps a day", "steps", target = "10000"),
    GoalPreset("😴 Sleep 8 hours", "sleep", target = "8"),
    GoalPreset("💰 Monthly income", "income"),
    GoalPreset("📚 Read 12 books", "custom", target = "12", title = "Read 12 books", unit = "books", start = "0"),
    GoalPreset("🏃 Run 100 km", "custom", target = "100", title = "Run 100 km", unit = "km", start = "0"),
)

@Composable
fun GoalsScreen(api: Api) {
    val context = LocalContext.current
    val levelState = LocalLevel.current
    val levelScope = rememberCoroutineScope()
    val goals = rememberLoader {
        api.goals().also {
            GogginsMode.update(context, it)
            levelScope.launch { levelState?.refresh() }  // a reached goal is +250 XP
        }
    }
    var creating by remember { mutableStateOf<GoalPreset?>(null) }

    LoadView(goals) { list ->
        Column(Modifier.verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("GOALS", Modifier.weight(1f), style = androidx.compose.material3.MaterialTheme.typography.headlineLarge, color = Rpg.Accent)
                Button(onClick = { creating = GoalPreset("", "weight") }) { Text("+ New goal") }
            }
            if (list.isEmpty()) {
                Text("No goals yet. Pick one to start, or make your own:", color = Rpg.Muted)
                GoalPresetChips { creating = it }
            }
            list.forEach { GoalCard(api, it, onChanged = goals::reload) }
        }
    }
    creating?.let { preset -> NewGoalDialog(api, preset, onDone = { creating = null; goals.reload() }, onCancel = { creating = null }) }
}

@Composable
internal fun GoalCard(api: Api, goal: Goal, onChanged: () -> Unit) {
    val scope = rememberCoroutineScope()
    var confirmDelete by remember { mutableStateOf(false) }
    var editing by remember { mutableStateOf(false) }
    var newValue by remember { mutableStateOf("") }
    var error by remember { mutableStateOf<String?>(null) }
    val color = if (goal.achieved) Rpg.Good else Rpg.Accent

    HudCard {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(goal.title, Modifier.weight(1f), fontWeight = FontWeight.Bold)
            Text(if (goal.direction == "decrease") "↓" else "↑", color = color, fontWeight = FontWeight.Black, fontSize = 18.sp)
        }
        Meter((goal.progress ?: 0.0).toFloat(), color)
        Row {
            Text(
                goal.currentValue?.let { "Now ${fmt(it)} ${goal.unit}" } ?: "Nothing logged yet",
                Modifier.weight(1f), color = Rpg.Muted, fontSize = 13.sp,
            )
            Text(
                if (goal.achieved) "🏆 Reached" else "${((goal.progress ?: 0.0) * 100).toInt()}% · target ${fmt(goal.targetValue)}",
                color = color, fontSize = 13.sp, fontWeight = FontWeight.Bold,
            )
        }
        goal.deadline?.let { Text("Deadline $it", color = Rpg.Muted, fontSize = 12.sp) }

        Row(verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text("🔥 Goggins scale ${goal.intensity}/10", fontWeight = FontWeight.Bold, color = gogginsColor(goal.intensity))
                Text(GogginsMode.describe(goal.intensity), color = Rpg.Muted, fontSize = 12.sp)
            }
            listOf(-1 to "−", 1 to "+").forEach { (step, label) ->
                val next = goal.intensity + step
                TextButton(
                    onClick = {
                        scope.launch {
                            error = runCatching { api.updateGoal(goal.id, JSONObject().put("intensity", next)); onChanged() }
                                .exceptionOrNull()?.message
                        }
                    },
                    enabled = next in 1..10,
                ) { Text(label, fontSize = 20.sp, fontWeight = FontWeight.Black) }
            }
        }

        if (goal.type == "custom") {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(
                    value = newValue, onValueChange = { newValue = it }, singleLine = true,
                    label = { Text("New value") }, modifier = Modifier.width(140.dp),
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                )
                TextButton(onClick = {
                    scope.launch {
                        error = runCatching {
                            api.updateGoal(goal.id, JSONObject().put("current_value", number(newValue, "New value")))
                            onChanged()
                        }.exceptionOrNull()?.message
                    }
                }) { Text("Update") }
            }
        }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
            TextButton(onClick = { editing = true }) { Text("Edit") }
            TextButton(onClick = { confirmDelete = true }) { Text("Delete", color = Rpg.Bad) }
        }
        error?.let { Text("❌ $it", color = Rpg.Bad, fontSize = 13.sp) }
    }

    if (editing) EditGoalDialog(api, goal, onDone = { editing = false; onChanged() }, onCancel = { editing = false })
    if (confirmDelete) {
        AlertDialog(
            onDismissRequest = { confirmDelete = false },
            title = { Text("Delete goal?") },
            text = { Text(goal.title) },
            confirmButton = {
                TextButton(onClick = {
                    confirmDelete = false
                    scope.launch { runCatching { api.deleteGoal(goal.id) }; onChanged() }
                }) { Text("Delete", color = Rpg.Bad) }
            },
            dismissButton = { TextButton(onClick = { confirmDelete = false }) { Text("Cancel") } },
        )
    }
}

@Composable
internal fun GoalPresetChips(onPick: (GoalPreset) -> Unit) {
    ChoiceChips(GOAL_PRESETS.map { it to it.label }, null, onPick)
}

@Composable
internal fun NewGoalDialog(api: Api, preset: GoalPreset, onDone: () -> Unit, onCancel: () -> Unit) {
    val scope = rememberCoroutineScope()
    var type by remember { mutableStateOf(preset.type) }
    var target by remember { mutableStateOf(preset.target) }
    var start by remember { mutableStateOf(preset.start) }
    var title by remember { mutableStateOf(preset.title) }
    var unit by remember { mutableStateOf(preset.unit) }
    var deadline by remember { mutableStateOf<LocalDate?>(null) }
    var current by remember { mutableStateOf("") }
    var error by remember { mutableStateOf<String?>(null) }
    var intensity by remember { mutableIntStateOf(5) }
    val custom = type == "custom"

    AlertDialog(
        onDismissRequest = onCancel,
        title = { Text("New goal") },
        text = {
            Column(Modifier.verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    GOAL_TYPES.forEach { (value, label) ->
                        FilterChip(selected = type == value, onClick = { type = value }, label = { Text(label) })
                    }
                }
                if (custom) {
                    OutlinedTextField(title, { title = it }, label = { Text("What (e.g. Read 20 books)") }, singleLine = true)
                    OutlinedTextField(unit, { unit = it }, label = { Text("Unit (e.g. books)") }, singleLine = true)
                }
                NumberField(target, { target = it }, "Target")
                Text("🔥 Goggins scale $intensity/10", fontWeight = FontWeight.Bold, color = gogginsColor(intensity))
                Slider(
                    value = intensity.toFloat(),
                    onValueChange = { intensity = it.toInt() },
                    valueRange = 1f..10f,
                    steps = 8,
                    colors = SliderDefaults.colors(thumbColor = gogginsColor(intensity), activeTrackColor = gogginsColor(intensity)),
                )
                Text(GogginsMode.describe(intensity), color = Rpg.Muted, fontSize = 12.sp)
                NumberField(start, { start = it }, if (custom) "Start" else "Start (empty = your latest value)")
                if (custom) NumberField(current, { current = it }, "Where you are now (optional)")
                DeadlinePicker(deadline, { deadline = it }, optional = true)
                error?.let { Text("❌ $it", color = Rpg.Bad, fontSize = 13.sp) }
            }
        },
        confirmButton = {
            TextButton(onClick = {
                scope.launch {
                    error = runCatching {
                        val body = JSONObject().put("type", type).put("target_value", number(target, "Target")).put("intensity", intensity)
                        if (start.isNotBlank()) body.put("start_value", number(start, "Start"))
                        deadline?.let { body.put("deadline", it.toString()) }
                        if (custom) {
                            if (title.isNotBlank()) body.put("title", title.trim())
                            if (unit.isNotBlank()) body.put("unit", unit.trim())
                            if (current.isNotBlank()) body.put("current_value", number(current, "Now"))
                        }
                        api.createGoal(body)
                        onDone()
                    }.exceptionOrNull()?.message
                }
            }) { Text("Create") }
        },
        dismissButton = { TextButton(onClick = onCancel) { Text("Cancel") } },
    )
}

/** Rename, move the target or start, change the deadline. Progress follows on its own. */
@Composable
private fun EditGoalDialog(api: Api, goal: Goal, onDone: () -> Unit, onCancel: () -> Unit) {
    var title by remember { mutableStateOf(goal.title) }
    var target by remember { mutableStateOf(fmt(goal.targetValue)) }
    var start by remember { mutableStateOf(fmt(goal.startValue)) }
    var deadline by remember { mutableStateOf(goal.deadline?.let(LocalDate::parse)) }
    FormDialog("Edit goal", "Save", onSave = {
        val body = JSONObject()
            .put("title", required(title, "Title"))
            .put("target_value", number(target, "Target"))
            .put("start_value", number(start, "Start"))
        // The server has no "clear deadline"; an unchanged or new date is sent as is
        deadline?.let { body.put("deadline", it.toString()) }
        api.updateGoal(goal.id, body)
        onDone()
    }, onDismiss = onCancel) {
        TextInput(title, { title = it }, "Title")
        NumberField(start, { start = it }, "Start (${goal.unit})")
        NumberField(target, { target = it }, "Target (${goal.unit})")
        DeadlinePicker(deadline, { deadline = it }, optional = goal.deadline == null)
    }
}

@Composable
private fun NumberField(value: String, onChange: (String) -> Unit, label: String) {
    OutlinedTextField(
        value, onChange, label = { Text(label) }, singleLine = true,
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal), modifier = Modifier.fillMaxWidth(),
    )
}

private fun number(raw: String, label: String): Double =
    raw.trim().replace(',', '.').toDoubleOrNull() ?: error("$label: enter a number")

private fun fmt(value: Double) = if (value % 1.0 == 0.0) value.toLong().toString() else "%.1f".format(value)

/** Cool at 1, hot at 10: the levels that trigger warnings (8+) glow red. */
private fun gogginsColor(level: Int) = when {
    level >= GogginsMode.MIN_LEVEL -> Rpg.Bad
    level >= 6 -> androidx.compose.ui.graphics.Color(0xFFFB923C)
    else -> Rpg.Muted
}
