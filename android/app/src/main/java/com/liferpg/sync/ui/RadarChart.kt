package com.liferpg.sync.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.TextMeasurer
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.drawText
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.liferpg.sync.Stat
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.sin

/** Grid rings, by score: D, B and A- thresholds, then the A edge. */
private val GRID_LEVELS = listOf(40f, 60f, 70f, CHART_EDGE)
private const val MAX_SCORE = 100f

/**
 * Stat card radar: one corner per stat, rank badges on an outer ring. The ring's edge is the top of
 * A, so S / SS / SSS scores break out past it.
 */
@Composable
fun StatRadar(stats: List<Stat>, modifier: Modifier = Modifier) {
    val measurer = rememberTextMeasurer()
    Canvas(modifier.fillMaxWidth().aspectRatio(1f)) {
        val outer = size.minDimension / 2
        val edge = outer * 0.43f          // radius of score 85; a 100 reaches 0.51
        val badgeRadius = outer * 0.69f   // rank badges, on the inner ring
        val labelRadius = outer * 0.89f   // stat codes, in the outer band
        val n = stats.size

        fun angle(i: Int) = (-PI / 2 + 2 * PI * i / n).toFloat()
        fun point(i: Int, radius: Float) = Offset(center.x + radius * cos(angle(i)), center.y + radius * sin(angle(i)))
        fun polygon(radius: (Int) -> Float) = Path().apply {
            for (i in 0 until n) point(i, radius(i)).let { if (i == 0) moveTo(it.x, it.y) else lineTo(it.x, it.y) }
            close()
        }

        // Card rings: an outer band for the names, an inner ring carrying the badges
        drawCircle(Rpg.SurfaceHigh.copy(alpha = 0.35f), radius = outer * 0.98f)
        drawCircle(Rpg.Background, radius = outer * 0.80f)
        drawCircle(Rpg.Outline, radius = outer * 0.98f, style = Stroke(2.dp.toPx()))
        drawCircle(Rpg.Outline, radius = outer * 0.80f, style = Stroke(1.5.dp.toPx()))
        drawCircle(Rpg.Outline.copy(alpha = 0.7f), radius = badgeRadius, style = Stroke(1.dp.toPx()))

        // Heptagon grid and spokes
        drawPath(polygon { edge }, Rpg.Surface)
        for (level in GRID_LEVELS) {
            val stroke = if (level == CHART_EDGE) Stroke(2.dp.toPx()) else Stroke(1.dp.toPx())
            drawPath(polygon { edge * level / CHART_EDGE }, Rpg.Outline, style = stroke)
        }
        for (i in 0 until n) drawLine(Rpg.Outline, center, point(i, edge), strokeWidth = 1.dp.toPx())

        // Scores
        fun radiusOf(i: Int) = edge * ((stats[i].score ?: 0).toFloat().coerceIn(0f, MAX_SCORE) / CHART_EDGE)
        val shape = polygon(::radiusOf)
        drawPath(shape, Brush.radialGradient(listOf(Rpg.Accent.copy(alpha = 0.55f), Rpg.AccentDeep.copy(alpha = 0.25f)), center, edge))
        drawPath(shape, Rpg.Accent, style = Stroke(2.5.dp.toPx()))
        for (i in 0 until n) {
            val p = point(i, radiusOf(i))
            if ((stats[i].score ?: 0) >= CHART_EDGE) drawCircle(rankColor("S").copy(alpha = 0.35f), 9.dp.toPx(), p)  // broke out
            drawCircle(statColor(stats[i].code), 4.dp.toPx(), p)
        }

        // Stat codes and rank badges
        for (i in 0 until n) {
            val stat = stats[i]
            drawCentered(measurer, stat.code, point(i, labelRadius), TextStyle(statColor(stat.code), 13.sp, FontWeight.Black, letterSpacing = 1.sp))
            val badge = point(i, badgeRadius)
            val color = rankColor(stat.grade)
            drawCircle(Rpg.Background, 16.dp.toPx(), badge)
            drawCircle(color, 16.dp.toPx(), badge, style = Stroke(2.dp.toPx()))
            drawCentered(measurer, stat.grade ?: "–", badge, TextStyle(color, if ((stat.grade?.length ?: 1) > 2) 11.sp else 14.sp, FontWeight.Black))
        }
    }
}

private fun DrawScope.drawCentered(measurer: TextMeasurer, text: String, at: Offset, style: TextStyle) {
    val layout = measurer.measure(text, style)
    drawText(layout, topLeft = Offset(at.x - layout.size.width / 2f, at.y - layout.size.height / 2f))
}
