package com.liferpg.sync

import android.content.Context
import androidx.core.content.edit

/** Server address, device token and the last sync result, kept in app-private storage. */
class Settings(context: Context) {
    private val prefs = context.getSharedPreferences("settings", Context.MODE_PRIVATE)

    var serverUrl: String
        get() = prefs.getString("server_url", DEFAULT_SERVER).orEmpty()
        set(value) = prefs.edit { putString("server_url", value.trim().trimEnd('/')) }

    var token: String
        get() = prefs.getString("token", "").orEmpty()
        set(value) = prefs.edit { putString("token", value.trim()) }

    /** Name the server gave this device, once the token was checked */
    var deviceName: String
        get() = prefs.getString("device_name", "").orEmpty()
        set(value) = prefs.edit { putString("device_name", value) }

    var lastStatus: String
        get() = prefs.getString("last_status", "Never synced").orEmpty()
        set(value) = prefs.edit { putString("last_status", value) }

    val isConfigured get() = serverUrl.isNotEmpty() && token.isNotEmpty()

    /** Level last celebrated in the app / announced by the background sync; -1 until first seen */
    var lastSeenLevel: Int
        get() = prefs.getInt("last_seen_level", -1)
        set(value) = prefs.edit { putInt("last_seen_level", value) }

    var lastNotifiedLevel: Int
        get() = prefs.getInt("last_notified_level", -1)
        set(value) = prefs.edit { putInt("last_notified_level", value) }

    /** Highest Goggins scale among your unfinished goals, remembered from the last goals load */
    var gogginsLevel: Int
        get() = prefs.getInt("goggins_level", 0)
        set(value) = prefs.edit { putInt("goggins_level", value) }

    /** The goal behind that level, for the nag text */
    var gogginsGoal: String
        get() = prefs.getString("goggins_goal", "").orEmpty()
        set(value) = prefs.edit { putString("goggins_goal", value) }

    /** Set by the notification's "Turn off"; cleared from Settings */
    var gogginsPaused: Boolean
        get() = prefs.getBoolean("goggins_paused", false)
        set(value) = prefs.edit { putBoolean("goggins_paused", value) }

    /** Apps Goggins mode watches */
    var gogginsApps: Set<String>
        get() = prefs.getStringSet("goggins_apps", null) ?: GogginsMode.DEFAULT_APPS
        set(value) = prefs.edit { putStringSet("goggins_apps", value) }

    companion object {
        const val DEFAULT_SERVER = "https://api-production-0c5a.up.railway.app"
    }
}
