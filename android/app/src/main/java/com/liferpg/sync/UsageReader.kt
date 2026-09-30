package com.liferpg.sync

import android.app.AppOpsManager
import android.app.usage.UsageEvents
import android.app.usage.UsageStatsManager
import android.content.Context
import android.os.Process
import java.time.Duration
import java.time.Instant
import java.time.LocalDate
import java.time.LocalTime
import java.time.ZoneId

/** Screen time per app, and a sleep estimate from when the phone stayed locked. */
class UsageReader(private val context: Context) {
    private val usageStats = context.getSystemService(UsageStatsManager::class.java)

    val hasAccess: Boolean
        get() {
            val appOps = context.getSystemService(AppOpsManager::class.java)
            val mode = appOps.unsafeCheckOpNoThrow(AppOpsManager.OPSTR_GET_USAGE_STATS, Process.myUid(), context.packageName)
            return mode == AppOpsManager.MODE_ALLOWED
        }

    /** Foreground minutes per package between [from] and [to]; apps under a minute are dropped. */
    fun appMinutes(from: Instant, to: Instant): Map<String, Long> {
        val totals = HashMap<String, Long>()
        val openSince = HashMap<String, Long>()
        fun close(pkg: String, at: Long) {
            val since = openSince.remove(pkg) ?: return
            // Clip to the window: we start reading early to catch apps already open at `from`
            val ms = minOf(at, to.toEpochMilli()) - maxOf(since, from.toEpochMilli())
            if (ms > 0) totals[pkg] = (totals[pkg] ?: 0) + ms
        }

        forEachEvent(from.minus(LOOKBACK), to) { event ->
            when (event.eventType) {
                UsageEvents.Event.ACTIVITY_RESUMED -> openSince.putIfAbsent(event.packageName, event.timeStamp)
                UsageEvents.Event.ACTIVITY_PAUSED,
                UsageEvents.Event.ACTIVITY_STOPPED -> close(event.packageName, event.timeStamp)
                UsageEvents.Event.SCREEN_NON_INTERACTIVE,
                UsageEvents.Event.DEVICE_SHUTDOWN -> openSince.keys.toList().forEach { close(it, event.timeStamp) }
            }
        }
        val now = minOf(to, Instant.now()).toEpochMilli()
        openSince.keys.toList().forEach { close(it, now) }

        return totals.mapValues { it.value / 60_000 }.filterValues { it >= 1 }
    }

    /**
     * Best guess at the night that ended on [day]: the longest stretch between 19:00 the evening
     * before and 14:00 on [day] when the phone wasn't in use. A glance under 5 minutes between
     * two idle stretches of an hour or more (checking the time at 3am) doesn't split the night.
     * Needs at least 3 hours to count.
     */
    fun estimateSleep(day: LocalDate, zone: ZoneId): SleepWindow? {
        val from = day.minusDays(1).atTime(LocalTime.of(19, 0)).atZone(zone).toInstant()
        val to = minOf(day.atTime(LocalTime.of(14, 0)).atZone(zone).toInstant(), Instant.now())
        if (!to.isAfter(from)) return null

        // Phone "in use" = from unlock (or screen on, if there's no lock screen) until screen off
        val events = mutableListOf<Pair<Long, Int>>()
        forEachEvent(from, to) { event ->
            if (event.eventType in USE_EVENTS) events += event.timeStamp to event.eventType
        }
        val startType = if (events.any { it.second == UsageEvents.Event.KEYGUARD_HIDDEN }) {
            UsageEvents.Event.KEYGUARD_HIDDEN
        } else {
            UsageEvents.Event.SCREEN_INTERACTIVE
        }

        val uses = mutableListOf<LongRange>()
        var useStart: Long? = null
        for ((time, type) in events) {
            when {
                type == startType && useStart == null -> useStart = time
                type == UsageEvents.Event.SCREEN_NON_INTERACTIVE && useStart != null -> {
                    uses += useStart..time
                    useStart = null
                }
            }
        }
        useStart?.let { uses += it..to.toEpochMilli() }

        // Idle stretches between uses
        val gaps = mutableListOf<LongRange>()
        var idleFrom = from.toEpochMilli()
        for (use in uses) {
            if (use.first > idleFrom) gaps += idleFrom..use.first
            idleFrom = maxOf(idleFrom, use.last)
        }
        if (to.toEpochMilli() > idleFrom) gaps += idleFrom..to.toEpochMilli()

        // A glance between two long idle stretches is a night-time check, not waking up
        val nights = mutableListOf<LongRange>()
        for (gap in gaps) {
            val prev = nights.lastOrNull()
            val isGlance = prev != null && gap.first - prev.last < GLANCE.toMillis()
            if (isGlance && prev!!.length() >= LONG_IDLE && gap.length() >= LONG_IDLE) {
                nights[nights.lastIndex] = prev.first..gap.last
            } else {
                nights += gap
            }
        }

        val night = nights.maxByOrNull { it.length() } ?: return null
        if (night.length() < MIN_SLEEP) return null
        return SleepWindow(Instant.ofEpochMilli(night.first), Instant.ofEpochMilli(night.last), night.length().toMinutes())
    }

