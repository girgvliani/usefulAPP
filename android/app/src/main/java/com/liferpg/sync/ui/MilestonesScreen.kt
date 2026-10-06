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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.unit.sp
import com.liferpg.sync.Api
import com.liferpg.sync.Milestone
import kotlinx.coroutines.launch

internal val MILESTONE_XP = listOf(250 to "Small", 500 to "Solid", 1000 to "Big", 2500 to "Huge", 5000 to "Legendary")

/** Starting points for people who don't know what to aim for yet. */
internal val MILESTONE_IDEAS = listOf(
    "Run a 5K without stopping" to 500,
    "Read 12 books this year" to 1000,
    "30 days with no reels" to 1000,
    "Ship a side project" to 2500,
    "Save 3 months of expenses" to 2500,
    "Hold a 2-minute plank" to 250,
)

@Composable
fun MilestonesScreen(api: Api) {
    val levelState = LocalLevel.current
    val scope = rememberCoroutineScope()
    val milestones = rememberLoader { api.milestones() }
    var editing by remember { mutableStateOf<Milestone?>(null) }
    var creating by remember { mutableStateOf<Pair<String, Int>?>(null) }
    var showDone by remember { mutableStateOf(false) }

    LoadView(milestones) { list ->
        val (done, open) = list.partition { it.completed }
        PlanPage(
            "Milestones",
            "Big one-off wins. Completing one shares its XP out over all your skills.",
            "+ Milestone", onAdd = { creating = "" to 500 },
        ) {
            ChoiceChips(listOf(false to "Open · ${open.size}", true to "Done · ${done.size}"), showDone) { showDone = it }
            val shown = if (showDone) done else open
            if (shown.isEmpty() && !showDone) {
                Text("No milestones yet. Pick one to start, or add your own:", color = Rpg.Muted)
                IdeaChips(MILESTONE_IDEAS.map { it.first }) { idea -> creating = MILESTONE_IDEAS.first { it.first == idea } }
            }
            if (shown.isEmpty() && showDone) Text("Nothing completed yet.", color = Rpg.Muted)
            shown.forEach { milestone ->
                MilestoneCard(
                    milestone,
                    onComplete = {
                        scope.launch {
                            runCatching { api.completeMilestone(milestone.key) }
                            milestones.reload()
                            levelState?.refresh()
                        }
                    },
                    onEdit = { editing = milestone },
                    onDelete = { scope.launch { runCatching { api.deleteMilestone(milestone.key) }; milestones.reload() } },
                )
            }
        }
    }

    creating?.let { (text, xp) ->
        MilestoneDialog(null, text, xp, onSave = { d, x -> api.createMilestone(d, x); creating = null; milestones.reload() }, onDismiss = { creating = null })
    }
    editing?.let { m ->
        MilestoneDialog(m, m.description, m.xp, onSave = { d, x -> api.updateMilestone(m.key, d, x); editing = null; milestones.reload() }, onDismiss = { editing = null })
    }
}

@Composable
internal fun MilestoneCard(milestone: Milestone, onComplete: () -> Unit, onEdit: () -> Unit, onDelete: () -> Unit) {
    var confirm by remember { mutableStateOf<String?>(null) }
    HudCard {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(
                (if (milestone.completed) "✅ " else "🏔️ ") + milestone.description,
                Modifier.weight(1f), fontWeight = FontWeight.Bold,
                textDecoration = if (milestone.completed) TextDecoration.LineThrough else null,
                color = if (milestone.completed) Rpg.Muted else Rpg.Text,
            )
            Text("+${milestone.xp} XP", color = if (milestone.completed) Rpg.Muted else Rpg.Good, fontWeight = FontWeight.Black)
        }
        Row(horizontalArrangement = Arrangement.End, modifier = Modifier.fillMaxWidth()) {
            if (!milestone.completed) {
                TextButton(onClick = { confirm = "complete" }) { Text("✓ Complete", color = Rpg.Good, fontWeight = FontWeight.Bold) }
                TextButton(onClick = onEdit) { Text("Edit") }
            }
            TextButton(onClick = { confirm = "delete" }) { Text("Delete", color = Rpg.Bad) }
        }
    }
    when (confirm) {
        "complete" -> ConfirmDialog(
            "Completed it?", "${milestone.description}\n\n+${milestone.xp} XP, shared over your skills. This can't be undone.", "Complete",
            color = Rpg.Good, onConfirm = { confirm = null; onComplete() }, onDismiss = { confirm = null },
        )
        "delete" -> ConfirmDialog(
            "Delete milestone?", milestone.description + if (milestone.completed) "\n\nXP you already earned stays." else "", "Delete",
            onConfirm = { confirm = null; onDelete() }, onDismiss = { confirm = null },
        )
    }
}

@Composable
internal fun MilestoneDialog(existing: Milestone?, text: String, xp: Int, onSave: suspend (String, Int) -> Unit, onDismiss: () -> Unit) {
    var description by remember { mutableStateOf(text) }
    var reward by remember { mutableStateOf(xp.toString()) }
    FormDialog(
        if (existing == null) "New milestone" else "Edit milestone",
        if (existing == null) "Create" else "Save",
        onSave = { onSave(required(description, "Milestone"), wholeNumber(reward, "XP")) },
        onDismiss = onDismiss,
    ) {
        TextInput(description, { description = it }, "What will you achieve?")
        if (existing == null && description.isEmpty()) IdeaChips(MILESTONE_IDEAS.map { it.first }) { idea ->
            description = idea
            reward = MILESTONE_IDEAS.first { it.first == idea }.second.toString()
        }
        Text("How big is it?", color = Rpg.Muted, fontSize = 12.sp)
        XpPicker(reward, { reward = it }, MILESTONE_XP)
    }
}

/** Tap a suggestion to use it. */
@Composable
internal fun IdeaChips(ideas: List<String>, onPick: (String) -> Unit) {
    ChoiceChips(ideas.map { it to "💡 $it" }, null, onPick)
}
