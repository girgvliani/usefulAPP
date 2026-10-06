package com.liferpg.sync.ui

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.runtime.snapshots.SnapshotStateMap
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.liferpg.sync.Api
import com.liferpg.sync.Attempt
import com.liferpg.sync.PlanStep
import com.liferpg.sync.QQuestion
import com.liferpg.sync.QSection
import com.liferpg.sync.Questionnaire
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.launch
import org.json.JSONArray
import org.json.JSONObject

/**
 * What matters to you and what to change to get there faster. Opens on your latest results when
 * you've taken it; "Retake" starts from your last answers. Every attempt is kept.
 */
@Composable
fun QuestionnaireScreen(api: Api, onOpen: (Dest) -> Unit) {
    val data = rememberLoader {
        coroutineScope {
            val q = async { api.questionnaire() }
            val past = async { api.attempts() }
            q.await() to past.await()
        }
    }
    var taking by remember { mutableStateOf(false) }

    LoadView(data) { (questionnaire, attempts) ->
        val latest = questionnaire.latest
        if (taking || latest == null) {
            QuestionnaireForm(
                api, questionnaire,
                onDone = { taking = false; data.reload() },
                onCancel = if (latest != null) ({ taking = false }) else null,
            )
        } else {
            QuestionnaireResults(api, latest, attempts, onRetake = { taking = true }, onOpen = onOpen)
        }
    }
}

/** One section per step, with a progress bar; answers start from your last attempt and your profile. */
@Composable
private fun QuestionnaireForm(api: Api, questionnaire: Questionnaire, onDone: () -> Unit, onCancel: (() -> Unit)?) {
    val scope = rememberCoroutineScope()
    val answers = remember { mutableStateMapOf<String, Any>().apply { putAll(startingAnswers(questionnaire)) } }
    var step by remember { mutableIntStateOf(0) }
    var error by remember { mutableStateOf<String?>(null) }
    var sending by remember { mutableStateOf(false) }
    val sections = questionnaire.sections
    val section = sections[step]
    val scroll = rememberScrollState()

    BackHandler(enabled = step > 0) { step--; error = null }

    Column(Modifier.verticalScroll(scroll).padding(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text("QUESTIONNAIRE", Modifier.weight(1f), style = MaterialTheme.typography.headlineLarge, color = Rpg.Accent)
            onCancel?.let { TextButton(onClick = it) { Text("Cancel") } }
        }
        Text("Step ${step + 1} of ${sections.size}", color = Rpg.Muted, fontSize = 13.sp)
        Meter((step + 1f) / sections.size, Rpg.Accent)
        SectionContent(section, answers)
        error?.let { Text("❌ $it", color = Rpg.Bad, fontSize = 14.sp) }
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            if (step > 0) OutlinedButton(onClick = { step--; error = null }) { Text("Back") }
            val last = step == sections.lastIndex
            Button(
                enabled = !sending,
                onClick = {
                    error = missing(section, answers)
                    if (error != null) return@Button
                    if (!last) {
                        step++
                        scope.launch { scroll.scrollTo(0) }
                        return@Button
                    }
                    sending = true
                    scope.launch {
                        error = runCatching { api.submitQuestionnaire(toJson(answers)) }.exceptionOrNull()?.message
                        sending = false
                        if (error == null) onDone()
                    }
                },
                modifier = Modifier.weight(1f),
            ) { Text(if (sending) "Working out your plan…" else if (last) "See my plan" else "Next") }
        }
    }
}

@Composable
internal fun SectionContent(section: QSection, answers: SnapshotStateMap<String, Any>) {
    Text(section.title.uppercase(), fontWeight = FontWeight.Black, fontSize = 20.sp)
    if (section.intro.isNotEmpty()) Text(section.intro, color = Rpg.Muted, fontSize = 13.sp)
    section.questions.forEach { q ->
        HudCard {
            Text(q.text + if (q.optional) "  (optional)" else "", fontWeight = FontWeight.Bold)
            QuestionInput(q, answers)
        }
    }
}

