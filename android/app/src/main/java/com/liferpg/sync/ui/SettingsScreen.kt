package com.liferpg.sync.ui

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.provider.Settings as AndroidSettings
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import androidx.health.connect.client.PermissionController
import androidx.lifecycle.compose.LifecycleResumeEffect
import com.liferpg.sync.Api
import com.liferpg.sync.GogginsMode
import com.liferpg.sync.HealthReader
import com.liferpg.sync.Income
import com.liferpg.sync.Profile
import com.liferpg.sync.Settings
import com.liferpg.sync.Sync
import com.liferpg.sync.SyncWorker
import com.liferpg.sync.TipWorker
import com.liferpg.sync.UsageReader
import kotlinx.coroutines.launch
import org.json.JSONObject

@Composable
fun SettingsScreen(settings: Settings, api: Api, onConnected: () -> Unit) {
    Column(Modifier.verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Text("SETTINGS", style = MaterialTheme.typography.headlineLarge, color = Rpg.Accent)
        ConnectionCard(settings, api, onConnected)
        PermissionsCard()
        if (settings.isConfigured) GogginsCard(settings)
        if (settings.isConfigured) TipsCard(settings)
        SyncCard(settings)
        if (settings.isConfigured) Text("Your targets, body and income goal are in ☰ → Profile & targets.", color = Rpg.Muted, fontSize = 13.sp)
    }
}

@Composable
private fun ConnectionCard(settings: Settings, api: Api, onConnected: () -> Unit) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var server by remember { mutableStateOf(settings.serverUrl) }
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var token by remember { mutableStateOf(settings.token) }
    var status by remember {
        mutableStateOf(if (settings.deviceName.isNotEmpty()) "✅ Connected as ${settings.deviceName}" else "Not connected yet")
    }

    /** Checks the saved token, then starts the hourly sync. */
    suspend fun verify(): String = try {
        settings.deviceName = api.device()
        SyncWorker.schedule(context)
        onConnected()
        "✅ Connected as ${settings.deviceName}. Syncing every hour."
    } catch (e: Exception) {
        settings.deviceName = ""
        "❌ ${e.message}"
    }

    fun signIn(newAccount: Boolean) {
        settings.serverUrl = server
        status = if (newAccount) "Creating your account…" else "Signing in…"
        scope.launch {
            status = try {
                val phone = "${Build.MANUFACTURER} ${Build.MODEL}".replaceFirstChar { it.uppercase() }
                settings.token = api.connectWithAccount(email, password, phone, newAccount)
                token = settings.token
                password = ""
                verify()
            } catch (e: Exception) {
                "❌ ${e.message}"
            }
        }
    }

    HudCard {
        SectionTitle("Account")
        OutlinedTextField(server, { server = it }, label = { Text("Server address") }, singleLine = true, modifier = Modifier.fillMaxWidth())
        OutlinedTextField(
            email, { email = it }, label = { Text("Email") }, singleLine = true, modifier = Modifier.fillMaxWidth(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
        )
        OutlinedTextField(
            password, { password = it }, label = { Text("Password (8+ characters)") }, singleLine = true,
            visualTransformation = PasswordVisualTransformation(), modifier = Modifier.fillMaxWidth(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
        )
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = { signIn(newAccount = false) }, Modifier.weight(1f)) { Text("Sign in") }
            OutlinedButton(onClick = { signIn(newAccount = true) }, Modifier.weight(1f)) { Text("Create account") }
        }
        Text("Signing in gives this phone its own token; the password isn't saved.", color = Rpg.Muted, fontSize = 12.sp)
        Text(status, color = if (status.startsWith("✅")) Rpg.Good else Rpg.Muted, fontSize = 13.sp)
    }

    HudCard {
        SectionTitle("Or paste a device token")
        OutlinedTextField(
            token, { token = it }, label = { Text("Device token (lrpg_…)") }, singleLine = true,
            visualTransformation = PasswordVisualTransformation(), modifier = Modifier.fillMaxWidth(),
        )
        OutlinedButton(
            onClick = {
                settings.serverUrl = server
                settings.token = token
                status = "Checking…"
                scope.launch { status = verify() }
            },
            modifier = Modifier.fillMaxWidth(),
        ) { Text("Save token & connect") }
    }
}

