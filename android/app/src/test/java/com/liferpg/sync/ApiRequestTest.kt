package com.liferpg.sync

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

/** Every request the app makes must be one OkHttp agrees to send. */
@RunWith(RobolectricTestRunner::class)
@Config(sdk = [36])
class ApiRequestTest {

    @Test
    fun actionsWithoutABodyStillGetOne() {
        // Completing a quest, milestone or project is a POST with nothing to send
        for (method in listOf("POST", "PUT", "PATCH")) {
            val body = Api.requestBody(method, null)
            assertNotNull(method, body)
            assertEquals(0L, body!!.contentLength())
            okhttp3.Request.Builder().url("https://example.com/todos/1/complete").method(method, body).build()
        }
    }

    @Test
    fun readsAndDeletesSendNone() {
        assertNull(Api.requestBody("GET", null))
        assertNull(Api.requestBody("DELETE", null))
    }

    @Test
    fun jsonBodiesAreSentAsJson() {
        val body = Api.requestBody("POST", JSONObject().put("task", "Read"))!!
        assertEquals("application/json", body.contentType().toString().substringBefore(';'))
    }
}
