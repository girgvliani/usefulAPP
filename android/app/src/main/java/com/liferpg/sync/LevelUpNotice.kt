package com.liferpg.sync

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat

/** After each background sync: a notification when you've reached a new level since the last one. */
object LevelUpNotice {
    private const val CHANNEL = "level_up"
    private const val ID = 20

    suspend fun check(context: Context) {
        val settings = Settings(context)
        val level = Api(settings).level()
        notifyAchievements(context, settings, level)
        val last = settings.lastNotifiedLevel
        settings.lastNotifiedLevel = maxOf(last, level.level)
        if (last < 0 || level.level <= last) return  // first look just remembers where you are

        val allowed = Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU ||
            ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED
        if (!allowed) return
        context.getSystemService(NotificationManager::class.java)
            .createNotificationChannel(NotificationChannel(CHANNEL, "Level ups", NotificationManager.IMPORTANCE_DEFAULT))
        val open = PendingIntent.getActivity(context, 0, Intent(context, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE)
        val notification = NotificationCompat.Builder(context, CHANNEL)
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setContentTitle("⬆️ LEVEL UP: LV ${level.level}")
            .setContentText("${level.title} · %,d XP · %,d to LV %d".format(level.xp, level.toNext, level.level + 1))
            .setContentIntent(open)
            .setAutoCancel(true)
            .build()
        NotificationManagerCompat.from(context).notify(ID, notification)
    }

    /** Earned by a sync (a marathon from Samsung Health, say): one notification for the new ones */
    private fun notifyAchievements(context: Context, settings: Settings, level: Level) {
        val fresh = level.newAchievements.filter { it.key !in settings.notifiedAchievements }
        if (fresh.isEmpty()) return
        settings.notifiedAchievements = settings.notifiedAchievements + fresh.map { it.key }
        val allowed = Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU ||
            ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED
        if (!allowed) return
        context.getSystemService(NotificationManager::class.java)
            .createNotificationChannel(NotificationChannel(CHANNEL, "Level ups", NotificationManager.IMPORTANCE_DEFAULT))
        val open = PendingIntent.getActivity(context, 1, Intent(context, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE)
        val best = fresh.maxBy { it.tier }
        val notification = NotificationCompat.Builder(context, CHANNEL)
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setContentTitle("🏆 ${if (fresh.size == 1) "Achievement" else "${fresh.size} achievements"}: ${best.icon} ${best.name}")
            .setContentText("+${fresh.sumOf { it.xp }} XP" + (best.title?.let { " · new title “$it”" } ?: ""))
            .setContentIntent(open)
            .setAutoCancel(true)
            .build()
        NotificationManagerCompat.from(context).notify(ID + 1, notification)
    }
}