@Composable
private fun PermissionsCard() {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val health = remember { HealthReader(context) }
    val usage = remember { UsageReader(context) }
    var healthLine by remember { mutableStateOf("…") }
    var usageAllowed by remember { mutableStateOf(usage.hasAccess) }

    fun refresh() {
        usageAllowed = usage.hasAccess
        scope.launch {
            healthLine = if (!health.isAvailable) {
                "not available"
            } else {
                val granted = health.grantedPermissions().intersect(HealthReader.PERMISSIONS).size
                "${if (granted == HealthReader.PERMISSIONS.size) "✅" else "⚠️"} $granted/${HealthReader.PERMISSIONS.size} allowed"
            }
        }
    }

    val requestHealth = rememberLauncherForActivityResult(PermissionController.createRequestPermissionResultContract()) { refresh() }
    // Usage access is granted in Android's settings; re-check when you come back
    LifecycleResumeEffect(Unit) {
        refresh()
        onPauseOrDispose { }
    }

    HudCard {
        SectionTitle("Phone data")
        PermissionRow("Health Connect (steps, sleep, weight)", healthLine) {
            if (health.isAvailable) requestHealth.launch(HealthReader.PERMISSIONS)
        }
        PermissionRow("Usage access (screen time, sleep estimate)", if (usageAllowed) "✅ allowed" else "❌ not allowed") {
            context.startActivity(Intent(AndroidSettings.ACTION_USAGE_ACCESS_SETTINGS))
        }
        Text(
            "Also set Settings › Apps › Life RPG Sync › Battery to Unrestricted, or Samsung stops the hourly sync.",
            color = Rpg.Muted, fontSize = 12.sp,
        )
    }
}

@Composable
private fun PermissionRow(label: String, state: String, onAllow: () -> Unit) {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        Column(Modifier.weight(1f)) {
            Text(label, fontSize = 14.sp)
            Text(state, color = Rpg.Muted, fontSize = 12.sp)
        }
        OutlinedButton(onClick = onAllow) { Text("Allow") }
    }
}

@Composable
private fun SyncCard(settings: Settings) {
    val context = LocalContext.current
    val levelState = LocalLevel.current
    val scope = rememberCoroutineScope()
    var status by remember { mutableStateOf(settings.lastStatus) }
    var syncing by remember { mutableStateOf(false) }

    HudCard {
        SectionTitle("Sync")
        Button(
            onClick = {
                syncing = true
                status = "Syncing…"
                scope.launch {
                    status = try {
                        Sync.run(context).also { levelState?.refresh() }
                    } catch (e: Exception) {
                        "❌ ${e.message}".also { settings.lastStatus = it }
                    }
                    syncing = false
                }
            },
            enabled = !syncing && settings.isConfigured,
            modifier = Modifier.fillMaxWidth(),
        ) { Text("Sync now") }
        OutlinedButton(
            onClick = {
                syncing = true
                status = "Importing the last ${Sync.HISTORY_DAYS} days…"
                scope.launch {
                    status = try {
                        Sync.run(context, days = Sync.HISTORY_DAYS)
                    } catch (e: Exception) {
                        "❌ ${e.message}".also { settings.lastStatus = it }
                    }
                    syncing = false
                }
            },
            enabled = !syncing && settings.isConfigured,
            modifier = Modifier.fillMaxWidth(),
        ) { Text("Import history (last ${Sync.HISTORY_DAYS} days)") }
        Text(
            "Pulls in past days so your stats don't start from zero. Android keeps about a week of screen time; steps and sleep go back further.",
            color = Rpg.Muted, fontSize = 12.sp,
        )
        Text(status, fontFamily = FontFamily.Monospace, fontSize = 12.sp, color = Rpg.Muted)
    }
}

/** Daily targets, body and income goal: what the shared formulas measure you against. */
@Composable
fun ProfileScreen(api: Api) {
    Column(Modifier.verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Text("PROFILE", style = MaterialTheme.typography.headlineLarge, color = Rpg.Accent)
        ProfileCard(api)
    }
}

@Composable
private fun ProfileCard(api: Api) {
    val profile = rememberLoader { api.profile() to api.income() }
    when (val load = profile.value) {
        is Load.Ready -> ProfileForm(api, load.value.first, load.value.second, onSaved = profile::reload)
        is Load.Failed -> HudCard {
            SectionTitle("Your profile")
            Text(load.message, color = Rpg.Muted, fontSize = 13.sp)
        }
        Load.Loading -> Unit
    }
}

