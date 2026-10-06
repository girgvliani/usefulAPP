package com.liferpg.sync.ui

import android.content.Intent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.liferpg.sync.Api
import com.liferpg.sync.FriendView
import com.liferpg.sync.GlobalBoard
import com.liferpg.sync.GlobalRow
import com.liferpg.sync.FriendsOverview
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.launch
import org.json.JSONObject

/** The four sharing switches: (key, title, what a friend then sees) */
private val SHARE_SWITCHES = listOf(
    Triple("level", "Level, XP and rank", "Your LV, title, XP and XP this week"),
    Triple("stats", "Categories and stats", "TOTAL, the 6 categories and 9 stats, and how TOTAL moved this week"),
    Triple("streaks", "Streaks", "Your current and best streaks"),
    Triple("goals", "Goals and progress", "Goal names and how far along you are, never the numbers (like your weight)"),
    Triple("achievements", "Achievements", "How many badges you've earned and your latest ones"),
)

/** A column of the leaderboard: its label, the value for a row (null = not shared), and how to show it */
internal data class Board(val key: String, val label: String, val value: (FriendView) -> Int?, val show: (Int) -> String)

internal val BOARDS: List<Board> = listOf(
    Board("level", "Level", { it.level?.level }, { "LV $it" }),
    Board("total", "TOTAL", { it.stats?.total }, { "$it" }),
    Board("week_xp", "XP this week", { it.level?.weekXp }, { "+$it XP" }),
    Board("improved", "Most improved", { it.stats?.totalChange }, { if (it > 0) "▲$it" else if (it < 0) "▼${-it}" else "±0" }),
) + listOf("mental" to "Mental", "physical" to "Physical", "practical" to "Practical", "cultural" to "Cultural",
    "discipline" to "Discipline", "social" to "Social").map { (key, name) ->
    Board(key, "${categoryIcon(key)} $name", { v -> v.stats?.categories?.firstOrNull { it.key == key }?.score }, { "$it" })
}

/** Friends you choose, sharing only what you switch on, compared on a leaderboard and on weekly progress. */
@Composable
fun FriendsScreen(api: Api) {
    val data = rememberLoader {
        coroutineScope {
            val overview = async { api.friends() }
            val board = async { api.leaderboard() }
            val everyone = async { runCatching { api.globalBoard() }.getOrNull() }
            Triple(overview.await(), board.await(), everyone.await())
        }
    }
    LoadView(data) { (overview, board, everyone) -> FriendsContent(api, overview, board, everyone, onChanged = data::reload) }
}

