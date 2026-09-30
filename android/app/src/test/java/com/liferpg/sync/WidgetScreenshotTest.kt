package com.liferpg.sync

import android.util.TypedValue
import android.view.View
import android.widget.FrameLayout
import androidx.activity.ComponentActivity
import androidx.compose.ui.unit.DpSize
import androidx.glance.appwidget.ExperimentalGlanceRemoteViewsApi
import androidx.glance.appwidget.GlanceRemoteViews
import com.github.takahirom.roborazzi.captureRoboImage
import com.liferpg.sync.widget.LifeRpgWidget
import com.liferpg.sync.widget.WidgetContent
import com.liferpg.sync.widget.WidgetData
import kotlinx.coroutines.runBlocking
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode

/** Renders the home-screen widget in each size and mood to app/build/screenshots. */
@OptIn(ExperimentalGlanceRemoteViewsApi::class)
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = [36], qualifiers = "w393dp-h851dp-xxhdpi")
class WidgetScreenshotTest {

    @Test
    fun largeAngry() = capture("widget_large_angry", LifeRpgWidget.LARGE, data("angry", "Your 12-day push-ups streak dies at midnight."))

    @Test
    fun wideWorried() = capture("widget_wide_worried", LifeRpgWidget.WIDE, data("worried", "Your 12-day push-ups streak dies at midnight."))

    @Test
    fun smallHappy() = capture("widget_small_happy", LifeRpgWidget.SMALL, data("happy", "Every streak is safe today. Stay hard.", allDone = true))

    private fun capture(name: String, size: DpSize, data: WidgetData) {
        val activity = Robolectric.buildActivity(ComponentActivity::class.java).setup().get()
        val result = runBlocking { GlanceRemoteViews().compose(activity, size) { WidgetContent(data) } }
        val parent = FrameLayout(activity)
        val view = result.remoteViews.apply(activity, parent)
        val px = { dp: Float -> TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP, dp, activity.resources.displayMetrics).toInt() }
        val (width, height) = px(size.width.value) to px(size.height.value)
        view.measure(View.MeasureSpec.makeMeasureSpec(width, View.MeasureSpec.EXACTLY), View.MeasureSpec.makeMeasureSpec(height, View.MeasureSpec.EXACTLY))
        view.layout(0, 0, width, height)
        view.captureRoboImage("build/screenshots/$name.png")
    }

    private fun data(mood: String, message: String, allDone: Boolean = false): WidgetData {
        fun streak(key: String, name: String, emoji: String, current: Int, done: Boolean, risk: Boolean = false, broken: Boolean = false) =
            Streak(key, name, emoji, "", current, current + 3, done || allDone, risk && !allDone, broken && !allDone)
        return WidgetData(
            streaks = Streaks(
                "2026-09-30", mood, message,
                listOf(
                    streak("checkin", "Check-in", "📝", 9, done = true),
                    streak("pushups", "Push-ups", "💪", 12, done = false, risk = true),
                    streak("sleep", "Sleep", "😴", 4, done = true),
                    streak("focus", "Focus", "📵", 2, done = false, broken = true),
                    streak("steps", "Steps", "👟", 6, done = false, risk = true),
                    streak("learning", "Learning", "📚", 3, done = true),
                    streak("shower", "Shower", "🚿", 21, done = true),
                    streak("meals", "Meals", "🍽️", 3, done = false, risk = true),
                    streak("calories", "Calories", "🎯", 2, done = true),
                ),
            ),
            sheet = ScreenshotTest.SAMPLE_SHEET,
            level = ScreenshotTest.SAMPLE_LEVEL,
            updated = "18:42",
        )
    }
}
