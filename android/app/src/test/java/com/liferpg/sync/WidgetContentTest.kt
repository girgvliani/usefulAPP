package com.liferpg.sync

import androidx.compose.ui.unit.DpSize
import androidx.glance.appwidget.testing.unit.runGlanceAppWidgetUnitTest
import androidx.glance.testing.unit.hasText
import androidx.glance.testing.unit.hasTextEqualTo
import com.liferpg.sync.ui.categoryIcon
import com.liferpg.sync.widget.LifeRpgWidget
import com.liferpg.sync.widget.WidgetContent
import com.liferpg.sync.widget.WidgetData
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

/**
 * What the widget's scrolling lists contain. The screenshots can't show list items (the launcher
 * draws them on the phone), so this checks the widget's content tree instead.
 */
@RunWith(RobolectricTestRunner::class)
class WidgetContentTest {
    private val streakNames = listOf("Check-in", "Push-ups", "Sleep", "Focus", "Steps", "Learning", "Shower", "Meals", "Calories")

    private val data = WidgetData(
        streaks = Streaks(
            "2026-09-30", "worried", "Your 12-day push-ups streak dies at midnight.",
            streakNames.mapIndexed { i, name -> Streak(name.lowercase(), name, "•", "", i + 1, i + 3, i % 2 == 0, i % 2 == 1, false) },
        ),
        sheet = ScreenshotTest.SAMPLE_SHEET,
        level = ScreenshotTest.SAMPLE_LEVEL,
        updated = "18:42",
    )

    @Test
    fun wideListsEveryStreak() = runGlanceAppWidgetUnitTest {
        setAppWidgetSize(LifeRpgWidget.WIDE)
        provideComposable { WidgetContent(data) }
        streakNames.forEach { onNode(hasText(it)).assertExists() }
        onNode(hasText("LV 12")).assertExists()
    }

    @Test
    fun largeListsEveryStreakCategoryAndStat() = runGlanceAppWidgetUnitTest {
        setAppWidgetSize(LifeRpgWidget.LARGE)
        provideComposable { WidgetContent(data) }
        // Tiles read "<emoji> <name>"; category rows "<icon> <name>"; stat rows are just the name
        // ("Focus" is both a streak and a stat). A one-stat category shows only its own row.
        streakNames.forEach { onNode(hasText("• $it")).assertExists() }
        val sheet = ScreenshotTest.SAMPLE_SHEET
        sheet.categories.forEach { category ->
            onNode(hasTextEqualTo("${categoryIcon(category.key)} ${category.name}")).assertExists()
            sheet.statsOf(category).takeIf { it.size > 1 }?.forEach { onNode(hasTextEqualTo(it.name)).assertExists() }
        }
        onNode(hasText("Weakest: ${categoryIcon("practical")} Practical 35")).assertExists()
        onNode(hasText("8,140 XP")).assertExists()
        onNode(hasText("960 XP to LV 13")).assertExists()
    }

    @Test
    fun smallShowsLevelAndTopStreak() = runGlanceAppWidgetUnitTest {
        setAppWidgetSize(DpSize(LifeRpgWidget.SMALL.width, LifeRpgWidget.SMALL.height))
        provideComposable { WidgetContent(data) }
        onNode(hasText("LV 12")).assertExists()
        onNode(hasText("dies at midnight")).assertExists()  // an at-risk streak goes first
    }
}
