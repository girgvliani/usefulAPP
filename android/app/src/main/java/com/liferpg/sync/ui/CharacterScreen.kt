package com.liferpg.sync.ui

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
import com.liferpg.sync.Category
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
    // Character → category → stat; Back walks the same way
    var openCategory by remember { mutableStateOf<String?>(null) }
    var openStat by remember { mutableStateOf<String?>(null) }
    LoadView(sheet) { (data, name) ->
        val category = data.categories.firstOrNull { it.key == openCategory }
        val stat = data.stats.firstOrNull { it.code == openStat }
        when {
            stat != null -> StatDetailScreen(api, stat, backLabel = category?.name ?: "Character", onBack = { openStat = null })
            category != null -> CategoryScreen(api, data, category, onBack = { openCategory = null }, onOpenStat = { openStat = it.code })
            else -> CharacterSheetView(
                data, name, levelState?.level,
                onOpen = { openStat = it.code },
                onOpenCategory = { openCategory = it.key },
                onRefresh = {
                    sheet.reload()
                    scope.launch { levelState?.refresh() }
                },
            )
        }
    }
}

@Composable
internal fun CharacterSheetView(
    sheet: CharacterSheet,
    name: String?,
    level: Level?,
    onOpen: (Stat) -> Unit = {},
    onOpenCategory: (Category) -> Unit = {},
    onRefresh: () -> Unit,
) {
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

        // A server from before the categories sends none: show the nine stats as before
        val byCategory = sheet.categories.isNotEmpty()
        HudCard {
            if (byCategory) CategoryRadar(sheet.categories, onSelect = onOpenCategory) else StatRadar(sheet.stats, onSelect = onOpen)
            Text(
                if (byCategory) "Tap a slice to open that category" else "Tap a slice to open that stat",
                color = Rpg.Muted, fontSize = 12.sp, modifier = Modifier.align(Alignment.CenterHorizontally),
            )
        }

        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            TotalPanel(sheet.overall, sheet.overallGrade, Modifier.weight(1f))
            RankLegend(Modifier.weight(1.3f))
        }

        if (byCategory) {
            SectionTitle("Categories · tap one to open it")
            sheet.categories.forEach { CategoryCard(it, sheet.statsOf(it), onOpenCategory, onOpen) }
        } else {
            SectionTitle("Stats · tap one for its full page")
            sheet.stats.forEach { StatRow(it, onOpen) }
        }
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
internal fun StatRow(stat: Stat, onOpen: (Stat) -> Unit) {
    val color = statColor(stat.code)
    HudCard(Modifier.clickable { onOpen(stat) }) {
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
        } else if (stat.bestMove != null) {
            Text("💡 ${stat.bestMove} (up to +${stat.bestMovePoints})", color = Rpg.Muted, fontSize = 13.sp)
        }
    }
}

/** Bar with a tick at the A edge, so S-tier scores visibly break past it. */
@Composable
internal fun ScoreBar(score: Int?, color: androidx.compose.ui.graphics.Color) {
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
