package com.liferpg.sync

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import com.github.takahirom.roborazzi.captureRoboImage
import com.liferpg.sync.ui.BOARDS
import com.liferpg.sync.ui.FriendsContent
import com.liferpg.sync.ui.LifeRpgTheme
import com.liferpg.sync.ui.Rpg
import org.junit.Assert.assertEquals
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode

/** The Friends screen with a few sample friends, and the leaderboard's order. */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = [36], qualifiers = "w393dp-h2200dp-xxhdpi")
class FriendsScreenshotTest {

    @Test
    fun friends() = capture("friends") { FriendsContent(null, OVERVIEW, BOARD, EVERYONE, onChanged = {}) }

    @Test
    fun leaderboardSortsAndHides() {
        val total = BOARDS.first { it.key == "total" }
        val shared = BOARD.filter { total.value(it) != null }.sortedByDescending { total.value(it) }
        assertEquals(listOf("Ben", "Nick"), shared.map { it.name })  // Cat doesn't share stats
        assertEquals("▲6", BOARDS.first { it.key == "improved" }.show(6))
    }

    private fun capture(name: String, content: @Composable () -> Unit) {
        captureRoboImage("build/screenshots/$name.png") {
            LifeRpgTheme { Box(Modifier.fillMaxSize().background(Rpg.Background)) { content() } }
        }
    }

    companion object {
        private fun stats(total: Int, change: Int, vararg scores: Int) = FriendStats(
            total, if (total >= 75) "A" else "B", change,
            listOf("mental", "physical", "practical", "cultural", "discipline", "social").zip(scores.toList()).map { (key, s) ->
                FriendCategory(key, key.replaceFirstChar { it.uppercase() }, s, if (s >= 75) "A" else if (s >= 60) "B" else "C", 2)
            },
            emptyList(),
        )

        val NICK = FriendView(1, "Nick", "K7QF-M2XA", me = true, FriendLevel(7, "Apprentice", 3437, 380), stats(65, 3, 61, 77, 35, 50, 69, 96), null, null)
        val BEN = FriendView(2, "Ben", "B3NX-77QA", me = false, FriendLevel(9, "Apprentice", 4980, 520), stats(78, 6, 82, 74, 70, 80, 85, 75),
            listOf(FriendStreak("Check-in", "📝", 12, 20), FriendStreak("Steps", "👟", 5, 9)),
            listOf(FriendGoal("Lose weight", 0.58, false), FriendGoal("Read 12 books", 1.0, true)))
        val CAT = FriendView(3, "Cat", "CAT2-PQ9Z", me = false, FriendLevel(4, "Novice", 1200, 610), null, null, null)

        val BOARD = listOf(NICK, BEN, CAT)
        // Nick is 63rd of 64: the top rows, then "…" and his own place
        val EVERYONE = GlobalBoard(
            64,
            listOf(
                GlobalRow(7, "Lasha", 21, "Elite", 23_400, false, 1),
                GlobalRow(2, "Ben", 9, "Apprentice", 4980, false, 2),
                GlobalRow(8, "Player QX7M-22LA", 8, "Apprentice", 3700, false, 3),
            ),
            GlobalRow(1, "Nick", 7, "Apprentice", 3437, true, 63),
        )
        val OVERVIEW = FriendsOverview(
            code = "K7QF-M2XA",
            sharing = mapOf("level" to true, "stats" to true, "streaks" to false, "goals" to false, "leaderboard" to true),
            friends = listOf(BEN, CAT),
            incoming = listOf(FriendRequest(9, "Dan", "D4NN-11ZZ")),
            outgoing = emptyList(),
        )
    }
}
