package com.liferpg.sync

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.content.pm.PackageManager
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.app.ServiceCompat
import androidx.core.content.ContextCompat
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import java.time.Duration
import java.time.Instant

/**
 * Watches which app is open (every few seconds, from usage access) and warns you off the apps
 * Goggins mode watches, as often as your level says. Runs as a foreground service, so it shows a
 * quiet "Goggins mode is on" notification while active.
 */
class GogginsService : Service() {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    private var watcher: Job? = null

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_TURN_OFF) {
            Settings(this).gogginsPaused = true
            NotificationManagerCompat.from(this).cancel(WARNING_ID)
            stopSelf()
            return START_NOT_STICKY
        }
        createChannels()
        val type = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE else 0
        ServiceCompat.startForeground(this, STATUS_ID, statusNotification(), type)
        if (watcher == null) watcher = scope.launch { watch() }
        return START_STICKY
    }

    override fun onDestroy() {
        scope.cancel()
        NotificationManagerCompat.from(this).cancel(WARNING_ID)
        super.onDestroy()
    }

    private suspend fun watch() {
        val usage = UsageReader(this)
        val settings = Settings(this)
        var checkedUntil = Instant.now()
        var inFront = usage.foregroundApp(checkedUntil.minus(Duration.ofMinutes(10)), checkedUntil, null)
        var lastWarning: Instant? = null
        var warned = 0

        while (scope.isActive) {
            if (!GogginsMode.shouldRun(this)) {
                stopSelf()
                return
            }
            val now = Instant.now()
            inFront = usage.foregroundApp(checkedUntil, now, inFront)
            checkedUntil = now

            val watched = inFront?.takeIf { it in settings.gogginsApps }
            if (watched == null) {
                // Left the app: the next visit starts over
                if (lastWarning != null) NotificationManagerCompat.from(this).cancel(WARNING_ID)
                lastWarning = null
            } else {
                val every = GogginsMode.nagEvery(settings.gogginsLevel)
                val due = lastWarning == null || (every != null && Duration.between(lastWarning, now).seconds >= every)
                if (due) {
                    warn(GogginsMode.APPS[watched] ?: watched, settings, warned++)
                    lastWarning = now
                }
            }
            delay(POLL_MS)
        }
    }

    private fun warn(app: String, settings: Settings, count: Int) {
        val goal = settings.gogginsGoal.ifEmpty { "your goal" }
        val messages = listOf(
            "Stay hard. Get off $app.",
            "“$goal” is a ${settings.gogginsLevel}/10. Is $app part of the plan?",
            "Nobody is coming to save you. Close $app and get back to “$goal”.",
            "Every minute on $app is a minute taken from “$goal”.",
            "You chose ${settings.gogginsLevel}/10. Prove it. Leave $app.",
        )
        val notification = NotificationCompat.Builder(this, WARNING_CHANNEL)
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setContentTitle("🔥 Goggins mode · level ${settings.gogginsLevel}")
            .setContentText(messages[count % messages.size])
            .setStyle(NotificationCompat.BigTextStyle().bigText(messages[count % messages.size]))
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setCategory(NotificationCompat.CATEGORY_REMINDER)
            .setVibrate(longArrayOf(0, 400, 200, 400))
            .setContentIntent(openApp())
            .addAction(0, "Turn off Goggins mode", turnOff())
            .setAutoCancel(true)
            .build()
        // Without the notification permission there's nothing to show; Settings asks for it
        val allowed = Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU ||
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED
        if (allowed) {
            NotificationManagerCompat.from(this).notify(WARNING_ID, notification)
        }
    }

    private fun statusNotification() = NotificationCompat.Builder(this, STATUS_CHANNEL)
        .setSmallIcon(R.drawable.ic_launcher_foreground)
        .setContentTitle("Goggins mode is on · level ${Settings(this).gogginsLevel}")
        .setContentText("Watching ${Settings(this).gogginsApps.size} distracting apps")
        .setOngoing(true)
        .setContentIntent(openApp())
        .addAction(0, "Turn off", turnOff())
        .build()

    private fun openApp() = PendingIntent.getActivity(
        this, 0, Intent(this, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE,
    )

    private fun turnOff() = PendingIntent.getService(
        this, 1, Intent(this, GogginsService::class.java).setAction(ACTION_TURN_OFF), PendingIntent.FLAG_IMMUTABLE,
    )

    private fun createChannels() {
        val manager = getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(
            NotificationChannel(STATUS_CHANNEL, "Goggins mode status", NotificationManager.IMPORTANCE_LOW),
        )
        manager.createNotificationChannel(
            NotificationChannel(WARNING_CHANNEL, "Goggins mode warnings", NotificationManager.IMPORTANCE_HIGH).apply {
                enableVibration(true)
                vibrationPattern = longArrayOf(0, 400, 200, 400)
            },
        )
    }

    companion object {
        private const val ACTION_TURN_OFF = "com.liferpg.sync.GOGGINS_OFF"
        private const val STATUS_CHANNEL = "goggins_status"
        private const val WARNING_CHANNEL = "goggins_warnings"
        private const val STATUS_ID = 10
        private const val WARNING_ID = 11
        private const val POLL_MS = 3_000L
    }
}
