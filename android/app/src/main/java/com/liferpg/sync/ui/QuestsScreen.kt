package com.liferpg.sync.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.unit.sp
import com.liferpg.sync.Api
import com.liferpg.sync.Quest
import com.liferpg.sync.Skill
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.launch
import org.json.JSONObject
import java.time.LocalDate
import java.time.temporal.ChronoUnit

internal val QUEST_XP = listOf(10 to "Quick", 25 to "Normal", 50 to "Hard", 100 to "Boss")

/** The server's deadline bonus: 1.5x on time, 1x up to a week late, 0.5x after that. */
internal fun questXp(quest: Quest, today: LocalDate = LocalDate.now()): Int {
    val late = ChronoUnit.DAYS.between(LocalDate.parse(quest.deadline), today)
    val multiplier = when {
        late <= 0 -> 1.5
        late <= 7 -> 1.0
        else -> 0.5
    }
    return (quest.baseXp * multiplier).toInt()
}

@Composable
fun QuestsScreen(api: Api) {
    val levelState = LocalLevel.current
    val scope = rememberCoroutineScope()
    val context = LocalContext.current
    val data = rememberLoader { coroutineScope { val q = async { api.quests() }; val s = async { api.skills() }; q.await() to s.await() } }
    var editing by remember { mutableStateOf<Quest?>(null) }
    var creating by remember { mutableStateOf(false) }

    LoadView(data) { (quests, skills) ->
        QuestList(
            quests, skills,
            onAdd = { creating = true },
            onComplete = { quest ->
                scope.launch {
                    runCatching { api.completeQuest(quest.id) }.onFailure { failed(context, "complete the quest", it) }
                    data.reload()
                    levelState?.refresh()
                }
            },
            onEdit = { editing = it },
            onDelete = { quest -> scope.launch { runCatching { api.deleteQuest(quest.id) }.onFailure { failed(context, "delete the quest", it) }; data.reload() } },
        )
        if (creating) QuestDialog(null, skills, onSave = { body -> api.createQuest(body); creating = false; data.reload() }, onDismiss = { creating = false })
        editing?.let { quest ->
            QuestDialog(quest, skills, onSave = { body -> api.updateQuest(quest.id, body); editing = null; data.reload() }, onDismiss = { editing = null })
        }
    }
}

/** Open quests grouped by when they're due; done ones behind a chip. */
@Composable
internal fun QuestList(
    quests: List<Quest>,
    skills: List<Skill>,
    onAdd: () -> Unit,
    onComplete: (Quest) -> Unit,
    onEdit: (Quest) -> Unit,
    onDelete: (Quest) -> Unit,
    today: LocalDate = LocalDate.now(),
) {
    var showDone by remember { mutableStateOf(false) }
    val (done, open) = quests.partition { it.completed }
    PlanPage("Quests", "To-dos that level up a skill. Finish by the deadline for 1.5x XP.", if (skills.isEmpty()) null else "+ Quest", onAdd) {
        if (skills.isEmpty()) Text("Add a skill first (☰ → Skills): every quest levels one up.", color = Rpg.Muted)
        ChoiceChips(listOf(false to "Open · ${open.size}", true to "Done · ${done.size}"), showDone) { showDone = it }
        if (showDone) {
            if (done.isEmpty()) Text("Nothing finished yet.", color = Rpg.Muted)
            done.sortedByDescending { it.completedOn }.forEach { QuestCard(it, skills, today, {}, {}, { onDelete(it) }) }
        } else {
            if (open.isEmpty()) Text("No open quests. Add the next thing you need to get done.", color = Rpg.Muted)
            open.groupBy { dueGroup(LocalDate.parse(it.deadline), today) }.toSortedMap().forEach { (group, items) ->
                SectionTitle(DUE_GROUPS[group])
                items.sortedBy { it.deadline }.forEach { quest ->
                    QuestCard(quest, skills, today, { onComplete(quest) }, { onEdit(quest) }, { onDelete(quest) })
                }
            }
        }
    }
}

private val DUE_GROUPS = listOf("⚠️ Overdue", "Today", "This week", "Later")

private fun dueGroup(deadline: LocalDate, today: LocalDate) = when {
    deadline < today -> 0
    deadline == today -> 1
    deadline <= today.plusDays(7) -> 2
    else -> 3
}

@Composable
private fun QuestCard(quest: Quest, skills: List<Skill>, today: LocalDate, onComplete: () -> Unit, onEdit: () -> Unit, onDelete: () -> Unit) {
    var confirmDelete by remember { mutableStateOf(false) }
    val skill = skills.firstOrNull { it.id == quest.skillId }
    val deadline = LocalDate.parse(quest.deadline)
    HudCard {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(
                quest.task, Modifier.weight(1f), fontWeight = FontWeight.Bold,
                textDecoration = if (quest.completed) TextDecoration.LineThrough else null,
                color = if (quest.completed) Rpg.Muted else Rpg.Text,
            )
            Text(
                if (quest.completed) "done" else "+${questXp(quest, today)} XP",
                color = if (quest.completed) Rpg.Muted else Rpg.Good, fontWeight = FontWeight.Black,
            )
        }
        Text(
            listOfNotNull(
                skill?.let { "🌳 ${skillLabel(it, skills)}" },
                if (quest.completed) quest.completedOn?.let { "finished ${longDate(LocalDate.parse(it))}" } else "due ${longDate(deadline)} · ${relative(deadline, today)}",
            ).joinToString("  ·  "),
            color = if (!quest.completed && deadline < today) Rpg.Bad else Rpg.Muted, fontSize = 12.sp,
        )
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
            if (!quest.completed) {
                TextButton(onClick = onComplete) { Text("✓ Done", color = Rpg.Good, fontWeight = FontWeight.Bold) }
                TextButton(onClick = onEdit) { Text("Edit") }
            }
            TextButton(onClick = { confirmDelete = true }) { Text("Delete", color = Rpg.Bad) }
        }
    }
    if (confirmDelete) {
        ConfirmDialog("Delete quest?", quest.task, "Delete", onConfirm = { confirmDelete = false; onDelete() }, onDismiss = { confirmDelete = false })
    }
}

@Composable
internal fun QuestDialog(existing: Quest?, skills: List<Skill>, onSave: suspend (JSONObject) -> Unit, onDismiss: () -> Unit) {
    var task by remember { mutableStateOf(existing?.task.orEmpty()) }
    var skillId by remember { mutableStateOf(existing?.skillId ?: skills.firstOrNull()?.id) }
    var xp by remember { mutableStateOf((existing?.baseXp ?: 25).toString()) }
    var deadline by remember { mutableStateOf(existing?.deadline?.let(LocalDate::parse) ?: LocalDate.now()) }
    FormDialog(
        if (existing == null) "New quest" else "Edit quest",
        if (existing == null) "Create" else "Save",
        onSave = {
            onSave(
                JSONObject()
                    .put("task", required(task, "Quest"))
                    .put("area_id", skillId ?: error("Pick a skill"))
                    .put("base_xp", wholeNumber(xp, "XP"))
                    .put("deadline", deadline.toString()),
            )
        },
        onDismiss = onDismiss,
    ) {
        TextInput(task, { task = it }, "What needs doing?")
        Text("Levels up", color = Rpg.Muted, fontSize = 12.sp)
        ChoiceChips(skills.map { it.id to skillLabel(it, skills) }, skillId) { skillId = it }
        Text("How hard?", color = Rpg.Muted, fontSize = 12.sp)
        XpPicker(xp, { xp = it }, QUEST_XP)
        DeadlinePicker(deadline, { if (it != null) deadline = it })
    }
}
