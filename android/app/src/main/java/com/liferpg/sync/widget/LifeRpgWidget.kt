package com.liferpg.sync.widget

import android.content.Context
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.DpSize
import androidx.compose.ui.unit.sp
import androidx.compose.ui.unit.TextUnit
import androidx.glance.action.ActionParameters
import androidx.glance.action.actionStartActivity
import androidx.glance.action.clickable
import androidx.glance.appwidget.action.ActionCallback
import androidx.glance.appwidget.action.actionRunCallback
import androidx.glance.appwidget.cornerRadius
import androidx.glance.appwidget.GlanceAppWidget
import androidx.glance.appwidget.GlanceAppWidgetReceiver
import androidx.glance.appwidget.lazy.items
import androidx.glance.appwidget.lazy.LazyColumn
import androidx.glance.appwidget.LinearProgressIndicator
import androidx.glance.appwidget.provideContent
import androidx.glance.appwidget.SizeMode
import androidx.glance.background
import androidx.glance.GlanceId
import androidx.glance.GlanceModifier
import androidx.glance.layout.Alignment
import androidx.glance.layout.Box
import androidx.glance.layout.Column
import androidx.glance.layout.fillMaxSize
import androidx.glance.layout.fillMaxWidth
import androidx.glance.layout.height
import androidx.glance.layout.padding
import androidx.glance.layout.Row
import androidx.glance.layout.Spacer
import androidx.glance.layout.width
import androidx.glance.LocalSize
import androidx.glance.text.FontWeight
import androidx.glance.text.Text
import androidx.glance.text.TextAlign
import androidx.glance.text.TextStyle
import androidx.glance.unit.ColorProvider
import com.liferpg.sync.Level
import com.liferpg.sync.MainActivity
import com.liferpg.sync.Streak
import com.liferpg.sync.ui.categoryIcon
import com.liferpg.sync.ui.rankColor
import com.liferpg.sync.ui.Rpg

/**
 * Home-screen widget, Duolingo-style: a face that gets worried when a streak is at risk and angry in
 * the evening (or when one broke), plus your streaks and rank laid out like a weather widget.
 */
class LifeRpgWidget : GlanceAppWidget() {
    override val sizeMode = SizeMode.Responsive(setOf(SMALL, WIDE, LARGE))

    override suspend fun provideGlance(context: Context, id: GlanceId) {
        val data = WidgetCache.load(context)
        provideContent { WidgetContent(data) }
    }

    companion object {
        val SMALL = DpSize(110.dp, 110.dp)
        val WIDE = DpSize(250.dp, 110.dp)
        val LARGE = DpSize(250.dp, 250.dp)
    }
}

class LifeRpgWidgetReceiver : GlanceAppWidgetReceiver() {
    override val glanceAppWidget: GlanceAppWidget = LifeRpgWidget()
}

/** The widget's ↻ */
class RefreshAction : ActionCallback {
    override suspend fun onAction(context: Context, glanceId: GlanceId, parameters: ActionParameters) {
        runCatching { WidgetCache.refresh(context) }
    }
}

@Composable
internal fun WidgetContent(data: WidgetData) {
    val mood = data.streaks?.mood ?: "idle"
    Box(
        GlanceModifier
            .fillMaxSize()
            .background(moodBackground(mood))
            .cornerRadius(24.dp)
            .clickable(actionStartActivity<MainActivity>())
            .padding(12.dp),
    ) {
        when {
            data.streaks == null -> Centered {
                Text("⚔️", style = text(28.sp))
                Text("Open Life RPG to sign in", style = text(13.sp, Rpg.Muted), maxLines = 2)
            }
            LocalSize.current.height >= LifeRpgWidget.LARGE.height -> Large(data)
            LocalSize.current.width >= LifeRpgWidget.WIDE.width -> Wide(data)
            else -> Small(data)
        }
    }
}

@Composable
private fun Small(data: WidgetData) {
    val streaks = data.streaks!!
    val top = ordered(streaks.streaks).first()
    Centered {
        data.level?.let { LevelLine(it, compact = true) }
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(face(streaks.mood), style = text(24.sp))
            Text(" 🔥 ${top.current}", style = text(20.sp, weight = FontWeight.Bold))
        }
        Text(top.name, style = text(12.sp))
        Text(state(top, long = true), style = text(11.sp, stateColor(top)), maxLines = 1)
    }
}

