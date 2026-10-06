package com.liferpg.sync.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.ModalDrawerSheet
import androidx.compose.material3.NavigationDrawerItem
import androidx.compose.material3.NavigationDrawerItemDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.liferpg.sync.Level
import com.liferpg.sync.Settings

/** Every screen in the app. The ☰ menu lists them all; the bottom bar holds the ones you pin. */
enum class Dest(val label: String, val short: String, val icon: String, val group: String, val blurb: String) {
    Character("Character", "Character", "⚔️", "Today", "Your stats, rank and radar"),
    CheckIn("Check-in", "Check-in", "📝", "Today", "Log the day in 30 seconds"),
    Meals("Meals", "Meals", "🍽️", "Today", "Photo-log what you eat"),
    Plan("Plan", "Plan", "🗺️", "Plan", "Everything you're working toward"),
    Goals("Goals", "Goals", "🎯", "Plan", "Targets, progress, Goggins mode"),
    Milestones("Milestones", "Milestones", "🏔️", "Plan", "Big one-off wins, big XP"),
    Quests("Quests", "Quests", "📜", "Plan", "To-dos with deadlines that earn XP"),
    Projects("Projects", "Projects", "💼", "Plan", "Paid work that feeds Wealth"),
    Skills("Skills", "Skills", "🌳", "Plan", "The life areas your XP levels up"),
    Questionnaire("Questionnaire", "Quiz", "🧭", "You", "What matters to you, and your plan"),
    About("About you", "About", "🪪", "You", "Everything your stats are built from"),
    Profile("Profile & targets", "Profile", "🧍", "You", "Daily targets, body, income goal"),
    Settings("Settings", "Settings", "⚙️", "You", "Account, phone data, sync, Goggins"),
}

val DEFAULT_PINNED = listOf(Dest.Character, Dest.CheckIn, Dest.Meals, Dest.Goals, Dest.Plan)
const val MIN_PINNED = 2
const val MAX_PINNED = 5

fun pinnedDests(settings: Settings): List<Dest> =
    settings.pinnedTabs?.mapNotNull { name -> Dest.entries.firstOrNull { it.name == name } }
        ?.takeIf { it.size >= MIN_PINNED } ?: DEFAULT_PINNED

/** The ☰ menu: every screen by group, plus editing the bottom bar. */
@Composable
fun AppDrawer(current: Dest, pinned: List<Dest>, level: Level?, onOpen: (Dest) -> Unit, onCustomize: () -> Unit) {
    ModalDrawerSheet(drawerContainerColor = Rpg.Surface) {
        Column(Modifier.verticalScroll(rememberScrollState()).padding(12.dp)) {
            Row(Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                if (level != null) LvBadge(level.level, size = 40)
                Column {
                    Text("LIFE RPG", color = Rpg.Accent, fontWeight = FontWeight.Black, fontSize = 20.sp)
                    if (level != null) Text("${level.title} · ${level.xp} XP", color = Rpg.Muted, fontSize = 13.sp)
                }
            }
            Dest.entries.groupBy { it.group }.forEach { (group, items) ->
                Text(group.uppercase(), Modifier.padding(start = 16.dp, top = 14.dp, bottom = 4.dp), color = Rpg.Muted, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                items.forEach { dest -> DrawerItem(dest, selected = dest == current, pinned = dest in pinned) { onOpen(dest) } }
            }
            HorizontalDivider(Modifier.padding(vertical = 12.dp), color = Rpg.Outline)
            NavigationDrawerItem(
                label = { Text("Customize bottom bar") },
                icon = { Text("✏️", fontSize = 18.sp) },
                selected = false,
                onClick = onCustomize,
                colors = drawerColors(),
            )
        }
    }
}

@Composable
private fun DrawerItem(dest: Dest, selected: Boolean, pinned: Boolean, onClick: () -> Unit) {
    NavigationDrawerItem(
        label = {
            Column {
                Text(dest.label, fontWeight = FontWeight.Bold)
                Text(dest.blurb, color = Rpg.Muted, fontSize = 12.sp)
            }
        },
        icon = { Text(dest.icon, fontSize = 20.sp) },
        badge = { if (pinned) Text("📌", fontSize = 12.sp) },
        selected = selected,
        onClick = onClick,
        colors = drawerColors(),
    )
}

@Composable
private fun drawerColors() = NavigationDrawerItemDefaults.colors(
    unselectedContainerColor = Rpg.Surface,
    selectedContainerColor = Rpg.SurfaceHigh,
    selectedTextColor = Rpg.Accent,
    unselectedTextColor = Rpg.Text,
)

/** Choose which screens sit on the bottom bar and in what order (2 to 5). */
@Composable
fun CustomizeBarDialog(pinned: List<Dest>, onSave: (List<Dest>) -> Unit, onDismiss: () -> Unit) {
    var chosen by remember { mutableStateOf(pinned) }

    fun move(index: Int, by: Int) {
        chosen = chosen.toMutableList().apply { add(index + by, removeAt(index)) }
    }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Bottom bar") },
        text = {
            Column(Modifier.verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text("On the bar · $MIN_PINNED to $MAX_PINNED, left to right", color = Rpg.Muted, fontSize = 12.sp)
                chosen.forEachIndexed { i, dest ->
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("${dest.icon}  ${dest.label}", Modifier.weight(1f), fontWeight = FontWeight.Bold)
                        TextButton(onClick = { move(i, -1) }, enabled = i > 0, modifier = Modifier.width(44.dp)) { Text("↑") }
                        TextButton(onClick = { move(i, 1) }, enabled = i < chosen.lastIndex, modifier = Modifier.width(44.dp)) { Text("↓") }
                        TextButton(onClick = { chosen = chosen - dest }, enabled = chosen.size > MIN_PINNED, modifier = Modifier.width(44.dp)) {
                            Text("✕", color = if (chosen.size > MIN_PINNED) Rpg.Bad else Rpg.Muted)
                        }
                    }
                }
                HorizontalDivider(Modifier.padding(vertical = 8.dp), color = Rpg.Outline)
                Text(if (chosen.size < MAX_PINNED) "Tap to add" else "The bar is full; remove one to add another", color = Rpg.Muted, fontSize = 12.sp)
                (Dest.entries - chosen.toSet()).forEach { dest ->
                    TextButton(onClick = { chosen = chosen + dest }, enabled = chosen.size < MAX_PINNED, modifier = Modifier.fillMaxWidth()) {
                        Text("+  ${dest.icon}  ${dest.label}", Modifier.fillMaxWidth())
                    }
                }
            }
        },
        confirmButton = { TextButton(onClick = { onSave(chosen) }) { Text("Save") } },
        dismissButton = {
            Row {
                TextButton(onClick = { chosen = DEFAULT_PINNED }) { Text("Reset") }
                TextButton(onClick = onDismiss) { Text("Cancel") }
            }
        },
    )
}