@Composable
internal fun FriendsContent(api: Api?, overview: FriendsOverview, board: List<FriendView>, everyone: GlobalBoard?, onChanged: () -> Unit) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var who by remember { mutableStateOf("") }
    var message by remember { mutableStateOf<String?>(null) }
    var boardKey by remember { mutableStateOf("level") }
    var showEveryone by remember { mutableStateOf(true) }  // the leaderboard opens on everyone
    var confirmRemove by remember { mutableStateOf<FriendView?>(null) }
    // Switches flip at once; if saving fails they flip back and say why
    val sharing = remember(overview.sharing) { mutableStateMapOf(*overview.sharing.toList().toTypedArray()) }

    /** Runs a server call; what it returns (or its error) is shown under "Add a friend" */
    fun act(action: suspend () -> String?) {
        scope.launch {
            message = runCatching { action() }.getOrElse { "❌ ${it.message}" }
            onChanged()
        }
    }

    Column(Modifier.verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Text("FRIENDS", style = MaterialTheme.typography.headlineLarge, color = Rpg.Accent)
        Text("Compare with friends you choose. They only see what you switch on below.", color = Rpg.Muted, fontSize = 13.sp)

        SectionTitle("Leaderboard")
        ChoiceChips(listOf(true to "🌍 Everyone", false to "👥 Friends"), showEveryone) { showEveryone = it }
        if (showEveryone && everyone != null) {
            GlobalLeaderboard(everyone)
        } else {
            ChoiceChips(BOARDS.map { it.key to it.label }, boardKey) { boardKey = it }
            Leaderboard(BOARDS.first { it.key == boardKey }, board)
        }

        HudCard {
            SectionTitle("Your friend code")
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(overview.code, Modifier.weight(1f), fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Black, fontSize = 26.sp, color = Rpg.Accent)
                OutlinedButton(onClick = {
                    val share = Intent(Intent.ACTION_SEND).setType("text/plain")
                        .putExtra(Intent.EXTRA_TEXT, "Add me on Life RPG: my friend code is ${overview.code}")
                    context.startActivity(Intent.createChooser(share, "Share your friend code"))
                }) { Text("Share") }
            }
            SectionTitle("Add a friend")
            TextInput(who, { who = it }, "Their friend code or email")
            Button(onClick = {
                val target = who
                act {
                    val status = api?.addFriend(target)
                    who = ""
                    if (status == "accepted") "✓ You're friends now" else "✓ Request sent; it's waiting for them"
                }
            }, enabled = who.isNotBlank(), modifier = Modifier.fillMaxWidth()) { Text("Send request") }
            message?.let { Text(it, color = if (it.startsWith("✓")) Rpg.Good else Rpg.Bad, fontSize = 13.sp) }
        }

        if (overview.incoming.isNotEmpty() || overview.outgoing.isNotEmpty()) {
            HudCard {
                SectionTitle("Requests")
                overview.incoming.forEach { r ->
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Column(Modifier.weight(1f)) {
                            Text(r.name, fontWeight = FontWeight.Bold)
                            Text("wants to be friends · ${r.code}", color = Rpg.Muted, fontSize = 12.sp)
                        }
                        TextButton(onClick = { act { api?.acceptFriend(r.requestId); "✓ You're friends with ${r.name}" } }) { Text("Accept", color = Rpg.Good) }
                        TextButton(onClick = { act { api?.dropRequest(r.requestId); "Declined" } }) { Text("Decline", color = Rpg.Bad) }
                    }
                }
                overview.outgoing.forEach { r ->
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Column(Modifier.weight(1f)) {
                            Text(r.name, fontWeight = FontWeight.Bold)
                            Text("waiting for them · ${r.code}", color = Rpg.Muted, fontSize = 12.sp)
                        }
                        TextButton(onClick = { act { api?.dropRequest(r.requestId); "Request taken back" } }) { Text("Cancel") }
                    }
                }
            }
        }

        HudCard {
            SectionTitle("What your friends see")
            SHARE_SWITCHES.forEach { (key, title, detail) ->
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Column(Modifier.weight(1f)) {
                        Text(title, fontWeight = FontWeight.Bold)
                        Text(detail, color = Rpg.Muted, fontSize = 12.sp)
                    }
                    Switch(
                        checked = sharing[key] == true,
                        onCheckedChange = { on ->
                            sharing[key] = on
                            act {
                                runCatching { api?.updateSharing(JSONObject().put(key, on)) }
                                    .onFailure { sharing[key] = !on; throw it }
                                null
                            }
                        },
                        colors = SwitchDefaults.colors(checkedTrackColor = Rpg.Accent),
                    )
                }
            }
            Text("All off = friends see only your name.", color = Rpg.Muted, fontSize = 12.sp)
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text("Show me on the global leaderboard", fontWeight = FontWeight.Bold)
                    Text("Everyone can see your name, level, title and XP there", color = Rpg.Muted, fontSize = 12.sp)
                }
                Switch(
                    checked = sharing["leaderboard"] == true,
                    onCheckedChange = { on ->
                        sharing["leaderboard"] = on
                        act {
                            runCatching { api?.updateSharing(JSONObject().put("leaderboard", on)) }
                                .onFailure { sharing["leaderboard"] = !on; throw it }
                            null
                        }
                    },
                    colors = SwitchDefaults.colors(checkedTrackColor = Rpg.Accent),
                )
            }
        }


        if (overview.friends.isEmpty()) {
            HudCard { Text("No friends yet. Share your code, or add theirs above.", color = Rpg.Muted) }
        }
        overview.friends.forEach { friend -> FriendCard(friend, onRemove = { confirmRemove = friend }) }
    }

    confirmRemove?.let { friend ->
        ConfirmDialog(
            "Unfriend ${friend.name}?", "You stop seeing each other's shared data. You can add each other again any time.", "Unfriend",
            onConfirm = { confirmRemove = null; act { api?.removeFriend(friend.id); "Unfriended ${friend.name}" } },
            onDismiss = { confirmRemove = null },
        )
    }
}

/** Everyone by XP: the top players, then your own place if you're further down (or hidden) */
@Composable
internal fun GlobalLeaderboard(board: GlobalBoard) {
    HudCard {
        Text("${board.players} ${if (board.players == 1) "player" else "players"} by level", color = Rpg.Muted, fontSize = 12.sp)
        board.top.forEach { GlobalRowView(it) }
        if (board.top.none { it.me }) {
            Text("…", color = Rpg.Muted)
            GlobalRowView(board.you)
            if (board.you.rank == null) Text("You're hidden from everyone else; turn it on below to take your place.", color = Rpg.Muted, fontSize = 12.sp)
        }
    }
}

@Composable
private fun GlobalRowView(row: GlobalRow) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Text(
            when (row.rank) { null -> "–"; 1 -> "🥇"; 2 -> "🥈"; 3 -> "🥉"; else -> "${row.rank}" },
            Modifier.width(40.dp), fontWeight = FontWeight.Black, color = Rpg.Muted,
        )
        Avatar(row.photoUrl, row.name, 34.dp)
        Column(Modifier.weight(1f).padding(start = 10.dp)) {
            Text(if (row.me) "${row.name} (you)" else row.name, fontWeight = if (row.me) FontWeight.Black else FontWeight.Normal,
                color = if (row.me) Rpg.Accent else Rpg.Text)
            Text("${row.title} · ${"%,d".format(row.xp)} XP", color = Rpg.Muted, fontSize = 12.sp)
        }
        Text("LV ${row.level}", fontWeight = FontWeight.Black)
    }
}

