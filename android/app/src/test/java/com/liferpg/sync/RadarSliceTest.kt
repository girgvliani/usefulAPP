package com.liferpg.sync

import com.liferpg.sync.ui.sliceAt
import org.junit.Assert.assertEquals
import org.junit.Test
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.sin

/** Tapping the radar picks the stat whose corner the tap points at. */
class RadarSliceTest {
    @Test
    fun cornersMapToTheirOwnIndex() {
        for (count in listOf(7, 8, 9)) {
            for (i in 0 until count) {
                // Exactly at corner i, and slightly to either side of it
                for (nudge in listOf(0.0, -0.3, 0.3)) {
                    val angle = -PI / 2 + 2 * PI * (i + nudge) / count
                    assertEquals("count $count, corner $i, nudge $nudge", i, sliceAt(cos(angle).toFloat() * 100, sin(angle).toFloat() * 100, count))
                }
            }
        }
    }

    @Test
    fun compassPointsWithNineStats() {
        assertEquals(0, sliceAt(0f, -100f, 9))   // straight up: the first stat (MP)
        assertEquals(2, sliceAt(100f, 0f, 9))    // right: 90 deg is nearest corner 2 (80 deg)
        assertEquals(7, sliceAt(-100f, 0f, 9))   // left: 270 deg is nearest corner 7 (280 deg)
        assertEquals(0, sliceAt(-5f, -100f, 9))  // just left of the top still wraps to the first
    }
}
