package com.liferpg.sync.ui

import android.net.Uri
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Snackbar
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.key
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp
import com.liferpg.sync.Api
import com.liferpg.sync.Settings

private enum class Tab(val label: String, val icon: String) {
    Character("Character", "⚔️"),
    CheckIn("Check-in", "📝"),
    Meals("Meals", "🍽️"),
    Goals("Goals", "🎯"),
    Settings("Settings", "⚙️"),
}

/** [sharedPhoto]: a photo shared into the app (Share → Life RPG Sync), logged as a meal. */
@Composable
fun LifeRpgApp(sharedPhoto: Uri? = null, onSharedPhotoUsed: () -> Unit = {}) {
    val context = LocalContext.current
    val settings = remember { Settings(context) }
    val api = remember { Api(settings) }
    // Opens on Settings until a token has been checked
    var tab by rememberSaveable { mutableIntStateOf(if (settings.deviceName.isNotEmpty()) Tab.Character.ordinal else Tab.Settings.ordinal) }
    // Bumped after connecting, so the other tabs load again with the new server and token
    var connection by remember { mutableIntStateOf(0) }
    LaunchedEffect(sharedPhoto) { if (sharedPhoto != null) tab = Tab.Meals.ordinal }

    val levelState = remember { LevelState(api, settings) }
    LaunchedEffect(connection) { levelState.refresh() }
    val snackbar = remember { SnackbarHostState() }
    LaunchedEffect(levelState.gained) {
        levelState.gained?.let {
            levelState.gained = null
            snackbar.showSnackbar("+$it XP")
        }
    }
    levelState.levelUp?.let { LevelUpDialog(it, onDismiss = { levelState.levelUp = null }) }

    CompositionLocalProvider(LocalLevel provides levelState) {
        Scaffold(
            containerColor = Rpg.Background,
            // The level sits above every screen
            topBar = { levelState.level?.let { Box(Modifier.background(Rpg.Surface).statusBarsPadding()) { LevelHud(it) } } },
            snackbarHost = {
                SnackbarHost(snackbar) { data ->
                    Snackbar(containerColor = Rpg.Good, contentColor = Rpg.Background) {
                        Text("⚡ ${data.visuals.message}", fontWeight = FontWeight.Black, fontSize = 16.sp)
                    }
                }
            },
            bottomBar = {
                NavigationBar(containerColor = Rpg.Surface) {
                    Tab.entries.forEach { item ->
                        NavigationBarItem(
                            selected = tab == item.ordinal,
                            onClick = { tab = item.ordinal },
                            icon = { Text(item.icon, fontSize = 20.sp) },
                            label = { Text(item.label) },
                            colors = NavigationBarItemDefaults.colors(
                                selectedTextColor = Rpg.Accent,
                                unselectedTextColor = Rpg.Muted,
                                indicatorColor = Rpg.SurfaceHigh,
                            ),
                        )
                    }
                }
            },
        ) { padding ->
            Box(Modifier.padding(padding).fillMaxSize()) {
                key(connection) {
                    when (Tab.entries[tab]) {
                        Tab.Character -> CharacterScreen(api)
                        Tab.CheckIn -> CheckInScreen(api)
                        Tab.Meals -> MealsScreen(api, sharedPhoto, onSharedPhotoUsed)
                        Tab.Goals -> GoalsScreen(api)
                        Tab.Settings -> SettingsScreen(settings, api, onConnected = { connection++ })
                    }
                }
            }
        }
    }
}
