package com.liferpg.sync.ui

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.liferpg.sync.Api
import com.liferpg.sync.Category
import com.liferpg.sync.CharacterSheet
import com.liferpg.sync.Stat

private val ICONS = mapOf(
    "mental" to "🧠", "physical" to "💪", "practical" to "🛠️", "cultural" to "📚", "discipline" to "🛡️", "social" to "👥",
)

private val BLURBS = mapOf(
    "mental" to "Mental energy and attention: sleep, deep work, and what the phone does to your focus.",
    "physical" to "Strength, stamina, and how you eat and weigh.",
    "practical" to "Earning and providing: income against your monthly goal.",
    "cultural" to "Learning, reading and skills.",
    "discipline" to "Doing what you said you'd do: check-ins, habits, tasks on time, eating within your target.",
    "social" to "Real time with people.",
)

fun categoryIcon(key: String) = ICONS[key] ?: "◆"

fun categoryBlurb(key: String) = BLURBS[key].orEmpty()

/** A category on the Character screen: its score, then each of its stats on a line you can tap. */
@Composable
internal fun CategoryCard(category: Category, stats: List<Stat>, onOpen: (Category) -> Unit, onOpenStat: (Stat) -> Unit) {
    HudCard {
        Row(Modifier.fillMaxWidth().clickable { onOpen(category) }, verticalAlignment = Alignment.CenterVertically) {
            Text(categoryIcon(category.key), fontSize = 24.sp)
            Column(Modifier.weight(1f).padding(start = 10.dp)) {
                Text(category.name.uppercase(), fontWeight = FontWeight.Black, fontSize = 17.sp)
                Text(stats.joinToString(" · ") { it.name }, color = Rpg.Muted, fontSize = 12.sp)
            }
            Text(category.score?.toString() ?: "–", fontWeight = FontWeight.Black, fontSize = 22.sp)
            Text("  ${category.grade ?: ""}", color = rankColor(category.grade), fontWeight = FontWeight.Black, fontSize = 18.sp)
            Text("  ›", color = Rpg.Accent, fontSize = 22.sp, fontWeight = FontWeight.Black)
        }
        ScoreBar(category.score, Rpg.Accent)
        // A category of one stat is that stat, so the line would only repeat the header
        if (stats.size > 1) stats.forEach { MiniStatRow(it, onOpenStat) }
    }
}

@Composable
private fun MiniStatRow(stat: Stat, onOpen: (Stat) -> Unit) {
    Row(Modifier.fillMaxWidth().clickable { onOpen(stat) }.padding(vertical = 2.dp), verticalAlignment = Alignment.CenterVertically) {
        Text(stat.code, Modifier.width(44.dp), color = statColor(stat.code), fontWeight = FontWeight.Black, fontSize = 12.sp)
        Text(stat.name, Modifier.weight(1f), fontSize = 14.sp)
        Text(stat.score?.toString() ?: "–", fontWeight = FontWeight.Bold, fontSize = 14.sp)
        Text(" ${stat.grade ?: ""}", Modifier.width(36.dp), color = rankColor(stat.grade), fontWeight = FontWeight.Black, fontSize = 13.sp)
    }
}

/** A category's own page: what it covers, its 30-day trend, and its stats (tap one for its full page). */
@Composable
fun CategoryScreen(api: Api, sheet: CharacterSheet, category: Category, onBack: () -> Unit, onOpenStat: (Stat) -> Unit) {
    BackHandler(onBack = onBack)
    val history = rememberLoader { api.history(30).map { it.date to it.categories[category.key] } }
    CategoryContent(category, sheet.statsOf(category), (history.value as? Load.Ready)?.value, onBack, onOpenStat)
}

@Composable
internal fun CategoryContent(category: Category, stats: List<Stat>, history: List<Pair<String, Int?>>?, onBack: () -> Unit, onOpenStat: (Stat) -> Unit) {
    Column(Modifier.verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        TextButton(onClick = onBack) { Text("← Character") }

        HudCard {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Box(Modifier.size(52.dp).border(2.dp, Rpg.Accent, RoundedCornerShape(14.dp)), contentAlignment = Alignment.Center) {
                    Text(categoryIcon(category.key), fontSize = 26.sp)
                }
                Column(Modifier.weight(1f)) {
                    Text(category.name.uppercase(), style = MaterialTheme.typography.titleLarge)
                    Text(
                        if (stats.size > 1) "Average of ${stats.joinToString(", ") { it.name }}" else "From ${stats.firstOrNull()?.name ?: "–"}",
                        color = Rpg.Muted, fontSize = 12.sp,
                    )
                }
                Text(category.score?.toString() ?: "–", fontWeight = FontWeight.Black, fontSize = 40.sp)
                Text(" ${category.grade ?: ""}", color = rankColor(category.grade), fontWeight = FontWeight.Black, fontSize = 26.sp)
            }
            ScoreBar(category.score, Rpg.Accent)
            Text(categoryBlurb(category.key), color = Rpg.Muted, fontSize = 13.sp)
            stats.filter { it.bestMove != null }.maxByOrNull { it.bestMovePoints ?: 0 }?.let {
                Text("💡 Biggest gain: ${it.bestMove} in ${it.name} (up to +${it.bestMovePoints})", color = Rpg.Accent, fontSize = 14.sp, fontWeight = FontWeight.Bold)
            }
        }

        if (history != null && history.any { it.second != null }) {
            SectionTitle("Last ${history.size} days · drag to read a day")
            HudCard { TrendLine(history) }
        }

        SectionTitle(if (stats.size > 1) "Its stats · tap one for its full page" else "Its stat · tap for the full page")
        stats.forEach { StatRow(it, onOpenStat) }
    }
}
