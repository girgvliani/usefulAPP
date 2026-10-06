package com.liferpg.sync.ui

import androidx.compose.foundation.border
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
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
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
import com.liferpg.sync.BabySteps
import kotlinx.coroutines.launch
import org.json.JSONArray
import org.json.JSONObject

/** Dave Ramsey's 7 Baby Steps: which one you're on, how far along each is, and your numbers. */
@Composable
fun BabyStepsScreen(api: Api) {
    val levelState = LocalLevel.current
    val data = rememberLoader { api.babySteps() }
    var shown by remember { mutableStateOf<BabySteps?>(null) }
    val scope = rememberCoroutineScope()
    var message by remember { mutableStateOf<String?>(null) }
    LoadView(data) { loaded ->
        val steps = shown ?: loaded
        Column(Modifier.verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            BabyStepsList(steps)
            BabyStepsForm(steps, message) { body ->
                scope.launch {
                    runCatching { api.saveBabySteps(body) }
                        .onSuccess { shown = it; message = "✓ Saved"; levelState?.refresh() }
                        .onFailure { message = "❌ ${it.message}" }
                }
            }
        }
    }
}

/** The seven steps, the one you're on highlighted */
@Composable
internal fun BabyStepsList(steps: BabySteps) {
    Text("BABY STEPS", style = MaterialTheme.typography.headlineLarge, color = Rpg.Accent)
    Text(
        "Dave Ramsey's 7 steps, in order: each one counts toward Wealth once every step before it is done (4, 5 and 6 run together).",
        color = Rpg.Muted, fontSize = 13.sp,
    )
    steps.steps.forEach { s ->
        val color = when {
            !s.applies -> Rpg.Muted
            s.current -> Rpg.Accent
            s.done -> Rpg.Good
            else -> Rpg.Outline
        }
        Column(
            Modifier.fillMaxWidth().border(if (s.current) 2.dp else 1.dp, color, RoundedCornerShape(16.dp)).padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(if (!s.applies) "–" else if (s.done) "✅" else "${s.step}", Modifier.width(32.dp), fontWeight = FontWeight.Black, fontSize = 18.sp, color = color)
                Column(Modifier.weight(1f)) {
                    Text(s.title, fontWeight = FontWeight.Black)
                    Text(s.detail, color = Rpg.Muted, fontSize = 12.sp)
                }
                if (s.current) Text("YOU'RE HERE", color = Rpg.Accent, fontWeight = FontWeight.Black, fontSize = 11.sp)
            }
            if (s.applies) Meter((s.progress ?: 0.0).toFloat(), if (s.done) Rpg.Good else Rpg.Accent)
            Text(s.note, color = Rpg.Muted, fontSize = 12.sp)
        }
    }
}

