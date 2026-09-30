package com.liferpg.sync.ui

import androidx.compose.animation.animateContentSize
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
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
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.liferpg.sync.Api
import com.liferpg.sync.CharacterSheet
import com.liferpg.sync.Level
import com.liferpg.sync.Stat
import kotlinx.coroutines.launch

@Composable
fun CharacterScreen(api: Api) {
    // The name on the card comes from the profile; the sheet still shows if that call fails
    val sheet = rememberLoader { api.character() to runCatching { api.profile().displayName }.getOrNull() }
    val levelState = LocalLevel.current
    val scope = rememberCoroutineScope()
    LoadView(sheet) { (data, name) ->
        CharacterSheetView(data, name, levelState?.level, onRefresh = {
            sheet.reload()
            scope.launch { levelState?.refresh() }
        })
    }
}

@Composable
internal fun CharacterSheetView(sheet: CharacterSheet, name: String?, level: Level?, onRefresh: () -> Unit) {
    Column(
        Modifier.verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text("“${(name ?: "Your character").uppercase()}”", style = MaterialTheme.typography.headlineLarge, color = Rpg.Accent)
                Text(sheet.date, color = Rpg.Muted, fontSize = 13.sp)
            }
            TextButton(onClick = onRefresh) { Text("↻ Refresh") }
        }

        level?.let { LevelHero(it) }

        HudCard {
            StatRadar(sheet.stats)
        }

        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            TotalPanel(sheet.overall, sheet.overallGrade, Modifier.weight(1f))
            RankLegend(Modifier.weight(1.3f))
        }

        SectionTitle("Stats · tap for the breakdown")
        sheet.stats.forEach { StatRow(it) }
    }
}

/** Tall enough for the rank legend (F to A+; S and above stay a surprise) */
private val PANEL_HEIGHT = 240.dp

@Composable
private fun TotalPanel(total: Int?, grade: String?, modifier: Modifier) {
    HudCard(modifier.height(PANEL_HEIGHT)) {
        SectionTitle("Total")
        Text(total?.toString() ?: "–", fontSize = 44.sp, fontWeight = FontWeight.Black, color = Rpg.Text)
        Box(
            Modifier
                .fillMaxWidth()
                .fillMaxHeight()
                .background(Brush.verticalGradient(listOf(rankColor(grade).copy(alpha = 0.25f), Rpg.Surface)), RoundedCornerShape(12.dp)),
            contentAlignment = Alignment.Center,
        ) {
            Text(grade ?: "–", fontSize = 48.sp, fontWeight = FontWeight.Black, color = rankColor(grade))
        }
    }
}

@Composable
private fun RankLegend(modifier: Modifier) {
    HudCard(modifier.height(PANEL_HEIGHT)) {
        SectionTitle("Ranks")
        Column {
            Ranks.filter { it.min < CHART_EDGE }.forEach { rank ->
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text("▸ ${rank.letter}", Modifier.width(44.dp), color = rankColor(rank.letter), fontWeight = FontWeight.Black, fontSize = 11.sp)
                    Text("${rank.min}–${rank.max}", color = Rpg.Muted, fontSize = 11.sp)
                }
            }
        }
    }
}

@Composable
private fun StatRow(stat: Stat) {
    var open by remember { mutableStateOf(false) }
    val color = statColor(stat.code)
    HudCard(Modifier.clickable { open = !open }.animateContentSize()) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            Box(
                Modifier.size(40.dp).border(2.dp, color, RoundedCornerShape(10.dp)),
                contentAlignment = Alignment.Center,
            ) { Text(stat.code, color = color, fontWeight = FontWeight.Black, fontSize = 12.sp) }
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Row(verticalAlignment = Alignment.Bottom) {
                    Text(stat.name, Modifier.weight(1f), fontWeight = FontWeight.Bold)
                    Text(stat.score?.toString() ?: "–", fontWeight = FontWeight.Black, fontSize = 18.sp)
                    Text("  ${stat.grade ?: ""}", color = rankColor(stat.grade), fontWeight = FontWeight.Black)
                }
                ScoreBar(stat.score, color)
            }
        }

        if (stat.score == null) {
            Text(stat.components.firstOrNull()?.note ?: "No data yet", color = Rpg.Muted, fontSize = 13.sp)
        } else if (!open && stat.bestMove != null) {
            Text("💡 ${stat.bestMove} (up to +${stat.bestMovePoints})", color = Rpg.Muted, fontSize = 13.sp)
        }

        if (open) Breakdown(stat)
    }
}

/** Bar with a tick at the A edge, so S-tier scores visibly break past it. */
@Composable
private fun ScoreBar(score: Int?, color: androidx.compose.ui.graphics.Color) {
    Box(Modifier.fillMaxWidth()) {
        Meter((score ?: 0) / 100f, color)
        Box(
            Modifier
                .fillMaxWidth(CHART_EDGE / 100f)
                .height(6.dp),
            contentAlignment = Alignment.CenterEnd,
        ) { Box(Modifier.width(2.dp).height(10.dp).background(Rpg.Text.copy(alpha = 0.7f))) }
    }
}

@Composable
private fun Breakdown(stat: Stat) {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        stat.components.forEach { c ->
            Row {
                Text(c.name, Modifier.weight(1f), fontSize = 13.sp)
                Text(
                    if (c.score == null) "—" else "%.1f / %.0f".format(c.score * c.weight, c.weight),
                    fontSize = 13.sp,
                    color = if (c.score == null) Rpg.Muted else Rpg.Text,
                )
            }
            Text(c.note, color = Rpg.Muted, fontSize = 11.sp, modifier = Modifier.padding(bottom = 2.dp))
        }
        stat.penalties.forEach { p ->
            Row {
                Text("⚠ ${p.name}", Modifier.weight(1f), fontSize = 13.sp, color = Rpg.Bad)
                Text("-%.0f".format(p.points), fontSize = 13.sp, color = Rpg.Bad)
            }
        }
        stat.ceiling?.let { Text("🔒 Max $it today (${stat.ceilingNote})", fontSize = 12.sp, color = Rpg.Muted) }
        if (stat.confidence < 100) Text("${100 - stat.confidence}% of this stat had no data yet", fontSize = 12.sp, color = Rpg.Muted)
        stat.bestMove?.let { Text("💡 Biggest gain: $it (up to +${stat.bestMovePoints})", fontSize = 13.sp, color = Rpg.Accent) }
    }
}
