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
import com.liferpg.sync.Project
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.launch
import org.json.JSONObject
import java.time.LocalDate

@Composable
fun ProjectsScreen(api: Api) {
    val levelState = LocalLevel.current
    val scope = rememberCoroutineScope()
    val context = LocalContext.current
    val data = rememberLoader {
        coroutineScope { val p = async { api.projects() }; val c = async { api.profile().currency }; p.await() to c.await() }
    }
    var editing by remember { mutableStateOf<Project?>(null) }
    var creating by remember { mutableStateOf(false) }
    var showDone by remember { mutableStateOf(false) }

    LoadView(data) { (projects, currency) ->
        val (done, open) = projects.partition { it.completed }
        PlanPage(
            "Projects",
            "Paid work. Completing one adds its value to this month's income (Wealth) and gives Work Skills XP: 1 per 10 $currency, 1.5x on time.",
            "+ Project", onAdd = { creating = true },
        ) {
            ChoiceChips(listOf(false to "Open · ${open.size}", true to "Done · ${done.size}"), showDone) { showDone = it }
            val shown = if (showDone) done.sortedByDescending { it.completedOn } else open.sortedBy { it.deadline }
            if (shown.isEmpty()) Text(if (showDone) "Nothing completed yet." else "No open projects.", color = Rpg.Muted)
            shown.forEach { project ->
                ProjectCard(
                    project, currency,
                    onComplete = {
                        scope.launch {
                            runCatching { api.completeProject(project.id) }.onFailure { failed(context, "complete the project", it) }
                            data.reload()
                            levelState?.refresh()
                        }
                    },
                    onEdit = { editing = project },
                    onDelete = { scope.launch { runCatching { api.deleteProject(project.id) }.onFailure { failed(context, "delete the project", it) }; data.reload() } },
                )
            }
        }
        if (creating) ProjectDialog(null, currency, onSave = { api.createProject(it); creating = false; data.reload() }, onDismiss = { creating = false })
        editing?.let { p -> ProjectDialog(p, currency, onSave = { api.updateProject(p.id, it); editing = null; data.reload() }, onDismiss = { editing = null }) }
    }
}

@Composable
private fun ProjectCard(project: Project, currency: String, onComplete: () -> Unit, onEdit: () -> Unit, onDelete: () -> Unit) {
    var confirm by remember { mutableStateOf<String?>(null) }
    val deadline = LocalDate.parse(project.deadline)
    HudCard {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(
                project.name, Modifier.weight(1f), fontWeight = FontWeight.Bold,
                textDecoration = if (project.completed) TextDecoration.LineThrough else null,
                color = if (project.completed) Rpg.Muted else Rpg.Text,
            )
            Text("%,d %s".format(project.value, currency), fontWeight = FontWeight.Black, color = if (project.completed) Rpg.Muted else Rpg.Good)
        }
        Text(
            if (project.completed) project.completedOn?.let { "Paid · finished ${longDate(LocalDate.parse(it))}" } ?: "Finished"
            else "Due ${longDate(deadline)} · ${relative(deadline)}",
            color = if (!project.completed && deadline < LocalDate.now()) Rpg.Bad else Rpg.Muted, fontSize = 12.sp,
        )
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
            if (!project.completed) {
                TextButton(onClick = { confirm = "complete" }) { Text("✓ Complete", color = Rpg.Good, fontWeight = FontWeight.Bold) }
                TextButton(onClick = onEdit) { Text("Edit") }
            }
            TextButton(onClick = { confirm = "delete" }) { Text("Delete", color = Rpg.Bad) }
        }
    }
    when (confirm) {
        "complete" -> ConfirmDialog(
            "Finished and paid?", "${project.name}\n\nAdds %,d %s to this month's earnings.".format(project.value, currency), "Complete",
            color = Rpg.Good, onConfirm = { confirm = null; onComplete() }, onDismiss = { confirm = null },
        )
        "delete" -> ConfirmDialog(
            "Delete project?",
            project.name + if (project.completed) "\n\nIts value comes off this month's earnings; XP stays." else "",
            "Delete", onConfirm = { confirm = null; onDelete() }, onDismiss = { confirm = null },
        )
    }
}

@Composable
private fun ProjectDialog(existing: Project?, currency: String, onSave: suspend (JSONObject) -> Unit, onDismiss: () -> Unit) {
    var name by remember { mutableStateOf(existing?.name.orEmpty()) }
    var value by remember { mutableStateOf(existing?.value?.toString().orEmpty()) }
    var deadline by remember { mutableStateOf(existing?.deadline?.let(LocalDate::parse) ?: LocalDate.now().plusWeeks(1)) }
    FormDialog(
        if (existing == null) "New project" else "Edit project",
        if (existing == null) "Create" else "Save",
        onSave = {
            val amount = wholeNumber(value, "Value").also { require(it > 0) { "Value: more than 0" } }
            onSave(JSONObject().put("name", required(name, "Name")).put("value", amount).put("deadline", deadline.toString()))
        },
        onDismiss = onDismiss,
    ) {
        TextInput(name, { name = it }, "Project / client")
        TextInput(value, { value = it }, "What it pays ($currency)", numeric = true)
        DeadlinePicker(deadline, { if (it != null) deadline = it })
    }
}
