package com.liferpg.sync.ui

import androidx.compose.material3.LocalContentColor
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

/** Dark game-HUD palette with the neon pink of the stat-card look. */
object Rpg {
    val Background = Color(0xFF0B0A14)
    val Surface = Color(0xFF15132A)
    val SurfaceHigh = Color(0xFF211E3D)
    val Outline = Color(0xFF3A3563)
    val Accent = Color(0xFFE879F9)
    val AccentDeep = Color(0xFF8B5CF6)
    val Text = Color(0xFFF4F1FF)
    val Muted = Color(0xFF9C97B8)
    val Good = Color(0xFF4ADE80)
    val Bad = Color(0xFFF87171)
}

/** One color per stat, the same as the terminal app's character sheet. */
val StatColors = mapOf(
    "MP" to Color(0xFFE879F9),
    "PS" to Color(0xFFF87171),
    "STA" to Color(0xFFFACC15),
    "H" to Color(0xFFA3E635),
    "INT" to Color(0xFF60A5FA),
    "DIS" to Color(0xFF22D3EE),
    "FOC" to Color(0xFFA78BFA),
    "SOC" to Color(0xFF4ADE80),
    "WLT" to Color(0xFFF59E0B),
)

fun statColor(code: String) = StatColors[code] ?: Rpg.Accent

data class Rank(val letter: String, val min: Int, val max: Int)

/** The server's F -> SSS ladder. S and above sit outside the chart's A edge. */
val Ranks = listOf(
    Rank("SSS", 95, 100),
    Rank("SS", 90, 94),
    Rank("S", 85, 89),
    Rank("A+", 80, 84),
    Rank("A", 75, 79),
    Rank("A-", 70, 74),
    Rank("B", 60, 69),
    Rank("C", 50, 59),
    Rank("D", 40, 49),
    Rank("F", 0, 39),
)

/** Score at the chart's outer ring: the top of A. */
const val CHART_EDGE = 85f

fun rankColor(letter: String?): Color = when {
    letter == null -> Rpg.Outline
    letter.startsWith("S") -> Color(0xFFFFD166)
    letter.startsWith("A") -> Rpg.Accent
    letter == "B" -> Color(0xFF60A5FA)
    letter == "C" -> Color(0xFF22D3EE)
    letter == "D" -> Color(0xFFFB923C)
    else -> Rpg.Bad
}

@Composable
fun LifeRpgTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = darkColorScheme(
            primary = Rpg.Accent,
            onPrimary = Rpg.Background,
            secondary = Rpg.AccentDeep,
            background = Rpg.Background,
            onBackground = Rpg.Text,
            surface = Rpg.Surface,
            onSurface = Rpg.Text,
            surfaceVariant = Rpg.SurfaceHigh,
            onSurfaceVariant = Rpg.Muted,
            surfaceContainer = Rpg.Surface,
            outline = Rpg.Outline,
            error = Rpg.Bad,
        ),
        typography = Typography(
            headlineLarge = TextStyle(fontWeight = FontWeight.Black, fontSize = 30.sp, letterSpacing = 1.5.sp),
            titleLarge = TextStyle(fontWeight = FontWeight.Black, fontSize = 20.sp, letterSpacing = 1.sp),
            titleMedium = TextStyle(fontWeight = FontWeight.Bold, fontSize = 16.sp),
            labelSmall = TextStyle(fontWeight = FontWeight.Bold, fontSize = 11.sp, letterSpacing = 1.2.sp),
        ),
    ) {
        CompositionLocalProvider(LocalContentColor provides Rpg.Text, content = content)
    }
}