@Composable
private fun QuestionInput(q: QQuestion, answers: SnapshotStateMap<String, Any>) {
    when (q.kind) {
        "single" -> q.options.forEach { (value, label) ->
            OptionRow(label, selected = answers[q.id] == value, round = true) { answers[q.id] = value }
        }
        "multi" -> {
            @Suppress("UNCHECKED_CAST")
            val picked = (answers[q.id] as? List<String>).orEmpty()
            q.options.forEach { (value, label) ->
                val on = value in picked
                val full = q.max != null && picked.size >= q.max && !on
                OptionRow(label, selected = on, round = false, enabled = !full) {
                    answers[q.id] = when {
                        on -> picked - value
                        value == "none" -> listOf("none")
                        else -> picked - "none" + value
                    }
                }
            }
        }
        "scale" -> {
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                (1..5).forEach { n ->
                    val on = answers[q.id] == n
                    Text(
                        "$n",
                        Modifier
                            .weight(1f)
                            .border(if (on) 2.dp else 1.dp, if (on) Rpg.Accent else Rpg.Outline, RoundedCornerShape(10.dp))
                            .clickable { answers[q.id] = n }
                            .padding(vertical = 10.dp),
                        fontWeight = FontWeight.Black, color = if (on) Rpg.Accent else Rpg.Text,
                        textAlign = androidx.compose.ui.text.style.TextAlign.Center,
                    )
                }
            }
            Row {
                Text(q.minLabel, Modifier.weight(1f), color = Rpg.Muted, fontSize = 12.sp)
                Text(q.maxLabel, color = Rpg.Muted, fontSize = 12.sp)
            }
        }
        "number" -> TextInput(
            answers[q.id]?.let { fmtAnswer(it) }.orEmpty(),
            { text -> if (text.isBlank()) answers.remove(q.id) else text.replace(',', '.').toDoubleOrNull()?.let { answers[q.id] = it } ?: run { answers[q.id] = text } },
            if (q.unit.isNotEmpty()) q.unit else "Number", numeric = true,
        )
        "text" -> TextInput((answers[q.id] as? String).orEmpty(), { answers[q.id] = it }, "Your answer")
        "rank" -> {
            @Suppress("UNCHECKED_CAST")
            val order = (answers[q.id] as? List<String>) ?: q.options.map { it.first }.also { answers[q.id] = it }
            val labels = q.options.toMap()
            order.forEachIndexed { i, value ->
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text("${i + 1}", Modifier.width(24.dp), color = Rpg.Accent, fontWeight = FontWeight.Black)
                    Text("${categoryIcon(value)}  ${labels[value] ?: value}", Modifier.weight(1f), fontWeight = FontWeight.Bold)
                    TextButton(onClick = { answers[q.id] = order.toMutableList().apply { add(i - 1, removeAt(i)) } }, enabled = i > 0) { Text("↑") }
                    TextButton(onClick = { answers[q.id] = order.toMutableList().apply { add(i + 1, removeAt(i)) } }, enabled = i < order.lastIndex) { Text("↓") }
                }
            }
        }
    }
}