/** Your numbers. Debts are listed for the snowball: smallest balance first. */
@Composable
internal fun BabyStepsForm(steps: BabySteps, message: String?, onSave: (JSONObject) -> Unit) {
    val p = steps.plan
    val money = steps.currency
    fun num(key: String) = if (p.isNull(key)) "" else p.optDouble(key).let { if (it % 1.0 == 0.0) it.toLong().toString() else it.toString() }
    var saved by remember(p) { mutableStateOf(num("saved")) }
    var starter by remember(p) { mutableStateOf(num("starter_target")) }
    var expenses by remember(p) { mutableStateOf(num("monthly_expenses")) }
    var months by remember(p) { mutableStateOf(p.optInt("months", 6)) }
    var invest by remember(p) { mutableStateOf(num("invest_percent")) }
    var kids by remember(p) { mutableStateOf(p.optBoolean("kids")) }
    var collegeSaved by remember(p) { mutableStateOf(num("college_saved")) }
    var collegeTarget by remember(p) { mutableStateOf(num("college_target")) }
    var home by remember(p) { mutableStateOf(p.optString("home", "renting")) }
    var mortgageBalance by remember(p) { mutableStateOf(num("mortgage_balance")) }
    var mortgageOriginal by remember(p) { mutableStateOf(num("mortgage_original")) }
    var giving by remember(p) { mutableStateOf(p.optBoolean("giving")) }
    val debts = remember(p) {
        mutableStateListOf<Triple<String, String, String>>().apply {
            val list = p.optJSONArray("debts") ?: JSONArray()
            for (i in 0 until list.length()) list.getJSONObject(i).let { add(Triple(it.getString("name"), it.optDouble("balance").toLong().toString(), it.optDouble("original").toLong().toString())) }
        }
    }
    var error by remember { mutableStateOf<String?>(null) }

    fun amount(raw: String, label: String, required: Boolean = false): Double? {
        val text = raw.trim().replace(",", "")
        if (text.isEmpty()) return if (required) error("$label: enter an amount") else null
        return text.toDoubleOrNull()?.takeIf { it >= 0 } ?: error("$label: enter an amount")
    }

    SectionTitle("Your numbers ($money)")
    HudCard {
        Text("Steps 1 and 3 · emergency fund", fontWeight = FontWeight.Bold)
        TextInput(saved, { saved = it }, "Emergency fund saved", numeric = true)
        TextInput(starter, { starter = it }, "Starter fund target (Ramsey: \$1,000)", numeric = true)
        TextInput(expenses, { expenses = it }, "Monthly expenses", numeric = true)
        Text("Full fund: how many months of expenses", color = Rpg.Muted, fontSize = 12.sp)
        ChoiceChips((3..6).map { it to "$it" }, months) { months = it }
    }
    HudCard {
        Text("Step 2 · debts (not the house)", fontWeight = FontWeight.Bold)
        debts.forEachIndexed { i, (name, balance, original) ->
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                TextInput(name, { debts[i] = Triple(it, balance, original) }, "Debt")
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Column(Modifier.weight(1f)) { TextInput(balance, { debts[i] = Triple(name, it, original) }, "Left", numeric = true) }
                    Column(Modifier.weight(1f)) { TextInput(original, { debts[i] = Triple(name, balance, it) }, "Started at", numeric = true) }
                }
                TextButton(onClick = { debts.removeAt(i) }) { Text("Remove", color = Rpg.Bad) }
            }
        }
        TextButton(onClick = { debts.add(Triple("", "", "")) }) { Text("+ Add a debt") }
        if (debts.isEmpty()) Text("No debts? Step 2 is already done.", color = Rpg.Muted, fontSize = 12.sp)
    }
    HudCard {
        Text("Steps 4-7", fontWeight = FontWeight.Bold)
        TextInput(invest, { invest = it }, "% of income invested for retirement", numeric = true)
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text("I have children (step 5)", Modifier.weight(1f))
            Switch(checked = kids, onCheckedChange = { kids = it }, colors = SwitchDefaults.colors(checkedTrackColor = Rpg.Accent))
        }
        if (kids) {
            TextInput(collegeSaved, { collegeSaved = it }, "College fund saved", numeric = true)
            TextInput(collegeTarget, { collegeTarget = it }, "College fund target", numeric = true)
        }
        Text("Home (step 6)", color = Rpg.Muted, fontSize = 12.sp)
        ChoiceChips(listOf("renting" to "Renting", "mortgage" to "Mortgage", "owned" to "Paid off"), home) { home = it }
        if (home == "mortgage") {
            TextInput(mortgageBalance, { mortgageBalance = it }, "Mortgage left", numeric = true)
            TextInput(mortgageOriginal, { mortgageOriginal = it }, "Mortgage started at", numeric = true)
        }
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text("I give regularly (step 7)", Modifier.weight(1f))
            Switch(checked = giving, onCheckedChange = { giving = it }, colors = SwitchDefaults.colors(checkedTrackColor = Rpg.Accent))
        }
    }
    Button(onClick = {
        error = null
        runCatching {
            val body = JSONObject()
                .put("saved", amount(saved, "Emergency fund saved", required = true))
                .put("months", months).put("kids", kids).put("home", home).put("giving", giving)
            amount(starter, "Starter fund target")?.takeIf { it > 0 }?.let { body.put("starter_target", it) }
            amount(expenses, "Monthly expenses")?.takeIf { it > 0 }?.let { body.put("monthly_expenses", it) }
            body.put("invest_percent", amount(invest, "% invested") ?: 0.0)
            if (kids) {
                amount(collegeSaved, "College fund saved")?.let { body.put("college_saved", it) }
                amount(collegeTarget, "College fund target")?.takeIf { it > 0 }?.let { body.put("college_target", it) }
            }
            if (home == "mortgage") {
                amount(mortgageBalance, "Mortgage left")?.let { body.put("mortgage_balance", it) }
                amount(mortgageOriginal, "Mortgage started at")?.takeIf { it > 0 }?.let { body.put("mortgage_original", it) }
            }
            body.put("debts", JSONArray(debts.filter { it.first.isNotBlank() }.map { (name, balance, original) ->
                JSONObject().put("name", name.trim())
                    .put("balance", amount(balance, "$name left", required = true))
                    .put("original", amount(original, "$name started at", required = true)?.takeIf { it > 0 } ?: error("$name: what it started at"))
            }))
            onSave(body)
        }.onFailure { error = it.message }
    }, modifier = Modifier.fillMaxWidth()) { Text("Save") }
    (error?.let { "❌ $it" } ?: message)?.let { Text(it, color = if (it.startsWith("✓")) Rpg.Good else Rpg.Bad, fontSize = 13.sp) }
}
