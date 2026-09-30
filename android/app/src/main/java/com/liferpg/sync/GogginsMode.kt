package com.liferpg.sync

import android.content.Context
import android.content.Intent

/**
 * Goggins scale 1-10 on each goal. Your highest level among unfinished goals decides how hard the
 * phone pushes back when you open a distracting app:
 * 1-7 nothing, 8 one warning per visit, 9 every 2 minutes, 10 every 20 seconds until you leave.
 */
object GogginsMode {
    const val MIN_LEVEL = 8

    /** Apps it can watch, with the name used in the warnings */
    val APPS = linkedMapOf(
        "com.google.android.youtube" to "YouTube",
        "com.instagram.android" to "Instagram",
        "com.zhiliaoapp.musically" to "TikTok",
        "com.ss.android.ugc.trill" to "TikTok",
        "com.facebook.katana" to "Facebook",
        "com.facebook.lite" to "Facebook Lite",
        "com.twitter.android" to "X",
        "com.snapchat.android" to "Snapchat",
        "com.reddit.frontpage" to "Reddit",
        "com.google.android.googlequicksearchbox" to "Google",
        "com.android.chrome" to "Chrome",
        "com.sec.android.app.sbrowser" to "Samsung Internet",
    )

    /** Browsers are off by default: they're also for work */
    val DEFAULT_APPS: Set<String> = APPS.keys - setOf("com.android.chrome", "com.sec.android.app.sbrowser")

    /** Seconds between warnings while you stay in a watched app; null = once per visit */
    fun nagEvery(level: Int): Long? = when {
        level >= 10 -> 20
        level == 9 -> 120
        else -> null
    }

    fun describe(level: Int): String = when (level) {
        in 1..3 -> "casual"
        in 4..6 -> "committed"
        7 -> "serious"
        8 -> "warns you once when you open a distracting app"
        9 -> "warns you every 2 minutes in a distracting app"
        else -> "relentless: a warning every 20 seconds until you leave the app"
    }

    /** Remembers the highest level among unfinished goals, then starts or stops the watcher to match. */
    fun update(context: Context, goals: List<Goal>) {
        val settings = Settings(context)
        val top = goals.filter { !it.achieved }.maxByOrNull { it.intensity }
        settings.gogginsLevel = top?.intensity ?: 0
        settings.gogginsGoal = top?.title.orEmpty()
        apply(context)
    }

    fun shouldRun(context: Context): Boolean {
        val settings = Settings(context)
        return settings.gogginsLevel >= MIN_LEVEL && !settings.gogginsPaused && UsageReader(context).hasAccess
    }

    /** Android only lets the watcher start while the app is open (or right after boot); stopping works any time. */
    fun apply(context: Context) {
        val service = Intent(context, GogginsService::class.java)
        if (shouldRun(context)) {
            runCatching { context.startForegroundService(service) }
        } else {
            context.stopService(service)
        }
    }
}