@Composable
private fun OptionRow(label: String, selected: Boolean, round: Boolean, enabled: Boolean = true, onClick: () -> Unit) {
    Row(
        Modifier
            .fillMaxWidth()
            .border(1.dp, if (selected) Rpg.Accent else Rpg.Outline.copy(alpha = 0.6f), RoundedCornerShape(12.dp))
            .clickable(enabled = enabled, onClick = onClick)
            .padding(horizontal = 12.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Text(
            when {
                round && selected -> "◉"
                round -> "○"
                selected -> "☑"
                else -> "☐"
            },
            color = if (selected) Rpg.Accent else Rpg.Muted, fontSize = 18.sp,
        )
        Text(label, color = if (enabled) Rpg.Text else Rpg.Muted)
    }
}

/** Your last answers, with what's newer in your profile on top */
private fun startingAnswers(q: Questionnaire): Map<String, Any> {
    val start = mutableMapOf<String, Any>()
    q.prefill.keys().forEach { key ->
        when (val v = q.prefill.get(key)) {
            is JSONArray -> start[key] = (0 until v.length()).map(v::getString)
            JSONObject.NULL -> Unit
            else -> start[key] = v
        }
    }
    return start
}

/** The first unanswered required question in a section, as a message; null when all are done */
internal fun missing(section: QSection, answers: Map<String, Any>): String? {
    for (q in section.questions) {
        val a = answers[q.id]
        val empty = a == null || (a is String && a.isBlank()) || (a is List<*> && a.isEmpty())
        if (empty && !q.optional) return "Answer \"${q.text}\""
        if (q.kind == "number" && a != null && a !is Number) return "\"${q.text}\": enter a number"
        if (q.kind == "number" && a is Number) {
            val n = a.toDouble()
            if ((q.min != null && n < q.min) || (q.max != null && n > q.max)) return "\"${q.text}\": ${q.min} to ${q.max}"
        }
    }
    return null
}

private fun toJson(answers: Map<String, Any>): JSONObject = JSONObject().apply {
    answers.forEach { (key, value) ->
        put(key, when (value) {
            is List<*> -> JSONArray(value)
            is Double -> if (value % 1.0 == 0.0 && key != "weight_kg") value.toInt() else value
            else -> value
        })
    }
}

private fun fmtAnswer(value: Any) = when (value) {
    is Double -> if (value % 1.0 == 0.0) value.toLong().toString() else value.toString()
    else -> value.toString()
}

/** What matters, where to focus, the plan (each step can become a goal), tips, and past attempts. */
@Composable
internal fun QuestionnaireResults(api: Api?, latest: Attempt, attempts: List<Attempt>, onRetake: () -> Unit, onOpen: (Dest) -> Unit) {
    val r = latest.results
    Column(Modifier.verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text("YOUR PLAN", Modifier.weight(1f), style = MaterialTheme.typography.headlineLarge, color = Rpg.Accent)
            TextButton(onClick = onRetake) { Text("Retake") }
        }
        Text("From your answers on ${latest.createdAt.take(10)}. Retake it whenever your life changes; every attempt is kept.", color = Rpg.Muted, fontSize = 13.sp)

        SectionTitle("What matters to you")
        HudCard {
            r.priorities.forEachIndexed { i, p ->
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text("${i + 1}", Modifier.width(22.dp), color = Rpg.Accent, fontWeight = FontWeight.Black)
                    Text("${categoryIcon(p.key)}  ${p.name}", Modifier.weight(1f), fontWeight = if (p.key in r.focus) FontWeight.Black else FontWeight.Normal)
                    Text(if (p.tracked) "${p.level}" else "~${p.level}", fontWeight = FontWeight.Bold)
                    Text("  ${rankLetter(p.level)}", Modifier.width(40.dp), color = rankColor(rankLetter(p.level)), fontWeight = FontWeight.Black)
                }
            }
            Text("~ = estimated from your answers until there's tracked data", color = Rpg.Muted, fontSize = 11.sp)
        }

        SectionTitle("Focus on")
        Text(
            r.focus.joinToString("  ·  ") { key -> "${categoryIcon(key)} ${r.priorities.firstOrNull { it.key == key }?.name ?: key}" },
            fontWeight = FontWeight.Black, fontSize = 16.sp,
        )
        Text("Where what matters most to you is furthest behind.", color = Rpg.Muted, fontSize = 12.sp)

        SectionTitle("Change these, in this order")
        r.plan.forEachIndexed { i, step -> PlanCard(api, i + 1, step, onOpen) }

        if (r.tips.isNotEmpty()) {
            SectionTitle("What works for you")
            HudCard { r.tips.forEach { Text("• $it", fontSize = 14.sp) } }
        }

        if (attempts.size > 1) {
            SectionTitle("Past attempts")
            HudCard {
                attempts.forEach { a ->
                    Row {
                        Text(a.createdAt.take(10), Modifier.width(100.dp), color = Rpg.Muted, fontSize = 13.sp)
                        Text("Focus: " + a.results.focus.joinToString(", ") { key -> a.results.priorities.firstOrNull { it.key == key }?.name ?: key }, fontSize = 13.sp)
                    }
                }
            }
        }
    }
}

@Composable
private fun PlanCard(api: Api?, number: Int, step: PlanStep, onOpen: (Dest) -> Unit) {
    val scope = rememberCoroutineScope()
    var added by remember { mutableStateOf<String?>(null) }
    HudCard {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text("$number", Modifier.width(24.dp), color = Rpg.Accent, fontWeight = FontWeight.Black, fontSize = 18.sp)
            Column(Modifier.weight(1f)) {
                Text(step.title, fontWeight = FontWeight.Black, fontSize = 16.sp)
                Text("${categoryIcon(step.category)} ${step.categoryName}", color = Rpg.Muted, fontSize = 12.sp)
            }
        }
        Text(step.why, color = Rpg.Muted, fontSize = 13.sp)
        Text("First step: ${step.firstStep}", fontSize = 14.sp)
        step.goal?.let { goal ->
            Row(verticalAlignment = Alignment.CenterVertically) {
                if (added == null) {
                    TextButton(onClick = {
                        scope.launch {
                            added = runCatching { api?.createGoal(JSONObject(goal.toString()).put("intensity", 5)); "✓ Goal added" }
                                .getOrElse { "❌ ${it.message}" }
                        }
                    }) { Text("🎯 Make it a goal") }
                } else {
                    Text(added!!, color = if (added!!.startsWith("✓")) Rpg.Good else Rpg.Bad, fontSize = 13.sp, modifier = Modifier.padding(end = 8.dp))
                    if (added!!.startsWith("✓")) TextButton(onClick = { onOpen(Dest.Goals) }) { Text("Open goals") }
                }
            }
        }
    }
}

/** The server's F → SSS ladder, for estimates the server didn't grade */
internal fun rankLetter(score: Int) = Ranks.first { score >= it.min }.letter
