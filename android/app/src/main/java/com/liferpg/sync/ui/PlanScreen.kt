package com.liferpg.sync.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.liferpg.sync.Api
import com.liferpg.sync.Goal
import com.liferpg.sync.Milestone
import com.liferpg.sync.Project
import com.liferpg.sync.Quest
import com.liferpg.sync.Skill
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import java.time.LocalDate

data class PlanData(
    val goals: List<Goal>,
    val milestones: List<Milestone>,
    val quests: List<Quest>,
    val projects: List<Project>,
    val skills: List<Skill>,
)

/** One page with everything you're working toward; each card opens its full list. */
@Composable
fun PlanScreen(api: Api, onOpen: (Dest) -> Unit) {
    val plan = rememberLoader {
        coroutineScope {
            val goals = async { api.goals() }
            val milestones = async { api.milestones() }
            val quests = async { api.quests() }
            val projects = async { api.projects() }
            val skills = async { api.skills() }
            PlanData(goals.await(), milestones.await(), quests.await(), projects.await(), skills.await())
        }
    }
    var goalPreset by remember { mutableStateOf<GoalPreset?>(null) }
    var milestoneIdea by remember { mutableStateOf<Pair<String, Int>?>(null) }

    LoadView(plan) { data ->
        PlanOverview(data, onOpen, onGoalPreset = { goalPreset = it }, onMilestoneIdea = { milestoneIdea = it })
    }
    goalPreset?.let { NewGoalDialog(api, it, onDone = { goalPreset = null; plan.reload() }, onCancel = { goalPreset = null }) }
    milestoneIdea?.let { (text, xp) ->
        MilestoneDialog(null, text, xp, onSave = { d, x -> api.createMilestone(d, x); milestoneIdea = null; plan.reload() }, onDismiss = { milestoneIdea = null })
    }
}

@Composable
internal fun PlanOverview(
    data: PlanData,
    onOpen: (Dest) -> Unit,
    onGoalPreset: (GoalPreset) -> Unit,
    onMilestoneIdea: (Pair<String, Int>) -> Unit,
    today: LocalDate = LocalDate.now(),
) {
    val openQuests = data.quests.filter { !it.completed }
    val overdue = openQuests.count { LocalDate.parse(it.deadline) < today }
    val dueToday = openQuests.count { LocalDate.parse(it.deadline) == today }
    val activeGoals = data.goals.filter { !it.achieved }
    val openMilestones = data.milestones.filter { !it.completed }
    val openProjects = data.projects.filter { !it.completed }

    Column(Modifier.verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Text("PLAN", style = MaterialTheme.typography.headlineLarge, color = Rpg.Accent)
        Text("Everything you're working toward. Tap a card to manage it; ☰ has the same list.", color = Rpg.Muted, fontSize = 13.sp)

        PlanCard(Dest.Goals, "${activeGoals.size} active · ${data.goals.size - activeGoals.size} reached", onOpen) {
            activeGoals.sortedByDescending { it.intensity }.take(3).forEach { goal ->
                PreviewRow(goal.title, "${((goal.progress ?: 0.0) * 100).toInt()}%")
                Meter((goal.progress ?: 0.0).toFloat(), Rpg.Accent)
            }
            if (data.goals.isEmpty()) {
                Text("Start with one:", color = Rpg.Muted, fontSize = 12.sp)
                GoalPresetChips(onGoalPreset)
            }
        }

        PlanCard(
            Dest.Quests,
            listOfNotNull(
                "${openQuests.size} open",
                if (dueToday > 0) "$dueToday due today" else null,
                if (overdue > 0) "⚠️ $overdue overdue" else null,
            ).joinToString(" · "),
            onOpen,
        ) {
            openQuests.sortedBy { it.deadline }.take(3).forEach { quest ->
                PreviewRow(quest.task, "+${questXp(quest, today)} XP · ${relative(LocalDate.parse(quest.deadline), today)}")
            }
        }

        PlanCard(Dest.Milestones, "${openMilestones.size} open · ${data.milestones.size - openMilestones.size} done", onOpen) {
            openMilestones.sortedByDescending { it.xp }.take(3).forEach { PreviewRow(it.description, "+${it.xp} XP") }
            if (data.milestones.isEmpty()) {
                Text("Ideas:", color = Rpg.Muted, fontSize = 12.sp)
                IdeaChips(MILESTONE_IDEAS.map { it.first }) { idea -> onMilestoneIdea(MILESTONE_IDEAS.first { it.first == idea }) }
            }
        }

        PlanCard(Dest.Projects, "${openProjects.size} open", onOpen) {
            openProjects.sortedBy { it.deadline }.take(3).forEach { PreviewRow(it.name, relative(LocalDate.parse(it.deadline), today)) }
        }

        PlanCard(Dest.Skills, "${data.skills.size} skills · LV ${data.skills.sumOf { it.level }} combined", onOpen) {
            data.skills.sortedByDescending { it.xp }.take(3).forEach { skill ->
                PreviewRow(skill.name, "LV ${skill.level}")
                Meter(skill.progress, Rpg.AccentDeep)
            }
        }
    }
}

@Composable
private fun PlanCard(dest: Dest, summary: String, onOpen: (Dest) -> Unit, preview: @Composable () -> Unit) {
    HudCard(Modifier.clickable { onOpen(dest) }) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(dest.icon, fontSize = 24.sp)
            Column(Modifier.weight(1f).padding(start = 12.dp)) {
                Text(dest.label.uppercase(), fontWeight = FontWeight.Black, fontSize = 17.sp)
                Text(summary, color = Rpg.Muted, fontSize = 12.sp)
            }
            Text("›", color = Rpg.Accent, fontSize = 28.sp, fontWeight = FontWeight.Black)
        }
        preview()
    }
}

@Composable
private fun PreviewRow(text: String, value: String) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Text(text, Modifier.weight(1f), fontSize = 14.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
        Text(value, color = Rpg.Muted, fontSize = 12.sp, fontWeight = FontWeight.Bold, modifier = Modifier.padding(start = 8.dp))
    }
}
