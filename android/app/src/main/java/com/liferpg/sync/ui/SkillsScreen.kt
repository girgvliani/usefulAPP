package com.liferpg.sync.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
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
import com.liferpg.sync.Skill
import kotlinx.coroutines.launch

private val CATEGORY_IDEAS = listOf("Health", "Learning", "Career", "Mind", "Creative", "Money", "Relationships")

/** A skill's name on a chip: just "Kotlin" unless another category has a "Kotlin" too. */
internal fun skillLabel(skill: Skill, all: List<Skill>) =
    if (all.count { it.shortName == skill.shortName } > 1) skill.name else skill.shortName

@Composable
fun SkillsScreen(api: Api) {
    val scope = rememberCoroutineScope()
    val skills = rememberLoader { api.skills() }
    var editing by remember { mutableStateOf<Skill?>(null) }
    var creating by remember { mutableStateOf(false) }
    var deleteError by remember { mutableStateOf<String?>(null) }

    LoadView(skills) { list ->
        SkillTree(list, onAdd = { creating = true }, onOpen = { editing = it })
        if (creating) SkillDialog(null, list, onSave = { api.createSkill(it); creating = false; skills.reload() }, onDismiss = { creating = false })
        editing?.let { skill ->
            SkillDialog(
                skill, list,
                onSave = { api.renameSkill(skill.id, it); editing = null; skills.reload() },
                onDelete = { scope.launch { runCatching { api.deleteSkill(skill.id) }.onFailure { e -> deleteError = e.message }; editing = null; skills.reload() } },
                onDismiss = { editing = null },
            )
        }
        deleteError?.let { ConfirmDialog("Can't delete", it, "OK", color = Rpg.Accent, onConfirm = { deleteError = null }, onDismiss = { deleteError = null }) }
    }
}

/** Skills grouped by category, each with its level and XP bar. */
@Composable
internal fun SkillTree(skills: List<Skill>, onAdd: () -> Unit, onOpen: (Skill) -> Unit) {
    PlanPage(
        "Skills",
        "The areas of your life that level up. Quests give XP to one skill, milestones to all of them. ${Skill.XP_PER_LEVEL} XP per level. Tap one to rename or delete it.",
        "+ Skill", onAdd,
    ) {
        if (skills.isEmpty()) Text("No skills yet. Add the areas you want to grow in.", color = Rpg.Muted)
        skills.groupBy { it.category }.toSortedMap().forEach { (category, items) ->
            HudCard {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(category.uppercase(), Modifier.weight(1f), fontWeight = FontWeight.Black, color = Rpg.Accent)
                    Text("LV ${items.sumOf { it.level }}", color = Rpg.Muted, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                }
                items.sortedByDescending { it.xp }.forEach { skill ->
                    Column(Modifier.fillMaxWidth().clickable { onOpen(skill) }.padding(vertical = 4.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text((if (skill.name in Skill.PROTECTED) "🔒 " else "") + skill.shortName, Modifier.weight(1f), fontWeight = FontWeight.Bold)
                            Text("LV ${skill.level}", fontWeight = FontWeight.Black)
                        }
                        Meter(skill.progress, Rpg.Accent)
                        Text("${skill.xp} XP · ${Skill.XP_PER_LEVEL - skill.xp % Skill.XP_PER_LEVEL} to LV ${skill.level + 1}", color = Rpg.Muted, fontSize = 12.sp)
                    }
                }
            }
        }
    }
}

@Composable
private fun SkillDialog(existing: Skill?, all: List<Skill>, onSave: suspend (String) -> Unit, onDismiss: () -> Unit, onDelete: (() -> Unit)? = null) {
    val locked = existing != null && existing.name in Skill.PROTECTED
    var category by remember { mutableStateOf(existing?.category?.takeIf { existing.name.contains(" - ") }.orEmpty()) }
    var name by remember { mutableStateOf(existing?.shortName.orEmpty()) }
    var confirmDelete by remember { mutableStateOf(false) }
    val categories = (all.map { it.category } + CATEGORY_IDEAS).distinct()

    FormDialog(
        if (existing == null) "New skill" else "Edit skill",
        if (existing == null) "Create" else "Save",
        onSave = {
            check(!locked) { "Habit XP lands in this skill, so it keeps its name" }
            val skill = required(name, "Skill")
            onSave(if (category.isBlank()) skill else "${category.trim()} - $skill")
        },
        onDismiss = onDismiss,
    ) {
        if (locked) {
            Text("🔒 ${existing!!.name} collects habit XP (push-ups, showers, social), so it can't be renamed or deleted.", color = Rpg.Muted, fontSize = 13.sp)
        } else {
            TextInput(category, { category = it }, "Category (optional)")
            ChoiceChips(categories.map { it to it }, category) { category = it }
            TextInput(name, { name = it }, "Skill (e.g. Kotlin, Guitar, Running)")
            if (existing != null && onDelete != null) {
                TextButton(onClick = { confirmDelete = true }) { Text("Delete this skill", color = Rpg.Bad) }
                Text("Its XP goes with it, so your level can drop. Not possible while quests use it.", color = Rpg.Muted, fontSize = 12.sp)
            }
        }
    }
    if (confirmDelete && existing != null && onDelete != null) {
        ConfirmDialog("Delete ${existing.name}?", "Its ${existing.xp} XP comes off your total.", "Delete", onConfirm = { confirmDelete = false; onDelete() }, onDismiss = { confirmDelete = false })
    }
}
