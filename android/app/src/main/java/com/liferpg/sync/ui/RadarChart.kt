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
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.TextUnit
import com.liferpg.sync.Category
import com.liferpg.sync.Stat
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.ui.input.pointer.pointerInput
import kotlin.math.PI
import kotlin.math.atan2
import kotlin.math.hypot
import kotlin.math.roundToInt
import kotlin.math.cos
import kotlin.math.sin

/** Grid rings, by score: D, B and A- thresholds, then the A edge. */
private val GRID_LEVELS = listOf(40f, 60f, 70f, CHART_EDGE)
private const val MAX_SCORE = 100f

/** One corner of the radar: its label (with an optional icon above it), score and rank, and the color of its dot and label. */
data class RadarPoint(val label: String, val score: Int?, val grade: String?, val color: Color, val icon: String? = null)

/**
 * Where things sit, as fractions of the chart's radius: the A edge (score 85), the rank badges, the
 * ring between them and the label band, and the labels. Long labels need a wider band.
 */
data class RadarLayout(val edge: Float, val badges: Float, val ring: Float, val labels: Float)

/** Stat codes: short labels, so the score area gets the room */
val CODE_LAYOUT = RadarLayout(edge = 0.43f, badges = 0.69f, ring = 0.80f, labels = 0.89f)

/** Category names: badges pulled in so names like DISCIPLINE fit beside them */
val NAME_LAYOUT = RadarLayout(edge = 0.33f, badges = 0.52f, ring = 0.68f, labels = 0.84f)

/** The nine stats, one corner each, in their own colors. */
@Composable
fun StatRadar(stats: List<Stat>, modifier: Modifier = Modifier, onSelect: ((Stat) -> Unit)? = null) {
    RadarChart(
        stats.map { RadarPoint(it.code, it.score, it.grade, statColor(it.code)) },
        modifier,
        onSelect = onSelect?.let { select -> { i: Int -> select(stats[i]) } },
    )
}

/** The six categories: icon and name at each corner, one color (the names carry identity). */
@Composable
fun CategoryRadar(categories: List<Category>, modifier: Modifier = Modifier, onSelect: ((Category) -> Unit)? = null) {
    RadarChart(
        categories.map { RadarPoint(it.name.uppercase(), it.score, it.grade, Rpg.Text, icon = categoryIcon(it.key)) },
        modifier,
        labelSize = 10.sp,
        layout = NAME_LAYOUT,
        onSelect = onSelect?.let { select -> { i: Int -> select(categories[i]) } },
    )
}

/**
 * Stat card radar: one corner per point, rank badges on an outer ring. The ring's edge is the top of
 * A, so S / SS / SSS scores break out past it.
 */
