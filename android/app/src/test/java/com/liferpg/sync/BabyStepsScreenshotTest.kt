package com.liferpg.sync

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.github.takahirom.roborazzi.captureRoboImage
import com.liferpg.sync.ui.BabyStepsForm
import com.liferpg.sync.ui.BabyStepsList
import com.liferpg.sync.ui.LifeRpgTheme
import com.liferpg.sync.ui.Rpg
import com.liferpg.sync.ui.babyStepsSummary
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode

/** Baby Steps as the server sends them: on step 2 with a credit card and a car loan, renting, no kids. */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = [36], qualifiers = "w393dp-h3600dp-xxhdpi")
class BabyStepsScreenshotTest {

    @Test
    fun parsesTheServerShape() {
        val steps = parseBabySteps(JSONObject(JSON))
        assertEquals(2, steps.current)
        assertEquals(0.4, steps.steps[1].progress!!, 1e-9)
        assertFalse(steps.steps[4].applies)  // step 5: no kids
        assertNull(steps.steps[2].progress)  // step 3: needs monthly expenses
        assertEquals("On step 2 of 7", babyStepsSummary(steps))
        assertEquals("Dave Ramsey's 7 steps: fill in your numbers", babyStepsSummary(null))
    }

    @Test
    fun babySteps() {
        val steps = parseBabySteps(JSONObject(JSON))
        captureRoboImage("build/screenshots/baby_steps.png") {
            LifeRpgTheme {
                Column(Modifier.fillMaxSize().background(Rpg.Background).padding(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
                    BabyStepsList(steps)
                    BabyStepsForm(steps, null) {}
                }
            }
        }
    }

    companion object {
        val JSON = """
        {"currency": "GEL", "current": 2, "score": 0.28,
         "plan": {"starter_target": 1000, "saved": 1000, "monthly_expenses": null, "months": 6,
                  "debts": [{"name": "Credit card", "balance": 600, "original": 1000}, {"name": "Car", "balance": 3000, "original": 5000}],
                  "invest_percent": 0, "kids": false, "college_saved": 0, "college_target": null,
                  "home": "renting", "mortgage_balance": null, "mortgage_original": null, "giving": false},
         "steps": [
          {"step": 1, "title": "Starter emergency fund", "detail": "Save a starter emergency fund.", "progress": 1.0, "done": true, "current": false, "note": "1,000 of 1,000 saved"},
          {"step": 2, "title": "Pay off all debt but the house", "detail": "The debt snowball.", "progress": 0.4, "done": false, "current": true, "note": "Next in the snowball: Credit card (600 left)"},
          {"step": 3, "title": "Full emergency fund", "detail": "Save 3-6 months of expenses.", "progress": null, "done": false, "current": false, "note": "Add your monthly expenses"},
          {"step": 4, "title": "Invest 15% for retirement", "detail": "15% of income.", "progress": 0.0, "done": false, "current": false, "note": "0% of income invested"},
          {"step": 5, "title": "Save for your children's college", "detail": "Save for your kids' education.", "progress": "n/a", "done": true, "current": false, "note": "No children"},
          {"step": 6, "title": "Pay off your home early", "detail": "Extra money at the mortgage.", "progress": "n/a", "done": true, "current": false, "note": "Renting: doesn't apply"},
          {"step": 7, "title": "Build wealth and give", "detail": "Keep building, and give.", "progress": 0.0, "done": false, "current": false, "note": "Tick when you give regularly"}
         ]}
        """
    }
}
