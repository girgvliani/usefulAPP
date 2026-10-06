package com.liferpg.sync.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.horizontalScroll
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
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.liferpg.sync.AchievementBrief
import com.liferpg.sync.Api
import com.liferpg.sync.Level
import com.liferpg.sync.Settings

/**
 * The player's level, shared by every screen. Screens call [refresh] after anything that can earn XP;
 * the difference in today's XP becomes the "+N XP" pop-up, and a higher level than last seen
 * becomes the LEVEL UP celebration.
 */
class LevelState(private val api: Api, private val settings: Settings) {
    var level by mutableStateOf<Level?>(null)
        private set
    /** "+25 XP" to show, cleared by whoever shows it */
    var gained by mutableStateOf<Int?>(null)
    /** A level reached since the app last celebrated one */
    var levelUp by mutableStateOf<Level?>(null)
    /** Achievements earned since the unlock screen was last shown (the server keeps track) */
    var newAchievements by mutableStateOf<List<AchievementBrief>>(emptyList())

    suspend fun refresh() {
        if (!settings.isConfigured) return
        val fresh = runCatching { api.level() }.getOrNull() ?: return  // older server: no levels yet
        val before = level
        if (before != null && fresh.xp > before.xp) gained = fresh.xp - before.xp
        if (settings.lastSeenLevel in 0 until fresh.level) levelUp = fresh
        if (settings.lastSeenLevel < 0 || fresh.level > settings.lastSeenLevel) settings.lastSeenLevel = fresh.level
        if (fresh.newAchievements.isNotEmpty()) newAchievements = fresh.newAchievements
        level = fresh
    }
}

val LocalLevel = staticCompositionLocalOf<LevelState?> { null }

/** Pinned above every screen: LV badge, title, XP bar, today's XP. */
@Composable
fun LevelHud(level: Level) {
    Row(
        Modifier
            .fillMaxWidth()
            .background(Brush.horizontalGradient(listOf(Rpg.Surface, Rpg.SurfaceHigh)))
            .padding(horizontal = 16.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        LvBadge(level.level, size = 44)
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Row(verticalAlignment = Alignment.Bottom) {
                Text(level.title.uppercase(), Modifier.weight(1f), color = Rpg.Accent, fontWeight = FontWeight.Black, fontSize = 13.sp, letterSpacing = 1.sp)
                Text("%,d / %,d XP".format(level.xp, level.nextLevelXp), color = Rpg.Muted, fontSize = 11.sp)
            }
            Meter(level.progress, Rpg.Accent)
        }
        if (level.todayXp > 0) {
            Text("+${level.todayXp}\ntoday", color = Rpg.Good, fontWeight = FontWeight.Black, fontSize = 12.sp, textAlign = TextAlign.Center, lineHeight = 13.sp)
        }
    }
}

@Composable
fun LvBadge(level: Int, size: Int) {
    Box(
        Modifier.size(size.dp).background(Brush.linearGradient(listOf(Rpg.Accent, Rpg.AccentDeep)), RoundedCornerShape((size / 3.5).dp)),
        contentAlignment = Alignment.Center,
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text("LV", color = Rpg.Background, fontSize = (size / 5).sp, fontWeight = FontWeight.Black, lineHeight = (size / 5).sp)
            Text("$level", color = Rpg.Background, fontSize = (size / 2.4).sp, fontWeight = FontWeight.Black, lineHeight = (size / 2.2).sp)
        }
    }
}