@Composable
fun RadarChart(
    points: List<RadarPoint>,
    modifier: Modifier = Modifier,
    labelSize: TextUnit = 13.sp,
    layout: RadarLayout = CODE_LAYOUT,
    onSelect: ((Int) -> Unit)? = null,
) {
    val measurer = rememberTextMeasurer()
    val tappable = if (onSelect == null) Modifier else Modifier.pointerInput(points) {
        // Each slice of the circle belongs to the corner it points at
        detectTapGestures { tap ->
            val dx = tap.x - size.width / 2f
            val dy = tap.y - size.height / 2f
            if (hypot(dx, dy) <= minOf(size.width, size.height) / 2f) onSelect(sliceAt(dx, dy, points.size))
        }
    }
    Canvas(modifier.fillMaxWidth().aspectRatio(1f).then(tappable)) {
        val outer = size.minDimension / 2
        val edge = outer * layout.edge           // radius of score 85; a 100 reaches 100/85 of it
        val badgeRadius = outer * layout.badges  // rank badges, on the inner ring
        val labelRadius = outer * layout.labels  // labels, in the outer band
        val n = points.size

        fun angle(i: Int) = (-PI / 2 + 2 * PI * i / n).toFloat()
        fun point(i: Int, radius: Float) = Offset(center.x + radius * cos(angle(i)), center.y + radius * sin(angle(i)))
        fun polygon(radius: (Int) -> Float) = Path().apply {
            for (i in 0 until n) point(i, radius(i)).let { if (i == 0) moveTo(it.x, it.y) else lineTo(it.x, it.y) }
            close()
        }

        // Card rings: an outer band for the names, an inner ring carrying the badges
        drawCircle(Rpg.SurfaceHigh.copy(alpha = 0.35f), radius = outer * 0.98f)
        drawCircle(Rpg.Background, radius = outer * layout.ring)
        drawCircle(Rpg.Outline, radius = outer * 0.98f, style = Stroke(2.dp.toPx()))
        drawCircle(Rpg.Outline, radius = outer * layout.ring, style = Stroke(1.5.dp.toPx()))
        drawCircle(Rpg.Outline.copy(alpha = 0.7f), radius = badgeRadius, style = Stroke(1.dp.toPx()))

        // Polygon grid and spokes
        drawPath(polygon { edge }, Rpg.Surface)
        for (level in GRID_LEVELS) {
            val stroke = if (level == CHART_EDGE) Stroke(2.dp.toPx()) else Stroke(1.dp.toPx())
            drawPath(polygon { edge * level / CHART_EDGE }, Rpg.Outline, style = stroke)
        }
        for (i in 0 until n) drawLine(Rpg.Outline, center, point(i, edge), strokeWidth = 1.dp.toPx())

        // Scores
        fun radiusOf(i: Int) = edge * ((points[i].score ?: 0).toFloat().coerceIn(0f, MAX_SCORE) / CHART_EDGE)
        val shape = polygon(::radiusOf)
        drawPath(shape, Brush.radialGradient(listOf(Rpg.Accent.copy(alpha = 0.55f), Rpg.AccentDeep.copy(alpha = 0.25f)), center, edge))
        drawPath(shape, Rpg.Accent, style = Stroke(2.5.dp.toPx()))
        for (i in 0 until n) {
            val p = point(i, radiusOf(i))
            if ((points[i].score ?: 0) >= CHART_EDGE) drawCircle(rankColor("S").copy(alpha = 0.35f), 9.dp.toPx(), p)  // broke out
            drawCircle(points[i].color, 4.dp.toPx(), p)
        }

        // Labels and rank badges
        for (i in 0 until n) {
            val corner = points[i]
            val label = buildAnnotatedString {
                corner.icon?.let { withStyle(SpanStyle(fontSize = labelSize * 1.8f)) { append(it + "\n") } }
                append(corner.label)
            }
            drawCentered(
                measurer, label, point(i, labelRadius),
                TextStyle(corner.color, labelSize, FontWeight.Black, letterSpacing = if (corner.icon != null) 0.5.sp else 1.sp, textAlign = TextAlign.Center),
            )
            val badge = point(i, badgeRadius)
            val color = rankColor(corner.grade)
            drawCircle(Rpg.Background, 16.dp.toPx(), badge)
            drawCircle(color, 16.dp.toPx(), badge, style = Stroke(2.dp.toPx()))
            drawCentered(measurer, corner.grade ?: "–", badge, TextStyle(color, if ((corner.grade?.length ?: 1) > 2) 11.sp else 14.sp, FontWeight.Black))
        }
    }
}

private fun DrawScope.drawCentered(measurer: TextMeasurer, text: String, at: Offset, style: TextStyle) =
    drawCentered(measurer, AnnotatedString(text), at, style)

private fun DrawScope.drawCentered(measurer: TextMeasurer, text: AnnotatedString, at: Offset, style: TextStyle) {
    val layout = measurer.measure(text, style)
    drawText(layout, topLeft = Offset(at.x - layout.size.width / 2f, at.y - layout.size.height / 2f))
}

/**
 * Which of [count] corners a point belongs to, given its offset from the center (screen coordinates,
 * y down). Corner 0 is at the top and the rest go clockwise, as the chart draws them.
 */
internal fun sliceAt(dx: Float, dy: Float, count: Int): Int {
    val fromTop = (atan2(dy.toDouble(), dx.toDouble()) + PI / 2 + 2 * PI) % (2 * PI)
    return (fromTop / (2 * PI / count)).roundToInt() % count
}
