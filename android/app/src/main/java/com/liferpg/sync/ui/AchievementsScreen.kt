package com.liferpg.sync.ui

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.Spring
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.animateIntAsState
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.scale
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.liferpg.sync.AchievementBrief
import com.liferpg.sync.AchievementItem
import com.liferpg.sync.Achievements
import com.liferpg.sync.Api
import com.liferpg.sync.StoryInfo
import kotlinx.coroutines.launch
import kotlin.math.cos
import kotlin.math.sin

/** Your achievements: stories (paths of chapters, with what's next) and every badge, with how to get it. */
@Composable
fun AchievementsScreen(api: Api) {
    val data = rememberLoader { api.achievements() }
    val levelState = LocalLevel.current
    val scope = rememberCoroutineScope()
    var open by remember { mutableStateOf<AchievementItem?>(null) }
    var message by remember { mutableStateOf<String?>(null) }
    LoadView(data) { all ->
        AchievementsContent(all, message, onOpen = { open = it })
        open?.let { item ->
            AchievementDialog(
                item, wearing = all.title == item.brief.key,
                onWear = { key ->
                    scope.launch {
                        runCatching { api.wearTitle(key) }
                            .onSuccess { message = if (key == null) "Back to your level title" else "Now wearing “${item.brief.title}”"; data.reload() }
                            .onFailure { message = "❌ ${it.message}" }
                        open = null
                    }
                },
                onDismiss = { open = null },
            )
        }
    }
    LaunchedEffect(Unit) { levelState?.refresh() }  // picks up anything just earned
}

@Composable
internal fun AchievementsContent(all: Achievements, message: String? = null, onOpen: (AchievementItem) -> Unit = {}) {
    var tab by remember { mutableStateOf("stories") }
    Column(Modifier.verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Text("ACHIEVEMENTS", style = MaterialTheme.typography.headlineLarge, color = Rpg.Accent)
        HudCard {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                HexBadge("🏆", tier = 3, earned = all.earned > 0, size = 64.dp)
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text("${all.earned} / ${all.total}", fontWeight = FontWeight.Black, fontSize = 26.sp)
                    Meter(all.earned.toFloat() / all.total.coerceAtLeast(1), Rpg.Gold)
                    Text("+%,d XP from achievements".format(all.xp), color = Rpg.Muted, fontSize = 12.sp)
                }
            }
            val worn = all.items.firstOrNull { it.brief.key == all.title }?.brief?.title
            Text(
                if (worn != null) "Wearing the title “$worn”" else "Earn a badge with a title (like “Jr. Goggins”) and wear it next to your name.",
                color = if (worn != null) Rpg.Gold else Rpg.Muted, fontSize = 13.sp, fontWeight = if (worn != null) FontWeight.Bold else FontWeight.Normal,
            )
            message?.let { Text(it, color = if (it.startsWith("❌")) Rpg.Bad else Rpg.Good, fontSize = 13.sp) }
        }
        ChoiceChips(listOf("stories" to "📖 Stories", "badges" to "🏅 All badges"), tab) { tab = it }
        if (tab == "stories") {
            all.stories.forEach { story -> StoryCard(story, all, onOpen) }
        } else {
            all.stories.forEach { story ->
                SectionTitle("${story.icon} ${story.name} · ${story.done}/${story.chapters.size}")
                story.chapters.mapNotNull { all.item(it) }.chunked(4).forEach { row ->
                    Row(Modifier.fillMaxWidth()) {
                        row.forEach { item -> BadgeTile(item, Modifier.weight(1f), onOpen) }
                        repeat(4 - row.size) { Spacer(Modifier.weight(1f)) }
                    }
                }
            }
        }
    }
}