    /**
     * The app in front after the events between [from] and [to], starting from [current] (what was
     * in front at [from]). null when the screen is off or you're on the home screen.
     */
    fun foregroundApp(from: Instant, to: Instant, current: String?): String? {
        var app = current
        forEachEvent(from, to) { event ->
            when (event.eventType) {
                UsageEvents.Event.ACTIVITY_RESUMED -> app = event.packageName
                UsageEvents.Event.ACTIVITY_PAUSED,
                UsageEvents.Event.ACTIVITY_STOPPED -> if (event.packageName == app) app = null
                UsageEvents.Event.SCREEN_NON_INTERACTIVE -> app = null
            }
        }
        return app
    }

    /** How many times the phone was unlocked (or switched on, without a lock screen) between [from] and [to]. */
    fun unlocks(from: Instant, to: Instant): Int {
        var unlocked = 0
        var screenOn = 0
        forEachEvent(from, to) { event ->
            when (event.eventType) {
                UsageEvents.Event.KEYGUARD_HIDDEN -> unlocked++
                UsageEvents.Event.SCREEN_INTERACTIVE -> screenOn++
            }
        }
        return if (unlocked > 0) unlocked else screenOn
    }

    /** True if the phone was unlocked in the hour before [bedtime]. */
    fun usedBefore(bedtime: Instant): Boolean {
        var used = false
        forEachEvent(bedtime.minus(Duration.ofHours(1)), bedtime) { event ->
            if (event.eventType == UsageEvents.Event.KEYGUARD_HIDDEN || event.eventType == UsageEvents.Event.ACTIVITY_RESUMED) {
                used = true
            }
        }
        return used
    }

    private inline fun forEachEvent(from: Instant, to: Instant, action: (UsageEvents.Event) -> Unit) {
        val events = usageStats.queryEvents(from.toEpochMilli(), to.toEpochMilli()) ?: return
        val event = UsageEvents.Event()
        while (events.hasNextEvent()) {
            events.getNextEvent(event)
            action(event)
        }
    }

    private fun LongRange.length() = Duration.ofMillis(last - first)

    companion object {
        private val LOOKBACK = Duration.ofHours(3)
        private val GLANCE = Duration.ofMinutes(5)
        private val LONG_IDLE = Duration.ofHours(1)
        private val MIN_SLEEP = Duration.ofHours(3)
        private val USE_EVENTS = setOf(
            UsageEvents.Event.KEYGUARD_HIDDEN,
            UsageEvents.Event.SCREEN_INTERACTIVE,
            UsageEvents.Event.SCREEN_NON_INTERACTIVE,
        )
    }
}
