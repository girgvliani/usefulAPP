package com.liferpg.sync

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.github.takahirom.roborazzi.captureRoboImage
import com.liferpg.sync.ui.CharacterSheetView
import com.liferpg.sync.ui.GoalCard
import com.liferpg.sync.ui.LevelHero
import com.liferpg.sync.ui.LevelHud
import com.liferpg.sync.ui.LevelUpContent
import com.liferpg.sync.ui.LifeRpgTheme
import com.liferpg.sync.ui.MealCard
import com.liferpg.sync.ui.Totals
import com.liferpg.sync.ui.Rpg
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode

/** Renders the screens with sample data to app/build/screenshots, to check the design without a phone. */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = [36], qualifiers = "w393dp-h1600dp-xxhdpi")  // Galaxy S23 width, tall enough for the whole scroll
class ScreenshotTest {

    @Test
    fun characterSheet() = capture("character") { CharacterSheetView(SAMPLE_SHEET, "Nick", SAMPLE_LEVEL, onRefresh = {}) }

    @Test
    fun goals() = capture("goals") {
        val api = Api(Settings(LocalContext.current))
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            SAMPLE_GOALS.forEach { GoalCard(api, it, onChanged = {}) }
        }
    }

    @Test
    fun levelHud() = capture("level_hud") {
        Column(verticalArrangement = Arrangement.spacedBy(24.dp)) {
            LevelHud(SAMPLE_LEVEL)
            Column(Modifier.padding(16.dp)) { LevelHero(SAMPLE_LEVEL) }
        }
    }

    @Test
    fun levelUp() = capture("level_up") {
        // The dialog opens in its own window, which screenshots can't capture; its contents render the same
        Column(Modifier.padding(32.dp), horizontalAlignment = androidx.compose.ui.Alignment.CenterHorizontally) {
            androidx.compose.material3.Text("⬆️ LEVEL UP!", color = Rpg.Accent)
            LevelUpContent(SAMPLE_LEVEL)
        }
    }

    @Test
    fun meals() = capture("meals") {
        val api = Api(Settings(LocalContext.current))
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Totals(SAMPLE_DAY)
            SAMPLE_DAY.meals.forEach { MealCard(api, it, onChanged = {}) }
        }
    }

    private fun capture(name: String, content: @Composable () -> Unit) {
        captureRoboImage("build/screenshots/$name.png") {
            LifeRpgTheme { Box(Modifier.fillMaxSize().background(Rpg.Background)) { content() } }
        }
    }

    companion object {
        private fun stat(code: String, name: String, score: Int?, grade: String?, best: String?) = Stat(
            code, name, score, grade, confidence = if (score == null) 0 else 100, ceiling = null, ceilingNote = "",
            bestMove = best, bestMovePoints = best?.let { 12 },
            components = listOf(StatComponent("Sleep last night", 25.0, 0.75, "6.5h"), StatComponent("Deep work", 25.0, 0.9, "3h focused")),
            penalties = listOf(StatPenalty("Reels / Shorts / TikTok", 8.0, "60 min")),
        )

        // One stat in each band: S-tier ones break past the A edge
        val SAMPLE_SHEET = CharacterSheet(
            date = "2026-09-30", overall = 71, overallGrade = "A-",
            stats = listOf(
                stat("MP", "Mental Power", 78, "A", "Reels / Shorts / TikTok"),
                stat("PS", "Physical Strength", 88, "S", "Max push-up test"),
                stat("STA", "Stamina", 62, "B", "Steps (7-day avg)"),
                stat("H", "Health", 81, "A+", "Protein"),
                stat("INT", "Intellect", 50, "C", "Learning (28 days)"),
                stat("DIS", "Discipline", 69, "B", "Showered"),
                stat("FOC", "Focus", 44, "D", "Reels / Shorts / TikTok"),
                stat("SOC", "Social", 96, "SSS", null),
                stat("WLT", "Wealth", 35, "F", "Monthly income goal"),
            ),
        )

        private fun meal(id: Int, at: String, type: String, name: String, kcal: Double, protein: Double, source: String, items: List<MealItem>) =
            Meal(id, "2026-09-30T$at:00+04:00", type, name, items, kcal, protein, kcal * 0.1, kcal * 0.04, source, 0.7)

        val SAMPLE_DAY = DayMeals(
            "2026-09-30",
            listOf(
                meal(1, "08:40", "breakfast", "Eggs and toast", 520.0, 32.0, "photo",
                    listOf(MealItem("Fried eggs (3)", 150.0, 270.0, 19.0, 1.0, 21.0), MealItem("Toast", 60.0, 250.0, 13.0, 45.0, 3.0))),
                meal(2, "13:15", "lunch", "Khinkali and salad", 1020.0, 48.0, "photo",
                    listOf(MealItem("Khinkali (5)", 350.0, 900.0, 45.0, 90.0, 38.0), MealItem("Tomato-cucumber salad", 200.0, 120.0, 3.0, 10.0, 8.0))),
                meal(3, "16:30", "snack", "Protein shake", 240.0, 48.0, "manual", listOf(MealItem("Whey x2", null, 240.0, 48.0, 6.0, 3.0))),
            ),
            kcal = 1780.0, protein = 128.0,
            targets = NutritionTargets(calories = 2520, protein = 184, adjustment = -500, missing = emptyList()),
        )

        val SAMPLE_LEVEL = Level(
            level = 12, xp = 8_140, levelStartXp = 7_800, nextLevelXp = 9_100, todayXp = 85,
            title = "Adept", nextTitle = "Veteran at LV 15",
            today = listOf("Slept 7-9h" to 15, "Deep work" to 30, "Meals logged" to 10, "Reels under 30 min" to 10, "Shower" to 5, "Step target" to 15),
            sources = mapOf("activity" to 6_890, "quests" to 750, "goals" to 500),
            history = (0 until 30).map { "2026-09-%02d".format(it + 1) to listOf(120, 95, 150, 60, 0, 140, 110, 135)[it % 8] },
        )

        val SAMPLE_GOALS = listOf(
            Goal(1, "weight", "Weight: 112 → 107 kg", "kg", 112.0, 107.0, 109.5, 0.5, "decrease", false, "2026-12-31", intensity = 10),
            Goal(2, "max_pushups", "Max push-ups: 32 → 50 reps", "reps", 32.0, 50.0, 50.0, 1.0, "increase", true, null, intensity = 5),
            Goal(3, "custom", "Read 20 books", "books", 0.0, 20.0, 7.0, 0.35, "increase", false, null, intensity = 8),
        )
    }
}