@Composable
private fun ProfileForm(api: Api, profile: Profile, income: Income, onSaved: () -> Unit) {
    val scope = rememberCoroutineScope()
    var name by remember(profile) { mutableStateOf(profile.displayName.orEmpty()) }
    var nickname by remember(profile) { mutableStateOf(profile.nickname.orEmpty()) }
    var publicName by remember(profile) { mutableStateOf(profile.publicName) }
    var currency by remember(profile) { mutableStateOf(profile.currency) }
    var pushups by remember(profile) { mutableStateOf(profile.pushupTarget.toString()) }
    var steps by remember(profile) { mutableStateOf(profile.stepsTarget.toString()) }
    var sleep by remember(profile) { mutableStateOf(profile.sleepTarget.toString()) }
    var height by remember(profile) { mutableStateOf(profile.heightCm?.toInt()?.toString().orEmpty()) }
    var birthYear by remember(profile) { mutableStateOf(profile.birthYear?.toString().orEmpty()) }
    var sex by remember(profile) { mutableStateOf(profile.sex) }
    var incomeGoal by remember(income) { mutableStateOf(if (income.monthlyGoal > 0) income.monthlyGoal.toString() else "") }
    var earned by remember(income) { mutableStateOf(income.earned.toString()) }
    var message by remember(profile) { mutableStateOf<String?>(null) }

    HudCard {
        SectionTitle("Your profile · the formulas are shared, these targets are yours")
        OutlinedTextField(name, { name = it }, label = { Text("Name on your card") }, singleLine = true, modifier = Modifier.fillMaxWidth())
        OutlinedTextField(nickname, { nickname = it.take(40) }, label = { Text("Nickname") }, singleLine = true, modifier = Modifier.fillMaxWidth())
        Text("Friends and the leaderboard see you as", color = Rpg.Muted, fontSize = 12.sp)
        ChoiceChips(listOf("nickname" to "Nickname", "name" to "Your name", "code" to "Just your code"), publicName) { publicName = it }
        OutlinedTextField(currency, { currency = it.uppercase().take(3) }, label = { Text("Currency (GEL, USD, EUR…)") }, singleLine = true, modifier = Modifier.fillMaxWidth())
        NumberInput(pushups, { pushups = it }, "Daily push-up target")
        NumberInput(steps, { steps = it }, "Daily step target")
        NumberInput(sleep, { sleep = it }, "Sleep target (hours a night)")
        SectionTitle("Body · for your calorie target")
        NumberInput(height, { height = it }, "Height (cm)")
        NumberInput(birthYear, { birthYear = it }, "Birth year")
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("Sex", Modifier.weight(1f))
            listOf("male" to "Male", "female" to "Female").forEach { (value, label) ->
                FilterChip(selected = sex == value, onClick = { sex = value }, label = { Text(label) })
            }
        }
        Text("Weight comes from Health Connect or the check-in.", color = Rpg.Muted, fontSize = 12.sp)
        NumberInput(incomeGoal, { incomeGoal = it }, "Monthly income goal ($currency), needed for Wealth")
        NumberInput(earned, { earned = it }, "Earned so far this month ($currency)")
        Text("Timezone: ${profile.timezone}", color = Rpg.Muted, fontSize = 12.sp)
        Button(
            onClick = {
                scope.launch {
                    message = try {
                        val body = JSONObject()
                            .put("currency", currency)
                            .put("pushup_target", pushups.toIntOrNull() ?: error("Push-up target: whole number"))
                            .put("steps_target", steps.toIntOrNull() ?: error("Step target: whole number"))
                            .put("sleep_target", sleep.replace(',', '.').toDoubleOrNull() ?: error("Sleep target: a number"))
                        if (name.isNotBlank()) body.put("display_name", name.trim())
                        if (nickname.isNotBlank()) body.put("nickname", nickname.trim())
                        body.put("public_name", publicName)
                        if (height.isNotBlank()) body.put("height_cm", height.toDoubleOrNull() ?: error("Height: a number in cm"))
                        if (birthYear.isNotBlank()) body.put("birth_year", birthYear.toIntOrNull() ?: error("Birth year: e.g. 2001"))
                        sex?.let { body.put("sex", it) }
                        api.updateProfile(body)
                        val money = JSONObject().put("current_month_earnings", earned.toIntOrNull() ?: error("Earned: whole number"))
                        if (incomeGoal.isNotBlank()) {
                            money.put("monthly_goal", incomeGoal.toIntOrNull()?.takeIf { it > 0 } ?: error("Income goal: a whole number above 0"))
                        }
                        api.updateIncome(money)
                        onSaved()
                        "✅ Saved"
                    } catch (e: Exception) {
                        "❌ ${e.message}"
                    }
                }
            },
            modifier = Modifier.fillMaxWidth(),
        ) { Text("Save profile") }
        message?.let { Text(it, color = if (it.startsWith("✅")) Rpg.Good else Rpg.Bad, fontSize = 13.sp) }
    }
}

