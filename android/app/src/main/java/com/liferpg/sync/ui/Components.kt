package com.liferpg.sync.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.MutableIntState
import androidx.compose.runtime.MutableState
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp

/** The HUD panel every section sits in: dark surface, thin neon-tinted frame. */
@Composable
fun HudCard(modifier: Modifier = Modifier, content: @Composable ColumnScope.() -> Unit) {
    Column(
        modifier
            .fillMaxWidth()
            .background(Rpg.Surface, RoundedCornerShape(18.dp))
            .border(
                1.dp,
                Brush.linearGradient(listOf(Rpg.Accent.copy(alpha = 0.6f), Rpg.Outline, Rpg.AccentDeep.copy(alpha = 0.5f))),
                RoundedCornerShape(18.dp),
            )
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
        content = content,
    )
}

@Composable
fun SectionTitle(text: String) {
    Text(text.uppercase(), style = MaterialTheme.typography.labelSmall, color = Rpg.Muted)
}

/** Result of a server call as the screens show it. */
sealed interface Load<out T> {
    data object Loading : Load<Nothing>
    data class Ready<T>(val value: T) : Load<T>
    data class Failed(val message: String) : Load<Nothing>
}

/** Runs [fetch] on first show and whenever `reload()` is called. */
class Loader<T>(private val state: MutableState<Load<T>>, private val trigger: MutableIntState) {
    val value get() = state.value
    fun reload() {
        trigger.intValue++
    }
}

@Composable
fun <T> rememberLoader(fetch: suspend () -> T): Loader<T> {
    val state = remember { mutableStateOf<Load<T>>(Load.Loading) }
    val trigger = remember { mutableIntStateOf(0) }
    LaunchedEffect(trigger.intValue) {
        state.value = Load.Loading
        state.value = try {
            Load.Ready(fetch())
        } catch (e: Exception) {
            Load.Failed(e.message ?: "Something went wrong")
        }
    }
    return remember { Loader(state, trigger) }
}

/** Spinner, or the error with a retry button, or [content] once loaded. */
@Composable
fun <T> LoadView(loader: Loader<T>, content: @Composable (T) -> Unit) {
    when (val load = loader.value) {
        is Load.Loading -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            CircularProgressIndicator(color = Rpg.Accent)
        }
        is Load.Failed -> Box(Modifier.fillMaxSize().padding(32.dp), contentAlignment = Alignment.Center) {
            Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Text(load.message, color = Rpg.Muted, textAlign = TextAlign.Center)
                Button(onClick = loader::reload) { Text("Try again") }
            }
        }
        is Load.Ready -> content(load.value)
    }
}

/** A thin progress bar in [color]. */
@Composable
fun Meter(fraction: Float, color: Color, modifier: Modifier = Modifier) {
    Box(modifier.fillMaxWidth().background(Rpg.SurfaceHigh, RoundedCornerShape(50))) {
        Box(
            Modifier
                .fillMaxWidth(fraction.coerceIn(0f, 1f))
                .background(Brush.horizontalGradient(listOf(color.copy(alpha = 0.7f), color)), RoundedCornerShape(50))
                .padding(vertical = 3.dp),
        )
    }
}
