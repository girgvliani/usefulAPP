package com.liferpg.sync.ui

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.size
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawWithContent
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.BlendMode
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.CompositingStrategy
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.clipPath
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import kotlin.math.cos
import kotlin.math.sin

/** Bronze → Legend: the hexagon's colours (top to bottom). Tier 1 is the violet of the badge sheet. */
internal val TIER_COLORS = mapOf(
    1 to listOf(Color(0xFF8B6CF6), Color(0xFF5B3FD6)),
    2 to listOf(Color(0xFFE879F9), Color(0xFF9D27B0)),
    3 to listOf(Color(0xFFFFD166), Color(0xFFE08A00)),
    4 to listOf(Color(0xFFFF6BD5), Color(0xFFFFB86B), Color(0xFF7C5CFF)),
)
internal val TIER_NAMES = mapOf(1 to "Bronze", 2 to "Silver", 3 to "Gold", 4 to "Legend")

internal fun tierColor(tier: Int): Color = TIER_COLORS.getValue(tier.coerceIn(1, 4)).first()

private val LOCKED_RING = Color(0xFF4A4660)
private val LOCKED_FILL = Color(0xFF221F33)

/**
 * A hexagonal badge: a white ring, the tier's gradient with low-poly facets, and the icon as a white
 * silhouette. Locked: grey ring, dark fill, a faint grey icon. Legend badges get a slow turning shine.
 */
@Composable
fun HexBadge(icon: String, tier: Int, earned: Boolean, size: Dp, modifier: Modifier = Modifier) {
    val shine = if (earned && tier >= 4) {
        val turn by rememberInfiniteTransition(label = "shine").animateFloat(
            0f, 360f, infiniteRepeatable(tween(6000, easing = LinearEasing), RepeatMode.Restart), label = "turn",
        )
        turn
    } else null
    Box(modifier.size(size), contentAlignment = Alignment.Center) {
        Canvas(Modifier.fillMaxSize()) { drawBadge(tier, earned, shine) }
        val iconSize = with(LocalDensity.current) { (size * 0.42f).toSp() }
        val tint = if (earned) Color.White else Color(0xFF6E6A86)
        Text(
            icon, fontSize = iconSize,
            modifier = Modifier
                .graphicsLayer(compositingStrategy = CompositingStrategy.Offscreen, alpha = if (earned) 1f else 0.7f)
                .drawWithContent {
                    drawContent()
                    drawRect(tint, blendMode = BlendMode.SrcIn)  // the emoji's shape, in one colour
                },
        )
    }
}

private fun DrawScope.drawBadge(tier: Int, earned: Boolean, shine: Float?) {
    val outer = hexPath(center, size.minDimension / 2f, size.minDimension * 0.09f)
    drawPath(outer, if (earned) Color.White else LOCKED_RING)
    val innerRadius = size.minDimension / 2f * 0.84f
    val inner = hexPath(center, innerRadius, size.minDimension * 0.07f)
    val colors = TIER_COLORS.getValue(tier.coerceIn(1, 4))
    clipPath(inner) {
        if (earned) {
            drawRect(Brush.verticalGradient(colors, startY = center.y - innerRadius, endY = center.y + innerRadius))
            // Low-poly facets: six wedges from the centre, alternately lighter and darker
            for (i in 0 until 6) {
                val a = Math.toRadians(-90.0 + i * 60)
                val b = Math.toRadians(-90.0 + (i + 1) * 60)
                val wedge = Path().apply {
                    moveTo(center.x, center.y)
                    lineTo(center.x + innerRadius * cos(a).toFloat(), center.y + innerRadius * sin(a).toFloat())
                    lineTo(center.x + innerRadius * cos(b).toFloat(), center.y + innerRadius * sin(b).toFloat())
                    close()
                }
                drawPath(wedge, if (i % 2 == 0) Color.White.copy(alpha = 0.10f) else Color.Black.copy(alpha = 0.08f))
            }
            // A soft triangle at the bottom, like the badge sheet
            val tri = Path().apply {
                moveTo(center.x, center.y + innerRadius * 0.15f)
                lineTo(center.x - innerRadius * 0.6f, center.y + innerRadius)
                lineTo(center.x + innerRadius * 0.6f, center.y + innerRadius)
                close()
            }
            drawPath(tri, Color.White.copy(alpha = 0.10f))
            if (shine != null) {
                rotate(shine, center) {
                    drawRect(Brush.sweepGradient(listOf(Color.Transparent, Color.White.copy(alpha = 0.45f), Color.Transparent, Color.Transparent), center))
                }
            }
        } else {
            drawRect(LOCKED_FILL)
        }
    }
}

/** A pointy-top hexagon with rounded corners */
internal fun hexPath(center: Offset, radius: Float, corner: Float): Path {
    val points = (0 until 6).map { i ->
        val angle = Math.toRadians(-90.0 + i * 60)
        Offset(center.x + radius * cos(angle).toFloat(), center.y + radius * sin(angle).toFloat())
    }
    val side = radius  // a regular hexagon's side equals its radius
    val t = (corner / side).coerceIn(0f, 0.5f)
    return Path().apply {
        points.forEachIndexed { i, p ->
            val prev = points[(i + 5) % 6]
            val next = points[(i + 1) % 6]
            val from = p + (prev - p) * t
            val to = p + (next - p) * t
            if (i == 0) moveTo(from.x, from.y) else lineTo(from.x, from.y)
            quadraticTo(p.x, p.y, to.x, to.y)
        }
        close()
    }
}
