package com.liferpg.sync.ui

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.border
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
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
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.liferpg.sync.Api
import com.liferpg.sync.Stat
import kotlin.math.roundToInt

/** A stat's own page: its score split into categories, a tip for every part that isn't full, 30 days of history. */
@Composable
fun StatDetailScreen(api: Api, stat: Stat, backLabel: String = "Character", onBack: () -> Unit) {
    BackHandler(onBack = onBack)
    val history = rememberLoader { api.history(30).map { it.date to it.stats[stat.code] } }
    StatDetailContent(stat, (history.value as? Load.Ready)?.value, onBack, backLabel)
}

@Composable
internal fun StatDetailContent(stat: Stat, history: List<Pair<String, Int?>>?, onBack: () -> Unit, backLabel: String = "Character") {
    Column(Modifier.verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        TextButton(onClick = onBack) { Text("← $backLabel") }

        HudCard {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Box(
                    Modifier.size(52.dp).border(2.dp, statColor(stat.code), RoundedCornerShape(14.dp)),
                    contentAlignment = Alignment.Center,
                ) { Text(stat.code, color = statColor(stat.code), fontWeight = FontWeight.Black) }
                Column(Modifier.weight(1f)) {
                    Text(stat.name.uppercase(), style = MaterialTheme.typography.titleLarge)
                    Text(
                        if (stat.confidence < 100) "${stat.confidence}% of this stat has data" else "Based on all its parts",
                        color = Rpg.Muted, fontSize = 12.sp,
                    )
                }
                Text(stat.score?.toString() ?: "–", fontWeight = FontWeight.Black, fontSize = 40.sp)
                Text(" ${stat.grade ?: ""}", color = rankColor(stat.grade), fontWeight = FontWeight.Black, fontSize = 26.sp)
            }
            ScoreBar(stat.score, statColor(stat.code))
            stat.ceiling?.let { Text("🔒 Max $it today (${stat.ceilingNote})", color = Rpg.Muted, fontSize = 13.sp) }
            stat.bestMove?.let { Text("💡 Biggest gain: $it (up to +${stat.bestMovePoints})", color = Rpg.Accent, fontSize = 14.sp, fontWeight = FontWeight.Bold) }
        }

        SectionTitle("Where the points come from")
        categoriesOf(stat).forEach { CategoryCard(it) }

        if (history != null && history.any { it.second != null }) {
            SectionTitle("Last ${history.size} days · drag to read a day")
            HudCard { TrendLine(history) }
        }
    }
}

@Composable
private fun CategoryCard(category: StatCategory) {
    HudCard {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(category.title, Modifier.weight(1f), fontWeight = FontWeight.Black, fontSize = 17.sp)
            when {
                category.isDrain -> Text("−%.0f".format(-category.earned), color = Rpg.Bad, fontWeight = FontWeight.Black, fontSize = 17.sp)
                category.hasData -> Text("%.0f / %.0f".format(category.earned, category.max), fontWeight = FontWeight.Black, fontSize = 17.sp)
                else -> Text("no data", color = Rpg.Muted, fontSize = 13.sp)
            }
        }
        if (!category.isDrain && category.hasData) Meter((category.earned / category.max).toFloat(), Rpg.Accent)

        category.parts.forEach { part ->
            Column(
                Modifier.fillMaxWidth().border(1.dp, Rpg.Outline.copy(alpha = 0.5f), RoundedCornerShape(12.dp)).padding(10.dp),
                verticalArrangement = Arrangement.spacedBy(4.dp),
            ) {
                Row {
                    Text(part.name, Modifier.weight(1f), fontSize = 14.sp, fontWeight = FontWeight.Bold)
                    Text(
                        when {
                            category.isDrain -> "−%.0f".format(part.max)
                            part.earned == null -> "—"
                            else -> "%.1f / %.0f".format(part.earned, part.max)
                        },
                        color = if (category.isDrain) Rpg.Bad else Rpg.Text, fontSize = 14.sp, fontWeight = FontWeight.Bold,
                    )
                }
                if (!category.isDrain && part.earned != null) Meter((part.earned / part.max).toFloat(), Rpg.Accent.copy(alpha = 0.8f))
                if (part.note.isNotEmpty()) Text(part.note, color = Rpg.Muted, fontSize = 12.sp)
                part.tip?.let { Text("💡 $it", color = Rpg.Accent, fontSize = 12.sp) }
            }
        }
    }
}

/** Daily scores (0-100) with a hairline at the A edge; drag or tap to read a day. */
@Composable
internal fun TrendLine(points: List<Pair<String, Int?>>) {
    var selected by remember(points) { mutableStateOf(points.indexOfLast { it.second != null }) }
    val shown = points.getOrNull(selected)
    Row {
        Text(shown?.first?.substring(5)?.replace('-', '/') ?: "", Modifier.weight(1f), color = Rpg.Muted, fontSize = 13.sp)
        Text(shown?.second?.toString() ?: "no data", fontWeight = FontWeight.Black, fontSize = 15.sp)
    }
    Canvas(
        Modifier
            .fillMaxWidth()
            .height(120.dp)
            .pointerInput(points) {
                fun pick(x: Float) {
                    selected = (x / size.width * (points.size - 1)).roundToInt().coerceIn(0, points.lastIndex)
                }
                detectTapGestures { pick(it.x) }
            }
            .pointerInput(points) {
                detectDragGestures { change, _ ->
                    selected = (change.position.x / size.width * (points.size - 1)).roundToInt().coerceIn(0, points.lastIndex)
                }
            },
    ) {
        val pad = 6.dp.toPx()
        fun x(i: Int) = if (points.size < 2) size.width / 2 else i * size.width / (points.size - 1)
        fun y(v: Int) = pad + (1 - v / 100f) * (size.height - 2 * pad)
        drawLine(Rpg.Outline, Offset(0f, y(CHART_EDGE.toInt())), Offset(size.width, y(CHART_EDGE.toInt())), strokeWidth = 1.dp.toPx())
        drawLine(Rpg.Outline, Offset(0f, y(0)), Offset(size.width, y(0)), strokeWidth = 1.dp.toPx())

        // A line per run of days with data; gaps where a day has none
        var path: Path? = null
        points.forEachIndexed { i, (_, v) ->
            if (v == null) {
                path?.let { drawPath(it, Rpg.Accent, style = Stroke(2.dp.toPx(), cap = StrokeCap.Round, join = StrokeJoin.Round)) }
                path = null
            } else {
                path = (path ?: Path().apply { moveTo(x(i), y(v)) }).apply { lineTo(x(i), y(v)) }
            }
        }
        path?.let { drawPath(it, Rpg.Accent, style = Stroke(2.dp.toPx(), cap = StrokeCap.Round, join = StrokeJoin.Round)) }

        points.getOrNull(selected)?.let { (_, v) ->
            drawLine(Rpg.Muted, Offset(x(selected), 0f), Offset(x(selected), size.height), strokeWidth = 1.dp.toPx())
            if (v != null) {
                drawCircle(Rpg.Surface, 6.dp.toPx(), Offset(x(selected), y(v)))
                drawCircle(Rpg.Accent, 4.dp.toPx(), Offset(x(selected), y(v)))
            }
        }
    }
}
