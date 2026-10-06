package com.liferpg.sync

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.runtime.Composable
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.github.takahirom.roborazzi.captureRoboImage
import com.liferpg.sync.ui.LifeRpgTheme
import com.liferpg.sync.ui.QuestionnaireResults
import com.liferpg.sync.ui.Rpg
import com.liferpg.sync.ui.SectionContent
import com.liferpg.sync.ui.missing
import com.liferpg.sync.ui.rankLetter
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode

/** A questionnaire step and the results page, with sample data. */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = [36], qualifiers = "w393dp-h1700dp-xxhdpi")
class QuestionnaireScreenshotTest {

    @Test
    fun step() = capture("questionnaire_step") {
        val answers = remember {
            mutableStateMapOf<String, Any>(
                "priorities" to listOf("physical", "mental", "practical", "discipline", "cultural", "social"),
                "main_goal" to "lose_weight",
                "why" to listOf("health"),
                "stress" to 4,
            )
        }
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) { SectionContent(SECTION, answers) }
    }

    @Test
    fun results() = capture("questionnaire_results") {
        QuestionnaireResults(null, ATTEMPT, listOf(ATTEMPT, ATTEMPT.copy(id = 1, createdAt = "2026-09-20T10:00:00")), onRetake = {}, onOpen = {})
    }

    @Test
    fun findsWhatsMissing() {
        val full = mapOf<String, Any>(
            "priorities" to listOf("physical"), "main_goal" to "fitter", "why" to listOf("health"), "stress" to 3, "pushups" to 25,
        )
        assertNull(missing(SECTION, full))
        assertEquals("Answer \"Why does it matter? (up to 2)\"", missing(SECTION, full - "why"))
        assertEquals("\"How many push-ups can you do?\": 0 to 500", missing(SECTION, full + ("pushups" to 900)))
        assertNull(missing(SECTION, full - "pushups"))  // optional
        assertEquals("B", rankLetter(64))
    }

    private fun capture(name: String, content: @Composable () -> Unit) {
        captureRoboImage("build/screenshots/$name.png") {
            LifeRpgTheme { Box(Modifier.fillMaxSize().background(Rpg.Background)) { content() } }
        }
    }

    companion object {
        private fun q(id: String, text: String, kind: String, options: List<Pair<String, String>> = emptyList(), max: Int? = null, optional: Boolean = false) =
            QQuestion(id, text, kind, options, optional, max, if (kind == "number") 0 else null, "", "Calm", "Very stressed")

        val SECTION = QSection(
            "matters", "What matters to you", "Your plan puts these first.",
            listOf(
                q("priorities", "Put these in order: most important to you first", "rank", listOf(
                    "mental" to "Mental", "physical" to "Physical", "practical" to "Practical",
                    "cultural" to "Cultural", "discipline" to "Discipline", "social" to "Social",
                )),
                q("main_goal", "If one thing changed in the next 3 months, what should it be?", "single", listOf(
                    "lose_weight" to "Lose weight", "fitter" to "Get stronger and fitter", "energy" to "More energy and focus",
                )),
                q("why", "Why does it matter? (up to 2)", "multi", listOf(
                    "health" to "Health and a long life", "looks" to "Look and feel better", "career" to "Career and money",
                ), max = 2),
                q("stress", "How stressed are you most days?", "scale"),
                q("pushups", "How many push-ups can you do?", "number", optional = true).copy(max = 500),
            ),
        )

        val ATTEMPT = Attempt(
            id = 2, createdAt = "2026-10-06T14:00:00",
            answers = JSONObject(),
            results = QResults(
                priorities = listOf(
                    Priority("physical", "Physical", 41, false), Priority("mental", "Mental", 61, true),
                    Priority("practical", "Practical", 60, false), Priority("discipline", "Discipline", 69, true),
                    Priority("cultural", "Cultural", 50, true), Priority("social", "Social", 50, false),
                ),
                focus = listOf("physical", "mental", "practical"),
                plan = listOf(
                    PlanStep("exercise", "physical", "Physical", "Two strength sessions a week",
                        "People who can do 40+ push-ups have far fewer heart problems than those who can do under 10 (Yang 2019).",
                        "Two 20-minute sessions: push-ups, squats, rows.", JSONObject("""{"type":"max_pushups","start_value":25,"target_value":35}""")),
                    PlanStep("sleep", "mental", "Mental", "Sleep 7-9 hours",
                        "Two weeks of 6-hour nights cost as much focus as a night without sleep (Van Dongen 2003).",
                        "Set an alarm for bedtime, 8 hours before you need to get up.", JSONObject("""{"type":"sleep","start_value":6.5,"target_value":8}""")),
                    PlanStep("reels", "mental", "Mental", "Cut reels and shorts to under 15 minutes",
                        "Heavy short-video use goes with worse attention and self-control (Nguyen 2025).",
                        "Turn on Goggins mode for your goal at level 8.", null),
                ),
                tips = listOf(
                    "You respond to pressure: set your main goal to Goggins level 8 or higher.",
                    "You're an evening person: put your focus block in the afternoon.",
                ),
            ),
        )
    }
}