@Composable
private fun Wide(data: WidgetData) {
    val streaks = data.streaks!!
    Row(GlanceModifier.fillMaxSize(), verticalAlignment = Alignment.CenterVertically) {
        Column(GlanceModifier.width(92.dp).padding(end = 8.dp), horizontalAlignment = Alignment.CenterHorizontally) {
            Text(face(streaks.mood), style = text(26.sp))
            val grade = data.sheet?.overallGrade
            Text(grade ?: "–", style = text(20.sp, rankColor(grade), FontWeight.Bold))
            data.level?.let { LevelLine(it, compact = true) }
        }
        // Every streak; scroll for the rest
        LazyColumn(GlanceModifier.defaultWeight()) {
            items(ordered(streaks.streaks), itemId = { it.key.hashCode().toLong() }) { StreakRow(it) }
        }
    }
}

@Composable
private fun Large(data: WidgetData) {
    val streaks = data.streaks!!
    Column(GlanceModifier.fillMaxSize()) {
        Row(GlanceModifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            Text(face(streaks.mood), style = text(30.sp))
            Column(GlanceModifier.defaultWeight().padding(start = 8.dp)) {
                Text(streaks.message, style = text(13.sp, weight = FontWeight.Bold), maxLines = 2)
                Text("Updated ${data.updated ?: "–"}", style = text(10.sp, Rpg.Muted))
            }
            Text("↻", style = text(20.sp, Rpg.Accent, FontWeight.Bold), modifier = GlanceModifier.clickable(actionRunCallback<RefreshAction>()).padding(6.dp))
        }
        data.level?.let { LevelLine(it, compact = false) }
        data.sheet?.let { sheet ->
            Row(GlanceModifier.fillMaxWidth().padding(vertical = 4.dp), verticalAlignment = Alignment.CenterVertically) {
                Text(sheet.overallGrade ?: "–", style = text(26.sp, rankColor(sheet.overallGrade), FontWeight.Bold))
                Spacer(GlanceModifier.width(10.dp))
                Column {
                    Text("TOTAL ${sheet.overall ?: "–"}", style = text(11.sp, Rpg.Muted, FontWeight.Bold))
                    // The category that needs you most; older servers have no categories, so a few stats instead
                    val weakest = sheet.categories.filter { it.score != null }.minByOrNull { it.score!! }
                    if (weakest != null) {
                        Text("Weakest: ${categoryIcon(weakest.key)} ${weakest.name} ${weakest.score}", style = text(12.sp, weight = FontWeight.Bold))
                    } else {
                        Row {
                            sheet.stats.filter { it.code in HEADLINE_STATS }.forEach {
                                Text("${it.code} ${it.score ?: "–"}  ", style = text(12.sp, weight = FontWeight.Bold))
                            }
                        }
                    }
                }
            }
        }
        // Scrolls: every streak as tiles, two per row, then every category and its stats
        LazyColumn(GlanceModifier.defaultWeight().fillMaxWidth()) {
            items(ordered(streaks.streaks).chunked(2), itemId = { pair -> pair.first().key.hashCode().toLong() }) { pair ->
                Row(GlanceModifier.fillMaxWidth().padding(bottom = 4.dp)) {
                    pair.forEachIndexed { index, streak ->
                        if (index == 1) Spacer(GlanceModifier.width(4.dp))
                        StreakTile(streak, GlanceModifier.defaultWeight())
                    }
                }
            }
            items(scoreLines(data), itemId = { line -> line.id.hashCode().toLong() }) { line ->
                Row(GlanceModifier.fillMaxWidth().padding(top = if (line.indent) 2.dp else 6.dp, bottom = 2.dp), verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        line.name,
                        style = if (line.indent) text(12.sp, Rpg.Muted) else text(12.sp, weight = FontWeight.Bold),
                        modifier = GlanceModifier.defaultWeight().padding(start = if (line.indent) 14.dp else 0.dp),
                        maxLines = 1,
                    )
                    Text("${line.score ?: "–"}", style = text(13.sp, weight = FontWeight.Bold))
                    Text("  ${line.grade ?: ""}", style = text(12.sp, rankColor(line.grade), FontWeight.Bold))
                }
            }
        }
    }
}

private class ScoreLine(val id: String, val name: String, val score: Int?, val grade: String?, val indent: Boolean)

