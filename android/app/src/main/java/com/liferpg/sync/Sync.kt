package com.liferpg.sync

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.time.Duration
import java.time.Instant
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter

/** Builds each day's summary and sends it to the server as source=auto. */
object Sync {
    private val HHMM = DateTimeFormatter.ofPattern("HH:mm")

    /** How far back "Import history" reaches: Health Connect's default read window. Screen time
     * usually only goes back 7-10 days, because that's all Android keeps. */
    const val HISTORY_DAYS = 30

    /**
     * Syncs the last [days] days ending today (by default yesterday, to finish it off, and today).
     * Days with nothing to send are skipped. Returns a summary for the status line.
     */
    suspend fun run(context: Context, days: Int = 2): String {
        val settings = Settings(context)
        check(settings.isConfigured) { "Enter the server address and device token first" }

        val zone = ZoneId.systemDefault()
        val today = LocalDate.now(zone)
        val built = (days - 1 downTo 0)
            .map { back -> today.minusDays(back.toLong()) }
            .map { day -> day to buildDay(context, day, zone) }
            .filter { (_, body) -> body.length() > 0 }
        if (built.isNotEmpty()) {
            Api(settings).syncDays(JSONArray(built.map { (day, body) -> JSONObject(body.toString()).put("date", day.toString()) }))
        }

        val time = LocalDateTime.now().format(DateTimeFormatter.ofPattern("MMM d HH:mm"))
        val status = if (days > 2) {
            val screenDays = built.count { (_, body) -> body.has("screen") }
            "✅ Imported ${built.size} of the last $days days ($time)\n" +
                "Screen time for $screenDays days; the rest had only health data or nothing Android still keeps"
        } else {
            "✅ Synced $time\n" + built.joinToString("\n") { (day, body) -> "$day  ${describe(body)}" }
        }
        settings.lastStatus = status
        return status
    }

    private suspend fun buildDay(context: Context, day: LocalDate, zone: ZoneId): JSONObject {
        val json = JSONObject()
        val usage = UsageReader(context)
        val health = HealthReader(context)
        val start = day.atStartOfDay(zone).toInstant()
        val end = minOf(day.plusDays(1).atStartOfDay(zone).toInstant(), Instant.now())

        if (usage.hasAccess) screenSection(context, usage, start, end)?.let { json.put("screen", it) }

        // Health Connect can refuse background reads; screen time still goes through
        val healthDay = if (health.isAvailable) runCatching { health.read(day, zone) }.getOrNull() else null
        healthDay?.let { h ->
            val body = JSONObject()
            h.steps?.takeIf { it > 0 }?.let { body.put("steps", it) }
            // Only send workouts, weight and heart rate when something was recorded, so a missing
            // wearable doesn't turn into "0 active minutes"
            h.activeMinutes?.takeIf { it > 0 }?.let { body.put("active_min", minOf(it, 1440)) }
            h.weightKg?.let { body.put("weight_kg", Math.round(it * 10) / 10.0) }
            h.restingHr?.let { body.put("resting_hr", it) }
            h.runKm?.let { body.put("run_km", Math.round(it * 100) / 100.0) }
            h.longestRunKm?.let { body.put("longest_run_km", Math.round(it * 100) / 100.0) }
            if (body.length() > 0) json.put("body", body)
        }

        val measured = healthDay?.sleep
        val sleep = measured ?: if (usage.hasAccess) usage.estimateSleep(day, zone) else null
        sleep?.let { s ->
            json.put("sleep", JSONObject().apply {
                put("bed", s.start.atZone(zone).format(HHMM))
                put("wake", s.end.atZone(zone).format(HHMM))
                put("hours", Math.round(s.minutesAsleep / 60.0 * 100) / 100.0)
                put("estimated", measured == null)
                // Only meaningful for measured sleep: an estimate starts exactly when the phone went dark
                if (measured != null) put("screen_before_bed", usage.hasAccess && usage.usedBefore(s.start))
            })
        }
        return json
    }

    /** null when Android has no usage left for that day (older than it keeps) */
    private fun screenSection(context: Context, usage: UsageReader, start: Instant, end: Instant): JSONObject? {
        val minutes = usage.appMinutes(start, end)
        val unlocks = usage.unlocks(start, end)
        if (minutes.isEmpty() && unlocks == 0) return null

        val categories = AppCategories(context)
        val onScreen = minutes.filterKeys { it !in categories.notScreenTime }
        val night = usage.appMinutes(start, minOf(start.plus(Duration.ofHours(5)), end))
            .filterKeys { it !in categories.notScreenTime }.values.sum()
        fun total(apps: Set<String>) = onScreen.filterKeys { it in apps }.values.sum()
        val gaming = onScreen.filterKeys { categories.isGame(it) }.values.sum()

        return JSONObject().apply {
            put("short_video_min", minOf(total(AppCategories.SHORT_VIDEO), 1440))
            put("long_video_min", minOf(total(AppCategories.LONG_VIDEO), 1440))
            put("gaming_min", minOf(gaming, 1440))
            put("social_min", minOf(total(AppCategories.SOCIAL), 1440))
            put("total_min", minOf(onScreen.values.sum(), 1440))
            put("night_min", minOf(night, 300))
            put("unlocks", minOf(unlocks, 5000))
            put("apps", JSONObject(minutes.mapValues { minOf(it.value, 1440) }))
        }
    }

    private fun describe(body: JSONObject): String {
        val parts = mutableListOf<String>()
        body.optJSONObject("sleep")?.let {
            parts += "sleep ${it.getDouble("hours")}h" + if (it.getBoolean("estimated")) " (est.)" else ""
        }
        body.optJSONObject("body")?.optLong("steps", -1)?.takeIf { it >= 0 }?.let { parts += "$it steps" }
        body.optJSONObject("screen")?.let {
            parts += "screen ${"%.1f".format(it.getLong("total_min") / 60.0)}h, ${it.getLong("unlocks")} unlocks, reels ${it.getLong("short_video_min")}m"
        }
        return parts.joinToString(" · ").ifEmpty { "nothing to send (check permissions)" }
    }
}
