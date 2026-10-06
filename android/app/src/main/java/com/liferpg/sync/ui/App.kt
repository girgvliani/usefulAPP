package com.liferpg.sync.ui

import android.net.Uri
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.material3.DrawerValue
import androidx.compose.material3.IconButton
import androidx.compose.material3.ModalNavigationDrawer
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Snackbar
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.rememberDrawerState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.key
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.listSaver
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.liferpg.sync.Api
import com.liferpg.sync.Level
import com.liferpg.sync.Settings
import kotlinx.coroutines.launch

/** [sharedPhoto]: a photo shared into the app (Share → Life RPG Sync), logged as a meal. */
@Composable
fun LifeRpgApp(sharedPhoto: Uri? = null, onSharedPhotoUsed: () -> Unit = {}) {
    val context = LocalContext.current
    val settings = remember { Settings(context) }
    val api = remember { Api(settings) }
    var pinned by remember { mutableStateOf(pinnedDests(settings)) }
    // Screens you went through, newest last; Back walks it. A bottom-bar tap starts it over.
    // Opens on Settings until a token has been checked.
    var stack by rememberSaveable(stateSaver = listSaver(save = { it.map(Dest::name) }, restore = { it.map(Dest::valueOf) })) {
        mutableStateOf(listOf(if (settings.deviceName.isNotEmpty()) Dest.Character else Dest.Settings))
    }
    val current = stack.last()
    fun open(dest: Dest, fromBar: Boolean = false) {
        if (dest == current) return
        stack = if (fromBar) listOf(dest) else stack + dest
    }
    // Bumped after connecting, so the other screens load again with the new server and token
    var connection by remember { mutableIntStateOf(0) }
    LaunchedEffect(sharedPhoto) { if (sharedPhoto != null) open(Dest.Meals) }

    val drawer = rememberDrawerState(DrawerValue.Closed)
    val scope = rememberCoroutineScope()
    var customizing by remember { mutableStateOf(false) }
    BackHandler(enabled = stack.size > 1) { stack = stack.dropLast(1) }
    BackHandler(enabled = drawer.isOpen) { scope.launch { drawer.close() } }  // registered last, so it goes first

    val levelState = remember { LevelState(api, settings) }
    LaunchedEffect(connection) { levelState.refresh() }
    val snackbar = remember { SnackbarHostState() }
    LaunchedEffect(levelState.gained) {
        levelState.gained?.let {
            levelState.gained = null
            snackbar.showSnackbar("+$it XP")
        }
    }
    // New achievements first; a level-up waits until they're closed
    if (levelState.newAchievements.isNotEmpty()) {
        AchievementUnlockDialog(levelState.newAchievements) {
            levelState.newAchievements = emptyList()
            scope.launch { runCatching { api.achievementsSeen() } }
        }
    } else {
        levelState.levelUp?.let { LevelUpDialog(it, onDismiss = { levelState.levelUp = null }) }
    }
    if (customizing) {
        CustomizeBarDialog(
            pinned,
            onSave = { chosen ->
                pinned = chosen
                settings.pinnedTabs = chosen.map { it.name }
                customizing = false
            },
            onDismiss = { customizing = false },
        )
    }

    CompositionLocalProvider(LocalLevel provides levelState, LocalServerUrl provides settings.serverUrl.trimEnd('/')) {
        ModalNavigationDrawer(
            drawerState = drawer,
            drawerContent = {
                AppDrawer(
                    current, pinned, levelState.level,
                    onOpen = { dest ->
                        scope.launch { drawer.close() }
                        open(dest, fromBar = dest in pinned)
                    },
                    onCustomize = {
                        scope.launch { drawer.close() }
                        customizing = true
                    },
                )
            },
        ) {
            Scaffold(
                containerColor = Rpg.Background,
                // ☰ and the level sit above every screen
                topBar = { TopBar(levelState.level, current, onMenu = { scope.launch { drawer.open() } }) },
                snackbarHost = {
                    SnackbarHost(snackbar) { data ->
                        Snackbar(containerColor = Rpg.Good, contentColor = Rpg.Background) {
                            Text("⚡ ${data.visuals.message}", fontWeight = FontWeight.Black, fontSize = 16.sp)
                        }
                    }
                },
                bottomBar = {
                    NavigationBar(containerColor = Rpg.Surface) {
                        pinned.forEach { item ->
                            NavigationBarItem(
                                selected = current == item,
                                onClick = { open(item, fromBar = true) },
                                icon = { Text(item.icon, fontSize = 20.sp) },
                                label = { Text(item.short, maxLines = 1, overflow = TextOverflow.Ellipsis) },
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
                    key(connection, current) {
                        when (current) {
                            Dest.Character -> CharacterScreen(api, onOpen = { open(it) })
                            Dest.CheckIn -> CheckInScreen(api)
                            Dest.Meals -> MealsScreen(api, sharedPhoto, onSharedPhotoUsed)
                            Dest.RepCounter -> RepCounterScreen(api)
                            Dest.Achievements -> AchievementsScreen(api)
                            Dest.Plan -> PlanScreen(api, onOpen = { open(it) })
                            Dest.Goals -> GoalsScreen(api)
                            Dest.Milestones -> MilestonesScreen(api)
                            Dest.Quests -> QuestsScreen(api)
                            Dest.Projects -> ProjectsScreen(api)
                            Dest.Skills -> SkillsScreen(api)
                            Dest.BabySteps -> BabyStepsScreen(api)
                            Dest.Questionnaire -> QuestionnaireScreen(api, onOpen = { open(it) })
                            Dest.Friends -> FriendsScreen(api)
                            Dest.Customize -> CustomizeScreen(api)
                            Dest.About -> AboutScreen(api, onOpen = { open(it) })
                            Dest.Profile -> ProfileScreen(api)
                            Dest.Settings -> SettingsScreen(settings, api, onConnected = { connection++ })
                        }
                    }
                }
            }
        }
    }
}

/** ☰, then the level HUD (or the screen's name before signing in). */
@Composable
private fun TopBar(level: Level?, current: Dest, onMenu: () -> Unit) {
    Row(Modifier.background(Rpg.Surface).statusBarsPadding(), verticalAlignment = Alignment.CenterVertically) {
        IconButton(onClick = onMenu) { Text("☰", fontSize = 24.sp, color = Rpg.Text) }
        Box(Modifier.weight(1f)) {
            if (level != null) {
                LevelHud(level)
            } else {
                Text("${current.icon}  ${current.label.uppercase()}", Modifier.padding(vertical = 18.dp), fontWeight = FontWeight.Black, color = Rpg.Accent)
            }
        }
    }
}