/** Each category, with its stats under it when it has more than one; plain stats from an older server. */
private fun scoreLines(data: WidgetData): List<ScoreLine> {
    val sheet = data.sheet ?: return emptyList()
    if (sheet.categories.isEmpty()) return sheet.stats.map { ScoreLine("stat" + it.code, it.name, it.score, it.grade, indent = false) }
    return sheet.categories.flatMap { category ->
        val stats = sheet.statsOf(category)
        listOf(ScoreLine("cat" + category.key, "${categoryIcon(category.key)} ${category.name}", category.score, category.grade, indent = false)) +
            if (stats.size > 1) stats.map { ScoreLine("stat" + it.code, it.name, it.score, it.grade, indent = true) } else emptyList()
    }
}

/** "LV 12", the bar through the level, and XP (plus today's gain when there's room). */
@Composable
private fun LevelLine(level: Level, compact: Boolean) {
    Column(GlanceModifier.fillMaxWidth().padding(vertical = 3.dp)) {
        Row(GlanceModifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            Text("LV ${level.level}" + if (compact || level.title.isEmpty()) "" else " · ${level.title.uppercase()}",
                style = text(if (compact) 12.sp else 14.sp, Rpg.Accent, FontWeight.Bold))
            if (!compact) {
                Text("  %,d XP".format(level.xp), style = text(12.sp), modifier = GlanceModifier.defaultWeight())
                if (level.todayXp > 0) Text("+${level.todayXp} today", style = text(11.sp, Rpg.Good, FontWeight.Bold))
            }
        }
        LinearProgressIndicator(
            progress = level.progress,
            modifier = GlanceModifier.fillMaxWidth().height(4.dp),
            color = ColorProvider(Rpg.Accent),
            backgroundColor = ColorProvider(Rpg.SurfaceHigh),
        )
        if (!compact) Text("%,d XP to LV %d".format(level.toNext, level.level + 1), style = text(10.sp, Rpg.Muted))
    }
}

@Composable
private fun StreakRow(streak: Streak) {
    Row(GlanceModifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Text("${streak.emoji} ${streak.name}", style = text(12.sp), modifier = GlanceModifier.defaultWeight(), maxLines = 1)
        Text("${streak.current}", style = text(13.sp, weight = FontWeight.Bold))
        Text(" ${state(streak)}", style = text(11.sp, stateColor(streak)))
    }
}

@Composable
private fun StreakTile(streak: Streak, modifier: GlanceModifier) {
    Column(modifier.background(Color(0x22FFFFFF)).cornerRadius(12.dp).padding(horizontal = 8.dp, vertical = 5.dp)) {
        Text("${streak.emoji} ${streak.name}", style = text(11.sp, Rpg.Muted), maxLines = 1)
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text("${streak.current}", style = text(18.sp, weight = FontWeight.Bold))
            Text(" ${state(streak)}", style = text(11.sp, stateColor(streak)))
        }
    }
}

@Composable
private fun Centered(content: @Composable () -> Unit) {
    Column(
        GlanceModifier.fillMaxSize(),
        verticalAlignment = Alignment.CenterVertically,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) { content() }
}

private val HEADLINE_STATS = setOf("MP", "FOC", "PS")

/** At-risk streaks first (the ones that need you), then broken, then the rest by length */
private fun ordered(streaks: List<Streak>) = streaks.sortedWith(
    compareByDescending<Streak> { it.atRisk }.thenByDescending { it.brokenToday }.thenByDescending { it.current },
)

private fun state(streak: Streak, long: Boolean = false) = when {
    streak.atRisk -> if (long) "dies at midnight" else "⚠"
    streak.brokenToday -> if (long) "broken today" else "✖"
    streak.doneToday -> if (long) "kept today ✓" else "✓"
    else -> if (long) "start it today" else "–"
}

private fun stateColor(streak: Streak) = when {
    streak.atRisk -> Color(0xFFFFD166)
    streak.brokenToday -> Rpg.Bad
    streak.doneToday -> Rpg.Good
    else -> Rpg.Muted
}

private fun face(mood: String) = when (mood) {
    "happy" -> "😄"
    "worried" -> "😟"
    "angry" -> "😡"
    else -> "😴"
}

private fun moodBackground(mood: String) = ColorProvider(
    when (mood) {
        "angry" -> Color(0xFF7F1D1D)
        "worried" -> Color(0xFF6B3A0F)
        else -> Rpg.Surface
    },
)

private fun text(size: TextUnit, color: Color = Rpg.Text, weight: FontWeight = FontWeight.Normal) =
    TextStyle(color = ColorProvider(color), fontSize = size, fontWeight = weight, textAlign = TextAlign.Start)
