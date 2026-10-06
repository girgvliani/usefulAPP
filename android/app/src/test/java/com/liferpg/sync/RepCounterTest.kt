package com.liferpg.sync

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** Rep counting from joint angles, frame by frame */
class RepCounterTest {

    private fun RepCounter.feed(vararg angles: Double?) = angles.count { update(it) }

    @Test
    fun anglesAtTheJoint() {
        assertEquals(90.0, RepCounter.jointAngle(0f, 0f, 0f, 1f, 1f, 1f), 1e-6)
        assertEquals(180.0, RepCounter.jointAngle(-1f, 0f, 0f, 0f, 1f, 0f), 1e-6)
        assertEquals(45.0, RepCounter.jointAngle(1f, 0f, 0f, 0f, 1f, 1f), 1e-6)
    }

    @Test
    fun countsFullPushups() {
        val c = RepCounter(Exercise.Pushups)
        // up, down, up = one rep; twice more
        repeat(3) { c.feed(170.0, 170.0, 170.0, 80.0, 75.0, 75.0, 75.0, 120.0, 170.0, 170.0, 170.0) }
        assertEquals(3, c.count)
    }

    @Test
    fun halfRepsDontCount() {
        val c = RepCounter(Exercise.Pushups)
        // Down only to 115° (not past 100°): no rep
        repeat(4) { c.feed(170.0, 170.0, 170.0, 115.0, 115.0, 115.0, 170.0, 170.0, 170.0) }
        assertEquals(0, c.count)
    }

    @Test
    fun oneJitteryFrameIsNotARep() {
        val c = RepCounter(Exercise.Squats)
        c.feed(175.0, 175.0, 175.0)
        // A single wild frame (smoothing halves it, and a phase must hold 2 frames)
        c.feed(60.0, 175.0, 175.0, 175.0)
        assertEquals(0, c.count)
    }

    @Test
    fun losingSightKeepsTheCount() {
        val c = RepCounter(Exercise.Situps)
        c.feed(140.0, 140.0, 140.0, 50.0, 50.0, 50.0, 50.0, 140.0, 140.0, 140.0, 140.0)
        assertEquals(1, c.count)
        assertFalse(c.update(null))
        assertEquals(null, c.angle)
        c.feed(40.0, 40.0, 40.0, 40.0, 150.0, 150.0, 150.0, 150.0)
        assertEquals(2, c.count)
        c.reset()
        assertEquals(0, c.count)
        assertEquals(Phase.Unknown, c.phase)
    }

    @Test
    fun startingDownCountsTheFirstRep() {
        val c = RepCounter(Exercise.Pushups)
        assertTrue(c.feed(80.0, 80.0, 80.0, 170.0, 170.0, 170.0, 170.0, 170.0) == 1)
    }
}
