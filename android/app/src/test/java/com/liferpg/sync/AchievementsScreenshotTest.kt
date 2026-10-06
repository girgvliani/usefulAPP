package com.liferpg.sync

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.github.takahirom.roborazzi.captureRoboImage
import com.liferpg.sync.ui.AchievementDetail
import com.liferpg.sync.ui.AchievementsContent
import com.liferpg.sync.ui.LifeRpgTheme
import com.liferpg.sync.ui.PoseFrame
import com.liferpg.sync.ui.PoseOverlay
import com.liferpg.sync.ui.RepHud
import com.liferpg.sync.ui.Rpg
import com.liferpg.sync.ui.UnlockContent
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode

/** Achievements from a real server response (test resources/achievements.json), the unlock screen, the rep counter HUD. */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = [36], qualifiers = "w393dp-h2400dp-xxhdpi")
class AchievementsScreenshotTest {
    private val all = parseAchievements(JSONObject(javaClass.getResource("/achievements.json")!!.readText()))

    @Test
    fun parsesTheServerResponse() {
        assertEquals(64, all.total)
        assertEquals(all.items.count { it.earned }, all.earned)
        assertEquals("sleep_week", all.title)
        val goggins = all.stories.first { it.key == "goggins" }
        assertEquals("run_10k", goggins.next)
        assertNotNull(all.item("run_marathon")!!.brief.title)
        assertTrue(all.item("run_10k")!!.progress in 0.5..0.7)  // 6.2 of 10 km
    }

    @Test
    fun stories() = capture("achievements_stories") { AchievementsContent(all) }

    @Test
    fun detail() = capture("achievement_detail") {
        Column(Modifier.padding(16.dp)) { AchievementDetail(all.item("run_marathon")!!, wearing = false) }
    }

    @Test
    fun unlocked() = capture("achievement_unlocked") {
        Column(Modifier.padding(16.dp)) {
            UnlockContent(listOf("run_marathon", "steps_10k", "push_50", "cam_first").map { all.item(it)!!.brief }, animate = false)
        }
    }

    @Test
    fun repHud() = capture("rep_counter_hud") {
        Box(Modifier.fillMaxWidth().aspectRatio(3f / 4f).background(Color(0xFF223344))) {
            val pts = mapOf(11 to Offset(180f, 200f), 13 to Offset(250f, 300f), 15 to Offset(200f, 380f), 12 to Offset(200f, 190f),
                23 to Offset(330f, 230f), 25 to Offset(420f, 260f), 27 to Offset(470f, 330f))
            PoseOverlay(PoseFrame(pts, 480, 640, mirrored = false, tracked = listOf(11, 13, 15)))
            RepHud(17, Phase.Flexed, 88.0, Exercise.Pushups)
        }
    }

    private fun capture(name: String, content: @Composable () -> Unit) {
        captureRoboImage("build/screenshots/$name.png") {
            LifeRpgTheme { Box(Modifier.fillMaxSize().background(Rpg.Background)) { content() } }
        }
    }
}
