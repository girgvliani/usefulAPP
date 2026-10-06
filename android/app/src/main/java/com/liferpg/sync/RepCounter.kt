package com.liferpg.sync

import kotlin.math.abs
import kotlin.math.atan2

/**
 * The exercises the camera can count, by the angle at one joint:
 * push-ups at the elbow (shoulder-elbow-wrist), squats at the knee (hip-knee-ankle), sit-ups at the hip
 * (shoulder-hip-knee). A rep is bending past [flexedBelow] and straightening past [extendedAbove] again.
 * Joints are ML Kit pose landmark ids, left side then right.
 */
enum class Exercise(
    val key: String,
    val label: String,
    val icon: String,
    val left: Triple<Int, Int, Int>,
    val right: Triple<Int, Int, Int>,
    val flexedBelow: Double,
    val extendedAbove: Double,
    val tip: String,
) {
    Pushups(
        "pushups", "Push-ups", "💪", Triple(11, 13, 15), Triple(12, 14, 16), 100.0, 150.0,
        "Phone on the floor 1-2 m away, side-on to you, your whole body in view.",
    ),
    Squats(
        "squats", "Squats", "🦵", Triple(23, 25, 27), Triple(24, 26, 28), 100.0, 155.0,
        "Stand 2-3 m away, side-on or facing the phone, head to feet in view.",
    ),
    Situps(
        "situps", "Sit-ups", "🧘", Triple(11, 23, 25), Triple(12, 24, 26), 75.0, 115.0,
        "Phone on the floor 1-2 m away, side-on, knees bent.",
    ),
}

enum class Phase { Unknown, Extended, Flexed }

/** Counts reps from one joint angle per camera frame. Pure logic, so it's tested without a camera. */
class RepCounter(val exercise: Exercise) {
    var count = 0
        private set
    var phase = Phase.Unknown
        private set
    /** The smoothed angle, null while the body isn't in view */
    var angle: Double? = null
        private set
    private var smoothed: Double? = null
    private var pending: Phase? = null
    private var pendingFrames = 0

    /** One frame. Returns true when this frame completed a rep. */
    fun update(raw: Double?): Boolean {
        if (raw == null) {
            angle = null
            return false
        }
        val s = smoothed?.let { it * (1 - SMOOTHING) + raw * SMOOTHING } ?: raw
        smoothed = s
        angle = s
        val seen = when {
            s < exercise.flexedBelow -> Phase.Flexed
            s > exercise.extendedAbove -> Phase.Extended
            else -> return false  // in between: keep the phase we're in
        }
        if (seen == phase) {
            pending = null
            return false
        }
        // A new phase has to hold for a couple of frames, so one jittery frame isn't a rep
        if (seen == pending) pendingFrames++ else { pending = seen; pendingFrames = 1 }
        if (pendingFrames < HOLD_FRAMES) return false
        val before = phase
        phase = seen
        pending = null
        if (before == Phase.Flexed && seen == Phase.Extended) {
            count++
            return true
        }
        return false
    }

    fun reset() {
        count = 0
        phase = Phase.Unknown
        angle = null
        smoothed = null
        pending = null
    }

    companion object {
        const val SMOOTHING = 0.5
        const val HOLD_FRAMES = 2
        /** Landmarks less sure than this don't count (ML Kit's in-frame likelihood) */
        const val MIN_LIKELIHOOD = 0.5f

        /** The angle at b, in degrees (0-180), between the lines to a and c */
        fun jointAngle(ax: Float, ay: Float, bx: Float, by: Float, cx: Float, cy: Float): Double {
            val degrees = Math.toDegrees(atan2((cy - by).toDouble(), (cx - bx).toDouble()) - atan2((ay - by).toDouble(), (ax - bx).toDouble()))
            val a = abs(degrees) % 360
            return if (a > 180) 360 - a else a
        }
    }
}