/** A story: its chapters as a path of badges, and the next one to do */
@Composable
private fun StoryCard(story: StoryInfo, all: Achievements, onOpen: (AchievementItem) -> Unit) {
    val chapters = story.chapters.mapNotNull { all.item(it) }
    HudCard {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(story.icon, fontSize = 26.sp)
            Column(Modifier.weight(1f).padding(start = 10.dp)) {
                Text(story.name.uppercase(), fontWeight = FontWeight.Black, fontSize = 16.sp, letterSpacing = 1.sp)
                Text("${story.done} of ${chapters.size} chapters", color = Rpg.Muted, fontSize = 12.sp)
            }
            if (story.done == chapters.size) Text("COMPLETE", color = Rpg.Gold, fontWeight = FontWeight.Black, fontSize = 11.sp)
        }
        Text(story.blurb, color = Rpg.Muted, fontSize = 13.sp)
        // The path: badges joined by a line, earned ones lit
        Row(Modifier.horizontalScroll(rememberScrollState()), verticalAlignment = Alignment.CenterVertically) {
            chapters.forEachIndexed { i, item ->
                if (i > 0) Box(Modifier.width(14.dp).height(3.dp).background(if (item.earned) Rpg.Accent else Rpg.Outline, RoundedCornerShape(2.dp)))
                HexBadge(item.brief.icon, item.brief.tier, item.earned, 46.dp, Modifier.clickable { onOpen(item) })
            }
        }
        chapters.firstOrNull { it.brief.key == story.next }?.let { next ->
            Column(
                Modifier.fillMaxWidth().background(Rpg.SurfaceHigh, RoundedCornerShape(14.dp)).clickable { onOpen(next) }.padding(12.dp),
                verticalArrangement = Arrangement.spacedBy(5.dp),
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text("NEXT · ${next.brief.name.uppercase()}", Modifier.weight(1f), color = Rpg.Accent, fontWeight = FontWeight.Black, fontSize = 12.sp, letterSpacing = 1.sp)
                    Text("+${next.brief.xp} XP", color = Rpg.Good, fontWeight = FontWeight.Black, fontSize = 12.sp)
                }
                Text(next.how, fontSize = 13.sp)
                if (next.target > 1) {
                    Meter(next.progress.toFloat(), tierColor(next.brief.tier))
                    Text(progressText(next), color = Rpg.Muted, fontSize = 12.sp)
                }
                next.brief.title?.let { Text("Unlocks the title “$it”", color = Rpg.Gold, fontSize = 12.sp, fontWeight = FontWeight.Bold) }
            }
        }
    }
}

@Composable
private fun BadgeTile(item: AchievementItem, modifier: Modifier, onOpen: (AchievementItem) -> Unit) {
    Column(modifier.clickable { onOpen(item) }.padding(vertical = 6.dp), horizontalAlignment = Alignment.CenterHorizontally) {
        HexBadge(item.brief.icon, item.brief.tier, item.earned, 62.dp)
        Text(
            item.brief.name, fontSize = 11.sp, textAlign = TextAlign.Center, maxLines = 2, overflow = TextOverflow.Ellipsis,
            color = if (item.earned) Rpg.Text else Rpg.Muted, fontWeight = if (item.earned) FontWeight.Bold else FontWeight.Normal,
            modifier = Modifier.padding(horizontal = 2.dp),
        )
        if (!item.earned && item.progress > 0) Meter(item.progress.toFloat(), tierColor(item.brief.tier), Modifier.width(48.dp).padding(top = 3.dp))
    }
}

internal fun progressText(item: AchievementItem): String {
    fun show(v: Double) = if (v % 1.0 == 0.0) "%,d".format(v.toLong()) else "%,.1f".format(v)
    return "${show(minOf(item.value, item.target))} / ${show(item.target)} ${item.unit}".trim()
}

/** One badge: what it takes, how far along you are, its XP and title */
@Composable
internal fun AchievementDialog(item: AchievementItem, wearing: Boolean, onWear: (String?) -> Unit, onDismiss: () -> Unit) {
    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = Rpg.Surface,
        confirmButton = { TextButton(onClick = onDismiss) { Text("Close") } },
        text = { AchievementDetail(item, wearing, onWear) },
    )
}

@Composable
internal fun AchievementDetail(item: AchievementItem, wearing: Boolean, onWear: (String?) -> Unit = {}) {
    Column(Modifier.fillMaxWidth(), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(8.dp)) {
        HexBadge(item.brief.icon, item.brief.tier, item.earned, 116.dp)
        Text(item.brief.name.uppercase(), fontWeight = FontWeight.Black, fontSize = 20.sp, letterSpacing = 1.sp, textAlign = TextAlign.Center)
        Text(
            "${TIER_NAMES[item.brief.tier]} · +${item.brief.xp} XP",
            color = tierColor(item.brief.tier), fontWeight = FontWeight.Black, fontSize = 13.sp,
        )
        Text(item.how, textAlign = TextAlign.Center, fontSize = 14.sp)
        if (item.earned) {
            Text("✅ Earned ${item.earnedAt?.take(10).orEmpty()}", color = Rpg.Good, fontWeight = FontWeight.Bold, fontSize = 13.sp)
        } else if (item.target > 1) {
            Meter(item.progress.toFloat(), tierColor(item.brief.tier), Modifier.fillMaxWidth())
            Text(progressText(item), color = Rpg.Muted, fontSize = 12.sp)
        } else {
            Text("Not earned yet", color = Rpg.Muted, fontSize = 13.sp)
        }
        item.brief.title?.let { title ->
            Text("Title: “$title”", color = Rpg.Gold, fontWeight = FontWeight.Black, fontSize = 15.sp)
            when {
                !item.earned -> Text("Earn it to wear this title next to your name", color = Rpg.Muted, fontSize = 12.sp)
                wearing -> OutlinedButton(onClick = { onWear(null) }) { Text("Take it off") }
                else -> Button(onClick = { onWear(item.brief.key) }) { Text("Wear this title") }
            }
        }
    }
}

