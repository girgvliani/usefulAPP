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
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import androidx.work.workDataOf
import java.time.Duration
import java.time.LocalDateTime
import java.util.concurrent.TimeUnit

/**
 * The daily tips: a morning notification with the one thing that would raise your scores most
 * today, and an evening one with what's still open before midnight (a streak about to end, steps
 * to go, the check-in).
 */
class TipWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        val settings = Settings(applicationContext)
        if (!settings.isConfigured || !settings.tipsOn) return Result.success()
        val whenOfDay = inputData.getString(KEY_WHEN) ?: "morning"
        return try {
            show(applicationContext, Api(settings).tip(whenOfDay))
            Result.success()
        } catch (e: Exception) {
            Result.retry()  // offline at that moment: try again shortly
        }
    }

    companion object {
        private const val KEY_WHEN = "when"
        private const val CHANNEL = "daily_tips"

        /** (Re)schedules both tips at the hours in Settings; [reset] moves them after the hours change. */
        fun schedule(context: Context, reset: Boolean = false) {
            val settings = Settings(context)
            val work = WorkManager.getInstance(context)
            for ((whenOfDay, hour) in listOf("morning" to settings.morningTipHour, "evening" to settings.eveningTipHour)) {
                val name = "tip-$whenOfDay"
                if (!settings.tipsOn) {
                    work.cancelUniqueWork(name)
                    continue
                }
                val request = PeriodicWorkRequestBuilder<TipWorker>(1, TimeUnit.DAYS)
                    .setInitialDelay(delayUntil(hour), TimeUnit.MILLISECONDS)
                    .setInputData(workDataOf(KEY_WHEN to whenOfDay))
                    .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
                    .build()
                work.enqueueUniquePeriodicWork(name, if (reset) ExistingPeriodicWorkPolicy.UPDATE else ExistingPeriodicWorkPolicy.KEEP, request)
            }
        }

        /** Milliseconds until the next [hour]:00 */
        internal fun delayUntil(hour: Int, now: LocalDateTime = LocalDateTime.now()): Long {
            var next = now.toLocalDate().atTime(hour, 0)
            if (!next.isAfter(now)) next = next.plusDays(1)
            return Duration.between(now, next).toMillis()
        }

        fun show(context: Context, tip: Tip) {
            val allowed = Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU ||
                ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED
            if (!allowed) return
            context.getSystemService(NotificationManager::class.java)
                .createNotificationChannel(NotificationChannel(CHANNEL, "Daily tips", NotificationManager.IMPORTANCE_DEFAULT))
            val open = PendingIntent.getActivity(context, 0, Intent(context, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE)
            val notification = NotificationCompat.Builder(context, CHANNEL)
                .setSmallIcon(R.drawable.ic_launcher_foreground)
                .setContentTitle(tip.title)
                .setContentText(tip.detail)
                .setStyle(NotificationCompat.BigTextStyle().bigText(tip.detail))
                .setContentIntent(open)
                .setAutoCancel(true)
                .build()
            NotificationManagerCompat.from(context).notify(if (tip.whenOfDay == "evening") 31 else 30, notification)
        }
    }
}
