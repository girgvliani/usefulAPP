package com.liferpg.sync

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.github.takahirom.roborazzi.captureRoboImage
import com.liferpg.sync.ui.AboutData
import com.liferpg.sync.ui.DayStrip
import com.liferpg.sync.ui.DayValuesContent
import com.liferpg.sync.ui.LifeRpgTheme
import com.liferpg.sync.ui.ProfileSummary
import com.liferpg.sync.ui.Rpg
import com.liferpg.sync.ui.appName
import com.liferpg.sync.ui.parse
import com.liferpg.sync.ui.show
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode
import java.time.LocalDate

/** The About you screen with a sample day, plus how values are read and shown. */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = [36], qualifiers = "w393dp-h1700dp-xxhdpi")
class AboutScreenshotTest {

    @Test
    fun aboutYou() = capture("about_you") {
        val today = LocalDate.of(2026, 10, 6)
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            ProfileSummary(ABOUT, onEdit = {})
            DayStrip(today, today, ABOUT.recent, onPick = {})
            DayValuesContent(CATALOG, DAY, NAMES, showEmpty = false, onToggleEmpty = {}, onEdit = {})
        }
    }

    @Test
    fun emptyValuesShown() = capture("about_you_empty") {
        Column(Modifier.padding(16.dp)) {
            DayValuesContent(CATALOG, DAY, NAMES, showEmpty = true, onToggleEmpty = {}, onEdit = {})
        }
    }

    @Test
    fun parsesWhatYouType() {
        assertEquals(7.5, parse(field("decimal"), "7,5"))
        assertEquals(9214, parse(field("whole"), " 9214 "))
        assertEquals(true, parse(field("yesno"), "true"))
        assertEquals("23:30", parse(field("time"), "23:30"))
        assertThrows(IllegalStateException::class.java) { parse(field("time"), "25:00") }
        assertThrows(IllegalStateException::class.java) { parse(field("whole"), "7.5") }
        assertThrows(IllegalArgumentException::class.java) { parse(field("decimal"), "  ") }
    }

    @Test
    fun showsValuesReadably() {
        assertEquals("9,214", show(field("whole"), 9214))
        assertEquals("7.5 h", show(field("decimal", unit = "h"), 7.5))
        assertEquals("8 h", show(field("decimal", unit = "h"), 8.0))
        assertEquals("Yes", show(field("yesno"), true))
        assertEquals("Instagram", appName("com.instagram.android"))
        assertEquals("YouTube", appName("com.google.android.youtube"))
        assertEquals("Telegram", appName("org.telegram.messenger"))
    }

    private fun capture(name: String, content: @Composable () -> Unit) {
        captureRoboImage("build/screenshots/$name.png") {
            LifeRpgTheme { Box(Modifier.fillMaxSize().background(Rpg.Background)) { content() } }
        }
    }

    companion object {
        private fun field(kind: String, unit: String = "") = LogField("body", "x", "X", unit, kind, "checkin", emptyList())

        val CATALOG = FieldCatalog(
            sections = listOf("sleep" to "Sleep", "work" to "Work", "mind" to "Mind", "screen" to "Phone use", "body" to "Body", "social" to "Social"),
            fields = listOf(
                LogField("sleep", "hours", "Hours slept", "h", "decimal", "both", listOf("MP", "DIS")),
                LogField("sleep", "bed", "Fell asleep", "", "time", "phone", listOf("MP")),
                LogField("sleep", "wake", "Woke up", "", "time", "phone", listOf("MP")),
                LogField("sleep", "late_caffeine", "Caffeine within 6h of bedtime", "", "yesno", "checkin", listOf("MP")),
                LogField("work", "deep", "Deep-focus hours", "h", "decimal", "checkin", listOf("MP")),
                LogField("mind", "learning_min", "Learning", "min", "whole", "checkin", listOf("INT")),
                LogField("screen", "short_video_min", "Reels / Shorts / TikTok", "min", "whole", "phone", listOf("MP", "FOC")),
                LogField("screen", "unlocks", "Unlocks", "", "whole", "phone", listOf("FOC")),
                LogField("body", "steps", "Steps", "", "whole", "phone", listOf("MP", "STA")),
                LogField("body", "weight_kg", "Weight", "kg", "decimal", "both", listOf("H")),
                LogField("body", "resting_hr", "Resting heart rate", "bpm", "whole", "phone", emptyList()),
                LogField("social", "interactions", "Meaningful contacts (30+ min)", "", "whole", "checkin", listOf("SOC")),
            ),
        )

        // The phone guessed 6.2h of sleep; the check-in corrected it to 7.5h
        val DAY = DayLog(
            auto = JSONObject("""{"sleep": {"hours": 6.2, "bed": "00:40", "wake": "06:55"},
                "screen": {"short_video_min": 42, "unlocks": 88, "apps": {"com.instagram.android": 31, "com.google.android.youtube": 54, "org.telegram.messenger": 12}},
                "body": {"steps": 9214, "weight_kg": 109.4, "resting_hr": 61}}"""),
            manual = JSONObject("""{"sleep": {"hours": 7.5, "late_caffeine": false}, "work": {"deep": 3}, "mind": {"learning_min": 45}}"""),
            merged = JSONObject("""{"sleep": {"hours": 7.5}, "body": {"steps": 9214}}"""),
            date = "2026-10-06",
        )

        val NAMES = mapOf("MP" to "Mental Power", "DIS" to "Discipline", "INT" to "Intellect", "FOC" to "Focus", "STA" to "Stamina", "H" to "Health", "SOC" to "Social")

        internal val ABOUT = AboutData(
            catalog = CATALOG,
            profile = Profile("Nick", "GEL", "Asia/Tbilisi", 100, 10000, 8.0, 185.0, 2003, "male"),
            income = Income(6000, 3900),
            sheet = null,
            recent = (0 until 14).filter { it !in setOf(3, 4, 9) }
                .associate { back -> LocalDate.of(2026, 10, 6).minusDays(back.toLong()).toString() to DAY },
        )
    }
}
