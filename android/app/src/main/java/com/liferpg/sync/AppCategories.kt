package com.liferpg.sync

import android.content.Context
import android.content.Intent
import android.content.pm.ApplicationInfo
import android.content.pm.PackageManager
import android.os.Build

/** Sorts app minutes into the check-in's screen buckets. Raw per-app minutes are sent too. */
class AppCategories(private val context: Context) {

    fun isGame(packageName: String): Boolean = try {
        appInfo(packageName).category == ApplicationInfo.CATEGORY_GAME
    } catch (e: PackageManager.NameNotFoundException) {
        false
    }

    /** Home-screen apps and system UI: time on them isn't "using the phone" for anything. */
    val notScreenTime: Set<String> by lazy {
        val home = Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_HOME)
        val pm = context.packageManager
        val launchers = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            pm.queryIntentActivities(home, PackageManager.ResolveInfoFlags.of(PackageManager.MATCH_DEFAULT_ONLY.toLong()))
        } else {
            @Suppress("DEPRECATION")
            pm.queryIntentActivities(home, PackageManager.MATCH_DEFAULT_ONLY)
        }
        launchers.map { it.activityInfo.packageName }.toSet() + setOf("com.android.systemui", context.packageName)
    }

    private fun appInfo(packageName: String): ApplicationInfo {
        val pm = context.packageManager
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            pm.getApplicationInfo(packageName, PackageManager.ApplicationInfoFlags.of(0))
        } else {
            @Suppress("DEPRECATION")
            pm.getApplicationInfo(packageName, 0)
        }
    }

    companion object {
        /** Feeds built around short videos. Instagram counts whole, since Reels is most of it. */
        val SHORT_VIDEO = setOf(
            "com.zhiliaoapp.musically", // TikTok
            "com.ss.android.ugc.trill", // TikTok (some regions)
            "com.instagram.android",
        )

        /** Social feeds (not messengers: talking to people isn't the problem). Overlaps SHORT_VIDEO on purpose. */
        val SOCIAL = setOf(
            "com.instagram.android",
            "com.instagram.barcelona", // Threads
            "com.zhiliaoapp.musically",
            "com.ss.android.ugc.trill",
            "com.facebook.katana",
            "com.facebook.lite",
            "com.twitter.android",
            "com.snapchat.android",
            "com.reddit.frontpage",
            "com.pinterest",
        )

        /** Long-form video. YouTube lands here: Android can't tell Shorts from normal videos. */
        val LONG_VIDEO = setOf(
            "com.google.android.youtube",
            "com.netflix.mediaclient",
            "com.amazon.avod.thirdpartyclient",
            "com.disney.disneyplus",
            "com.wbd.stream",
            "tv.twitch.android.app",
        )
    }
}
