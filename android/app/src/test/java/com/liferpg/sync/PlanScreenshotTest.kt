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
import com.liferpg.sync.ui.AppDrawer
import com.liferpg.sync.ui.DEFAULT_PINNED
import com.liferpg.sync.ui.Dest
import com.liferpg.sync.ui.LifeRpgTheme
import com.liferpg.sync.ui.MilestoneCard
import com.liferpg.sync.ui.PlanData
import com.liferpg.sync.ui.PlanOverview
import com.liferpg.sync.ui.QuestList
import com.liferpg.sync.ui.Rpg
import com.liferpg.sync.ui.SkillTree
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode
import java.time.LocalDate

/** The ☰ menu and the Plan screens with sample data, to app/build/screenshots. */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = [36], qualifiers = "w393dp-h1400dp-xxhdpi")
class PlanScreenshotTest {

    @Test
    fun drawer() = capture("nav_drawer") {
        AppDrawer(Dest.Quests, DEFAULT_PINNED, ScreenshotTest.SAMPLE_LEVEL, onOpen = {}, onCustomize = {})
    }

    @Test
    fun plan() = capture("plan") {
        PlanOverview(SAMPLE_PLAN, onOpen = {}, onGoalPreset = {}, onMilestoneIdea = {}, today = TODAY)
    }

    @Test
    fun emptyPlan() = capture("plan_empty") {
        PlanOverview(PlanData(emptyList(), emptyList(), emptyList(), emptyList(), SKILLS), onOpen = {}, onGoalPreset = {}, onMilestoneIdea = {}, today = TODAY)
    }

    @Test
    fun quests() = capture("quests") {
        QuestList(QUESTS, SKILLS, onAdd = {}, onComplete = {}, onEdit = {}, onDelete = {}, today = TODAY)
    }

    @Test
    fun skills() = capture("skills") { SkillTree(SKILLS, onAdd = {}, onOpen = {}) }

    @Test
    fun milestones() = capture("milestones") {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            MILESTONES.forEach { MilestoneCard(it, onComplete = {}, onEdit = {}, onDelete = {}) }
        }
    }

    private fun capture(name: String, content: @Composable () -> Unit) {
        captureRoboImage("build/screenshots/$name.png") {
            LifeRpgTheme { Box(Modifier.fillMaxSize().background(Rpg.Background)) { content() } }
        }
    }

    companion object {
        val TODAY: LocalDate = LocalDate.of(2026, 10, 1)

        val SKILLS = listOf(
            Skill(1, "Health - Exercise", 4, 520),
            Skill(2, "Health - Sleep", 2, 210),
            Skill(3, "Learning - Reading", 3, 400),
            Skill(4, "Career - Work Skills", 6, 830),
            Skill(5, "Career - Kotlin", 2, 160),
            Skill(6, "Social Balance", 1, 45),
        )

        val QUESTS = listOf(
            Quest(1, "Finish the stats API docs", 4, 50, "2026-09-28", false, null),
            Quest(2, "Call grandma", 6, 25, "2026-10-01", false, null),
            Quest(3, "Read 50 pages", 3, 25, "2026-10-04", false, null),
            Quest(4, "Build the Android widget", 5, 100, "2026-10-20", false, null),
            Quest(5, "Book the dentist", 1, 10, "2026-09-25", true, "2026-09-24"),
        )

        val MILESTONES = listOf(
            Milestone("run_5k", "Run a 5K without stopping", 500, false),
            Milestone("ship_app", "Ship Life RPG to the Play Store", 2500, false),
            Milestone("100_pushups", "100 push-ups in a day", 250, true),
        )

        val SAMPLE_PLAN = PlanData(
            goals = ScreenshotTest.SAMPLE_GOALS,
            milestones = MILESTONES,
            quests = QUESTS,
            projects = listOf(
                Project(1, "Client website redesign", 3000, "2026-10-15", false, null),
                Project(2, "Landing page for a cafe", 800, "2026-10-05", false, null),
            ),
            skills = SKILLS,
        )
    }
}
