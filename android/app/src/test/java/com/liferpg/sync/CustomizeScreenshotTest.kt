package com.liferpg.sync

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import com.github.takahirom.roborazzi.captureRoboImage
import com.liferpg.sync.ui.CustomizeContent
import com.liferpg.sync.ui.LifeRpgTheme
import com.liferpg.sync.ui.Rpg
import org.junit.Assert.assertEquals
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode
import java.time.LocalDateTime

/** The Customize screen at LV 7 (parts off unlocked, the rest locked), and when the daily tips fire. */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = [36], qualifiers = "w393dp-h2400dp-xxhdpi")
class CustomizeScreenshotTest {

    @Test
    fun customize() = capture("customize") { CustomizeContent(CUSTOM, null, onPartOff = { _, _, _ -> }, onReset = {}) }

    @Test
    fun tipsFireAtTheNextHour() {
        val at = LocalDateTime.of(2026, 10, 7, 8, 30)
        assertEquals(30 * 60_000L, TipWorker.delayUntil(9, at))            // later today
        assertEquals((24 * 60 - 30) * 60_000L, TipWorker.delayUntil(8, at))  // already past: tomorrow
    }

    private fun capture(name: String, content: @Composable () -> Unit) {
        captureRoboImage("build/screenshots/$name.png") {
            LifeRpgTheme { Box(Modifier.fillMaxSize().background(Rpg.Background)) { content() } }
        }
    }

    companion object {
        private val LADDER = listOf(
            Unlock(7, "parts_off", "Turn parts off", "Leave out parts of a stat you don't track; it's judged on the rest. Drains still count.", true, true),
            Unlock(15, "weights", "Weight the parts", "Decide how much each part of a stat counts.", false, false),
            Unlock(20, "targets", "Personal targets", "Set your own target for any part and see your progress.", false, false),
            Unlock(25, "categories", "Move stats between categories", "Put any stat in the category it means to you.", false, false),
            Unlock(30, "questions", "Your own check-in questions", "Track anything: water, guitar, cold showers.", false, false),
            Unlock(40, "own_stats", "Your own stats", "Build a stat from any of your data.", false, false),
            Unlock(1000, "genius", "Genius", "The last unlock. Coming later.", false, false),
        )
        val CUSTOM = Customization(
            level = 7, ladder = LADDER, next = LADDER[1],
            off = mapOf("MP" to listOf("Meditation")),
            stats = listOf(
                StatParts("MP", "Mental Power", listOf("Sleep last night" to 25.0, "Deep work" to 25.0, "Physical activity" to 12.0, "Meditation" to 5.0)),
                StatParts("SOC", "Social", listOf("Meaningful contacts / week" to 100.0)),
            ),
        )
    }
}
