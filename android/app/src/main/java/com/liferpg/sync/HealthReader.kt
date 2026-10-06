package com.liferpg.sync

import android.content.Context
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.DistanceRecord
import androidx.health.connect.client.records.ExerciseSessionRecord
import androidx.health.connect.client.records.RestingHeartRateRecord
import androidx.health.connect.client.records.SleepSessionRecord
import androidx.health.connect.client.records.StepsRecord
import androidx.health.connect.client.records.WeightRecord
import androidx.health.connect.client.request.AggregateRequest
import androidx.health.connect.client.request.ReadRecordsRequest
import androidx.health.connect.client.time.TimeRangeFilter
import java.time.Duration
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId

data class HealthDay(
    val steps: Long?,
    val activeMinutes: Long?,
    val weightKg: Double?,
    val restingHr: Long?,
    val sleep: SleepWindow?,
    val runKm: Double? = null,         // every running workout that day
    val longestRunKm: Double? = null,  // the longest one
)

/** A night of sleep: when it started and ended, and minutes actually asleep. */
data class SleepWindow(val start: Instant, val end: Instant, val minutesAsleep: Long)

/** Reads what Samsung Health (or any other app) shared into Health Connect. */
class HealthReader(private val context: Context) {
    private val client by lazy { HealthConnectClient.getOrCreate(context) }

    val isAvailable get() = HealthConnectClient.getSdkStatus(context) == HealthConnectClient.SDK_AVAILABLE

    suspend fun grantedPermissions(): Set<String> = client.permissionController.getGrantedPermissions()

    suspend fun read(day: LocalDate, zone: ZoneId): HealthDay {
        val granted = grantedPermissions()
        val start = day.atStartOfDay(zone).toInstant()
        val end = day.plusDays(1).atStartOfDay(zone).toInstant()
        val range = TimeRangeFilter.between(start, end)

        val steps = if (READ_STEPS in granted) {
            client.aggregate(AggregateRequest(setOf(StepsRecord.COUNT_TOTAL), range))[StepsRecord.COUNT_TOTAL]
        } else null

        val sessions = if (READ_EXERCISE in granted) client.readRecords(ReadRecordsRequest(ExerciseSessionRecord::class, range)).records else null
        val activeMinutes = sessions?.sumOf { Duration.between(it.startTime, it.endTime).toMinutes() }
        // Runs: the distance recorded during each running workout (Samsung Health shares both)
        val runs = if (sessions != null && READ_DISTANCE in granted) {
            sessions.filter { it.exerciseType in RUNNING }.map { run ->
                client.aggregate(AggregateRequest(setOf(DistanceRecord.DISTANCE_TOTAL), TimeRangeFilter.between(run.startTime, run.endTime)))[DistanceRecord.DISTANCE_TOTAL]
                    ?.inKilometers ?: 0.0
            }.filter { it > 0 }
        } else emptyList()

        val weightKg = if (READ_WEIGHT in granted) {
            client.readRecords(ReadRecordsRequest(WeightRecord::class, range)).records
                .maxByOrNull { it.time }?.weight?.inKilograms
        } else null

        val restingHr = if (READ_RESTING_HR in granted) {
            client.readRecords(ReadRecordsRequest(RestingHeartRateRecord::class, range)).records
                .maxByOrNull { it.time }?.beatsPerMinute
        } else null

        return HealthDay(
            steps, activeMinutes, weightKg, restingHr, if (READ_SLEEP in granted) readSleep(start) else null,
            runKm = runs.sum().takeIf { runs.isNotEmpty() }, longestRunKm = runs.maxOrNull(),
        )
    }

    /** The longest sleep session that ended between midnight and 14:00 of the day. */
    private suspend fun readSleep(dayStart: Instant): SleepWindow? {
        val morningEnd = dayStart.plus(Duration.ofHours(14))
        val range = TimeRangeFilter.between(dayStart.minus(Duration.ofHours(12)), morningEnd)
        val session = client.readRecords(ReadRecordsRequest(SleepSessionRecord::class, range)).records
            .filter { it.endTime > dayStart && it.endTime <= morningEnd }
            .maxByOrNull { Duration.between(it.startTime, it.endTime) }
            ?: return null

        val total = Duration.between(session.startTime, session.endTime).toMinutes()
        val awake = session.stages
            .filter { it.stage in AWAKE_STAGES }
            .sumOf { Duration.between(it.startTime, it.endTime).toMinutes() }
        return SleepWindow(session.startTime, session.endTime, total - awake)
    }

    companion object {
        private val READ_STEPS = HealthPermission.getReadPermission(StepsRecord::class)
        private val READ_EXERCISE = HealthPermission.getReadPermission(ExerciseSessionRecord::class)
        private val READ_SLEEP = HealthPermission.getReadPermission(SleepSessionRecord::class)
        private val READ_WEIGHT = HealthPermission.getReadPermission(WeightRecord::class)
        private val READ_RESTING_HR = HealthPermission.getReadPermission(RestingHeartRateRecord::class)
        private val READ_DISTANCE = HealthPermission.getReadPermission(DistanceRecord::class)
        private val RUNNING = setOf(ExerciseSessionRecord.EXERCISE_TYPE_RUNNING, ExerciseSessionRecord.EXERCISE_TYPE_RUNNING_TREADMILL)

        val PERMISSIONS = setOf(
            READ_STEPS, READ_EXERCISE, READ_SLEEP, READ_WEIGHT, READ_RESTING_HR, READ_DISTANCE,
            // Lets the hourly sync read while the app is closed
            HealthPermission.PERMISSION_READ_HEALTH_DATA_IN_BACKGROUND,
        )

        private val AWAKE_STAGES = setOf(
            SleepSessionRecord.STAGE_TYPE_AWAKE,
            SleepSessionRecord.STAGE_TYPE_AWAKE_IN_BED,
            SleepSessionRecord.STAGE_TYPE_OUT_OF_BED,
        )
    }
}