/** Shown when something new is earned: the best badge pops in over turning light rays, the rest below. */
@Composable
fun AchievementUnlockDialog(earned: List<AchievementBrief>, onDismiss: () -> Unit) {
    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = Rpg.Surface,
        confirmButton = { Button(onClick = onDismiss) { Text("Stay hard 💪") } },
        text = { UnlockContent(earned) },
    )
}

@Composable
internal fun UnlockContent(earned: List<AchievementBrief>, animate: Boolean = true) {
    val best = earned.maxWith(compareBy<AchievementBrief> { it.tier }.thenBy { it.xp })
    val pop = remember { Animatable(if (animate) 0.2f else 1f) }
    LaunchedEffect(Unit) { pop.animateTo(1f, spring(dampingRatio = Spring.DampingRatioMediumBouncy, stiffness = Spring.StiffnessLow)) }
    val turn by rememberInfiniteTransition(label = "rays").animateFloat(
        0f, if (animate) 360f else 0f, infiniteRepeatable(tween(9000, easing = LinearEasing), RepeatMode.Restart), label = "turn",
    )
    val totalXp = earned.sumOf { it.xp }
    var shownXp by remember { mutableStateOf(if (animate) 0 else totalXp) }
    val countUp by animateIntAsState(shownXp, tween(1200), label = "xp")
    LaunchedEffect(Unit) { shownXp = totalXp }
    val color = tierColor(best.tier)
    Column(Modifier.fillMaxWidth(), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(
            if (earned.size == 1) "🏆 ACHIEVEMENT UNLOCKED" else "🏆 ${earned.size} ACHIEVEMENTS UNLOCKED",
            color = Rpg.Gold, fontWeight = FontWeight.Black, fontSize = 15.sp, letterSpacing = 1.5.sp, textAlign = TextAlign.Center,
        )
        Box(Modifier.size(190.dp), contentAlignment = Alignment.Center) {
            Canvas(Modifier.size(190.dp)) {
                rotate(turn) {
                    val r = size.minDimension / 2
                    for (i in 0 until 12) {
                        val a = Math.toRadians(i * 30.0)
                        val b = Math.toRadians(i * 30.0 + 12)
                        val ray = androidx.compose.ui.graphics.Path().apply {
                            moveTo(center.x, center.y)
                            lineTo(center.x + r * cos(a).toFloat(), center.y + r * sin(a).toFloat())
                            lineTo(center.x + r * cos(b).toFloat(), center.y + r * sin(b).toFloat())
                            close()
                        }
                        drawPath(ray, Brush.radialGradient(listOf(color.copy(alpha = 0.55f), Color.Transparent), center, r))
                    }
                }
                drawCircle(Brush.radialGradient(listOf(color.copy(alpha = 0.45f), Color.Transparent), center, size.minDimension / 2.6f), center = Offset(center.x, center.y))
            }
            HexBadge(best.icon, best.tier, earned = true, size = 120.dp, modifier = Modifier.scale(pop.value))
        }
        Text(best.name.uppercase(), fontWeight = FontWeight.Black, fontSize = 22.sp, letterSpacing = 1.sp, textAlign = TextAlign.Center)
        Text("${TIER_NAMES[best.tier]} · +${best.xp} XP", color = color, fontWeight = FontWeight.Black, fontSize = 13.sp)
        best.title?.let { Text("New title: “$it” (wear it from Achievements)", color = Rpg.Gold, fontSize = 13.sp, fontWeight = FontWeight.Bold, textAlign = TextAlign.Center) }
        val rest = earned - best
        if (rest.isNotEmpty()) {
            rest.chunked(5).forEach { row ->
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    row.forEach { HexBadge(it.icon, it.tier, earned = true, size = 44.dp) }
                }
            }
            Text(rest.take(6).joinToString(" · ") { it.name } + if (rest.size > 6) " · …" else "", color = Rpg.Muted, fontSize = 12.sp, textAlign = TextAlign.Center)
        }
        Text(
            "+%,d XP".format(countUp),
            Modifier.border(1.dp, Rpg.Good, RoundedCornerShape(50)).padding(horizontal = 14.dp, vertical = 4.dp),
            color = Rpg.Good, fontWeight = FontWeight.Black, fontSize = 18.sp,
        )
    }
}