@Composable
private fun NumberInput(value: String, onChange: (String) -> Unit, label: String) {
    OutlinedTextField(
        value, onChange, label = { Text(label) }, singleLine = true,
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal), modifier = Modifier.fillMaxWidth(),
    )
}

@Composable
private fun GogginsCard(settings: Settings) {
    val context = LocalContext.current
    val level = settings.gogginsLevel
    var paused by remember { mutableStateOf(settings.gogginsPaused) }
    var apps by remember { mutableStateOf(settings.gogginsApps) }
    var notificationsAllowed by remember { mutableStateOf(canNotify(context)) }
    val askNotifications = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) {
        notificationsAllowed = it
        GogginsMode.apply(context)
    }
    // "Turn off" on a warning pauses it from outside the app; show that when you come back
    LifecycleResumeEffect(Unit) {
        paused = settings.gogginsPaused
        notificationsAllowed = canNotify(context)
        onPauseOrDispose { }
    }

    HudCard {
        SectionTitle("🔥 Goggins mode")
        Text(
            when {
                level >= GogginsMode.MIN_LEVEL -> "Level $level from “${settings.gogginsGoal}”: ${GogginsMode.describe(level)}."
                level > 0 -> "Your highest goal is at $level/10. Raise one to ${GogginsMode.MIN_LEVEL}+ in Goals to switch this on."
                else -> "Give a goal a Goggins scale of ${GogginsMode.MIN_LEVEL}+ in Goals to switch this on."
            },
            fontSize = 14.sp,
        )
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(if (paused) "Paused" else "On", Modifier.weight(1f), fontWeight = FontWeight.Bold)
            Switch(
                checked = !paused && level >= GogginsMode.MIN_LEVEL,
                enabled = level >= GogginsMode.MIN_LEVEL,
                onCheckedChange = { on ->
                    settings.gogginsPaused = !on
                    paused = !on
                    GogginsMode.apply(context)
                },
            )
        }
        if (!notificationsAllowed && Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            OutlinedButton(
                onClick = { askNotifications.launch(Manifest.permission.POST_NOTIFICATIONS) },
                modifier = Modifier.fillMaxWidth(),
            ) { Text("Allow notifications (needed for the warnings)") }
        }
        if (!UsageReader(context).hasAccess) {
            Text("Needs usage access (above) to see which app is open.", color = Rpg.Bad, fontSize = 12.sp)
        }

        SectionTitle("Watch these apps")
        GogginsMode.APPS.entries.groupBy({ it.value }, { it.key }).forEach { (name, packages) ->
            val checked = packages.any { it in apps }
            fun toggle(on: Boolean) {
                apps = if (on) apps + packages else apps - packages.toSet()
                settings.gogginsApps = apps
            }
            Row(Modifier.fillMaxWidth().clickable { toggle(!checked) }, verticalAlignment = Alignment.CenterVertically) {
                Checkbox(checked = checked, onCheckedChange = ::toggle)
                Text(name)
            }
        }
    }
}

/** Before Android 13 notifications need no permission */
private fun canNotify(context: Context) = Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU ||
    ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED

/** Morning and evening tip notifications, at the hours you pick */
@Composable
private fun TipsCard(settings: Settings) {
    val context = LocalContext.current
    var on by remember { mutableStateOf(settings.tipsOn) }
    var morning by remember { mutableStateOf(settings.morningTipHour) }
    var evening by remember { mutableStateOf(settings.eveningTipHour) }
    fun save() {
        settings.tipsOn = on
        settings.morningTipHour = morning
        settings.eveningTipHour = evening
        TipWorker.schedule(context, reset = true)
    }
    HudCard {
        SectionTitle("💡 Daily tips")
        Row(verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text("Morning and evening tips", fontWeight = FontWeight.Bold)
                Text("Morning: the one thing that raises your scores most today. Evening: what's still open before midnight.", color = Rpg.Muted, fontSize = 12.sp)
            }
            Switch(checked = on, onCheckedChange = { on = it; save() })
        }
        if (on) {
            Text("Morning", color = Rpg.Muted, fontSize = 12.sp)
            ChoiceChips((6..11).map { it to "%02d:00".format(it) }, morning) { morning = it; save() }
            Text("Evening", color = Rpg.Muted, fontSize = 12.sp)
            ChoiceChips((17..22).map { it to "%02d:00".format(it) }, evening) { evening = it; save() }
        }
    }
}