/** The Character screen's headline: an XP ring around the level, today's XP, XP per day, sources. */
@Composable
fun LevelHero(level: Level) {
    HudCard {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(18.dp)) {
            Box(Modifier.size(132.dp), contentAlignment = Alignment.Center) {
                Canvas(Modifier.size(132.dp)) {
                    val stroke = 12.dp.toPx()
                    val inset = stroke / 2
                    val arc = Size(size.width - stroke, size.height - stroke)
                    drawArc(Rpg.SurfaceHigh, 0f, 360f, false, Offset(inset, inset), arc, style = Stroke(stroke))
                    drawArc(
                        Brush.sweepGradient(listOf(Rpg.AccentDeep, Rpg.Accent, Rpg.AccentDeep)), -90f, 360f * level.progress, false,
                        Offset(inset, inset), arc, style = Stroke(stroke, cap = StrokeCap.Round),
                    )
                }
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text("LEVEL", color = Rpg.Muted, fontSize = 11.sp, fontWeight = FontWeight.Black, letterSpacing = 2.sp)
                    Text("${level.level}", fontSize = 46.sp, fontWeight = FontWeight.Black, lineHeight = 48.sp)
                }
            }
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(level.title.uppercase(), color = Rpg.Accent, fontWeight = FontWeight.Black, fontSize = 22.sp, letterSpacing = 1.5.sp)
                Text("%,d XP".format(level.xp), fontWeight = FontWeight.Black, fontSize = 20.sp)
                Text("%,d XP to LV %d".format(level.toNext, level.level + 1), color = Rpg.Muted, fontSize = 13.sp)
                level.nextTitle?.let { Text("Next title: $it", color = Rpg.Muted, fontSize = 12.sp) }
            }
        }

        SectionTitle(if (level.todayXp > 0) "Today · +${level.todayXp} XP" else "Today · nothing earned yet")
        if (level.today.isNotEmpty()) {
            Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                level.today.forEach { (reason, xp) ->
                    Text(
                        "$reason +$xp",
                        Modifier.border(1.dp, Rpg.Outline, RoundedCornerShape(50)).padding(horizontal = 10.dp, vertical = 5.dp),
                        fontSize = 12.sp, fontWeight = FontWeight.Bold,
                    )
                }
            }
        } else {
            Text("Check in, hit your targets and log meals to earn XP.", color = Rpg.Muted, fontSize = 13.sp)
        }

        if (level.history.any { it.second > 0 }) {
            SectionTitle("XP per day · last ${level.history.size} days")
            XpBars(level.history.map { it.second })
        }

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            listOf("activity" to "Activity", "quests" to "Quests", "goals" to "Goals", "achievements" to "Badges").forEach { (key, label) ->
                Column(Modifier.weight(1f).background(Rpg.SurfaceHigh, RoundedCornerShape(12.dp)).padding(10.dp)) {
                    Text(label.uppercase(), color = Rpg.Muted, fontSize = 10.sp, fontWeight = FontWeight.Black, letterSpacing = 1.sp)
                    Text("%,d".format(level.sources[key] ?: 0), fontWeight = FontWeight.Black, fontSize = 16.sp)
                }
            }
        }
    }
}

/** One bar per day, today brightest; a single series, so one color. */
@Composable
private fun XpBars(values: List<Int>) {
    val max = (values.maxOrNull() ?: 0).coerceAtLeast(1)
    Canvas(Modifier.fillMaxWidth().height(56.dp)) {
        val gap = 2.dp.toPx()
        val width = (size.width - gap * (values.size - 1)) / values.size
        values.forEachIndexed { i, v ->
            val h = (size.height * v / max).coerceAtLeast(if (v > 0) 2.dp.toPx() else 0f)
            drawRoundRect(
                if (i == values.lastIndex) Rpg.Accent else Rpg.Accent.copy(alpha = 0.55f),
                topLeft = Offset(i * (width + gap), size.height - h),
                size = Size(width, h),
                cornerRadius = CornerRadius(2.dp.toPx()),
            )
        }
    }
}

/** Shown once for each new level. */
@Composable
fun LevelUpDialog(level: Level, onDismiss: () -> Unit) {
    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = Rpg.Surface,
        title = { Text("⬆️ LEVEL UP!", color = Rpg.Accent, fontWeight = FontWeight.Black, letterSpacing = 2.sp) },
        text = { LevelUpContent(level) },
        confirmButton = { TextButton(onClick = onDismiss) { Text("Stay hard") } },
    )
}

@Composable
internal fun LevelUpContent(level: Level) {
    Column(Modifier.fillMaxWidth(), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(8.dp)) {
        LvBadge(level.level, size = 96)
        Text(level.title.uppercase(), color = Rpg.Accent, fontWeight = FontWeight.Black, fontSize = 20.sp, letterSpacing = 1.5.sp)
        Text("%,d XP · %,d to LV %d".format(level.xp, level.toNext, level.level + 1), color = Rpg.Muted, fontSize = 13.sp)
    }
}