/** Ranked by the chosen column; people who don't share it are listed after, without a value. */
@Composable
internal fun Leaderboard(board: Board, rows: List<FriendView>) {
    val ranked = rows.filter { board.value(it) != null }.sortedByDescending { board.value(it) }
    val hidden = rows.filter { board.value(it) == null }
    HudCard {
        ranked.forEachIndexed { i, row ->
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    when (i) { 0 -> "🥇"; 1 -> "🥈"; 2 -> "🥉"; else -> "${i + 1}" },
                    Modifier.width(32.dp), fontWeight = FontWeight.Black, color = Rpg.Muted,
                )
                Text(if (row.me) "${row.name} (you)" else row.name, Modifier.weight(1f),
                    fontWeight = if (row.me) FontWeight.Black else FontWeight.Normal, color = if (row.me) Rpg.Accent else Rpg.Text)
                Text(board.show(board.value(row)!!), fontWeight = FontWeight.Black)
            }
        }
        if (ranked.size <= 1 && hidden.isEmpty()) Text("Add friends to see where you stand.", color = Rpg.Muted, fontSize = 13.sp)
        hidden.forEach { row ->
            Row {
                Text("–", Modifier.width(32.dp), color = Rpg.Muted)
                Text(row.name, Modifier.weight(1f), color = Rpg.Muted)
                Text("not shared", color = Rpg.Muted, fontSize = 12.sp)
            }
        }
    }
}

/** What one friend shares */
@Composable
internal fun FriendCard(friend: FriendView, onRemove: () -> Unit) {
    HudCard {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Avatar(friend.photoUrl, friend.name, 48.dp, ring = Rpg.Outline)
            Column(Modifier.weight(1f).padding(start = 12.dp)) {
                Text(friend.name, fontWeight = FontWeight.Black, fontSize = 18.sp)
                Text(friend.code, color = Rpg.Muted, fontSize = 12.sp, fontFamily = FontFamily.Monospace)
            }
            friend.level?.let { LvBadge(it.level, size = 40) }
        }
        friend.level?.let { Text("${it.title} · ${"%,d".format(it.xp)} XP · +${it.weekXp} this week", color = Rpg.Muted, fontSize = 13.sp) }
        friend.stats?.let { s ->
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("TOTAL ${s.total ?: "–"}", fontWeight = FontWeight.Black)
                Text("  ${s.totalGrade ?: ""}", color = rankColor(s.totalGrade), fontWeight = FontWeight.Black)
                s.totalChange?.let { Text("  ${if (it >= 0) "▲" else "▼"}${kotlin.math.abs(it)} this week", color = if (it >= 0) Rpg.Good else Rpg.Bad, fontSize = 12.sp) }
            }
            s.categories.chunked(3).forEach { row ->
                Row {
                    row.forEach { c ->
                        Text("${categoryIcon(c.key)} ${c.score ?: "–"} ${c.grade ?: ""}", Modifier.weight(1f), fontSize = 13.sp, color = rankColor(c.grade))
                    }
                }
            }
        }
        friend.streaks?.filter { it.current > 0 }?.takeIf { it.isNotEmpty() }?.let { list ->
            Text(list.joinToString("   ") { "${it.emoji} ${it.current}" }, fontSize = 13.sp)
        }
        friend.goals?.forEach { g ->
            Row {
                Text(g.title, Modifier.weight(1f), fontSize = 13.sp)
                Text(if (g.achieved) "🏆" else "${((g.progress ?: 0.0) * 100).toInt()}%", fontSize = 13.sp, fontWeight = FontWeight.Bold)
            }
            Meter((g.progress ?: 0.0).toFloat(), if (g.achieved) Rpg.Good else Rpg.Accent)
        }
        friend.achievements?.let { a ->
            Text("🏆 ${a.earned} of ${a.total} achievements", fontWeight = FontWeight.Bold, fontSize = 13.sp)
            if (a.badges.isNotEmpty()) {
                Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                    a.badges.take(7).forEach { HexBadge(it.icon, it.tier, earned = true, size = 38.dp) }
                }
            }
        }
        if (friend.level == null && friend.stats == null && friend.streaks == null && friend.goals == null && friend.achievements == null) {
            Text("${friend.name} isn't sharing anything yet.", color = Rpg.Muted, fontSize = 13.sp)
        }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
            TextButton(onClick = onRemove) { Text("Unfriend", color = Rpg.Bad) }
        }
    }
}
