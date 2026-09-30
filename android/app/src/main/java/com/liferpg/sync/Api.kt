package com.liferpg.sync

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.time.LocalDate
import java.util.concurrent.TimeUnit

/** The server said no. `code` is the HTTP status; 4xx won't fix itself on retry, 5xx might. */
class ApiException(val code: Int, message: String) : Exception(message)

/** Every call the app makes to the Life RPG server, authenticated with the device token. */
class Api(private val settings: Settings) {

    suspend fun device(): String = JSONObject(call("GET", "/devices/me")!!).getString("name")

    suspend fun character(): CharacterSheet = parseCharacterSheet(JSONObject(call("GET", "/stats/character")!!))

    /** Raw JSON, so the widget can cache it as-is */
    suspend fun characterJson(): String = call("GET", "/stats/character")!!

    suspend fun streaksJson(): String = call("GET", "/stats/streaks")!!

    suspend fun levelJson(): String = call("GET", "/stats/level")!!

    suspend fun level(): Level = parseLevel(JSONObject(levelJson()))

    /** null when nothing is logged for that day yet */
    suspend fun day(date: LocalDate): DayLog? = try {
        parseDayLog(JSONObject(call("GET", "/daily-logs/$date")!!))
    } catch (e: ApiException) {
        if (e.code == 404) null else throw e
    }

    /** Check-in values; they override the phone's values field by field */
    suspend fun saveManual(date: LocalDate, sections: JSONObject): DayLog =
        parseDayLog(JSONObject(call("PUT", "/daily-logs/$date?source=manual", sections)!!))

    /** Drop one check-in value so the phone's value shows through again */
    suspend fun clearManual(date: LocalDate, section: String, field: String) {
        call("DELETE", "/daily-logs/$date?source=manual&section=$section&field=$field")
    }

    /** Phone data for several days in one request */
    suspend fun syncDays(days: JSONArray) {
        call("POST", "/daily-logs/batch?source=auto", JSONObject().put("days", days))
    }

    suspend fun goals(): List<Goal> = parseGoals(JSONArray(call("GET", "/goals")!!))

    suspend fun createGoal(body: JSONObject): Goal = parseGoal(JSONObject(call("POST", "/goals", body)!!))

    suspend fun updateGoal(id: Int, body: JSONObject): Goal = parseGoal(JSONObject(call("PATCH", "/goals/$id", body)!!))

    suspend fun deleteGoal(id: Int) {
        call("DELETE", "/goals/$id")
    }

    suspend fun profile(): Profile = parseProfile(JSONObject(call("GET", "/profile")!!))

    suspend fun updateProfile(body: JSONObject): Profile = parseProfile(JSONObject(call("PATCH", "/profile", body)!!))

    suspend fun meals(date: LocalDate): DayMeals = parseDayMeals(JSONObject(call("GET", "/meals?day=$date")!!))

    /** Sends a meal photo; the server reads it with AI and saves the meal. Can take ~30 s. */
    suspend fun logMealPhoto(jpeg: ByteArray, eatenAt: String?, note: String?): Meal = withContext(Dispatchers.IO) {
        check(settings.isConfigured) { "Enter the server address and device token in Settings" }
        val form = MultipartBody.Builder().setType(MultipartBody.FORM)
            .addFormDataPart("photo", "meal.jpg", jpeg.toRequestBody("image/jpeg".toMediaType()))
            .apply {
                eatenAt?.let { addFormDataPart("eaten_at", it) }
                note?.takeIf { it.isNotBlank() }?.let { addFormDataPart("note", it) }
            }
            .build()
        val request = Request.Builder()
            .url("${settings.serverUrl}/meals/photo")
            .header("Authorization", "Bearer ${settings.token}")
            .post(form)
            .build()
        photoClient.newCall(request).execute().use { response ->
            val text = response.body.string()
            if (!response.isSuccessful) throw ApiException(response.code, errorDetail(text) ?: "Server error ${response.code}")
            parseMeal(JSONObject(text))
        }
    }

    suspend fun logMeal(body: JSONObject): Meal = parseMeal(JSONObject(call("POST", "/meals", body)!!))

    suspend fun updateMeal(id: Int, body: JSONObject): Meal = parseMeal(JSONObject(call("PATCH", "/meals/$id", body)!!))

    suspend fun deleteMeal(id: Int) {
        call("DELETE", "/meals/$id")
    }

    suspend fun income(): Income = parseIncome(JSONObject(call("GET", "/income")!!))

    suspend fun updateIncome(body: JSONObject): Income = parseIncome(JSONObject(call("PUT", "/income", body)!!))

    /**
     * Signs in (or signs up) once with email and password, and gets this phone its own device token.
     * The password and the short-lived login token are never stored; only the device token is.
     */
    suspend fun connectWithAccount(email: String, password: String, deviceName: String, newAccount: Boolean): String {
        val credentials = JSONObject().put("email", email.trim()).put("password", password)
        val auth = send("POST", if (newAccount) "/auth/register" else "/auth/login", credentials, bearer = null)
        val login = JSONObject(auth!!).getString("access_token")
        val device = send("POST", "/devices", JSONObject().put("name", deviceName), bearer = login)
        return JSONObject(device!!).getString("token")
    }

    private suspend fun call(method: String, path: String, body: JSONObject? = null): String? {
        check(settings.isConfigured) { "Enter the server address and device token in Settings" }
        return send(method, path, body, settings.token)
    }

    private suspend fun send(method: String, path: String, body: JSONObject?, bearer: String?): String? = withContext(Dispatchers.IO) {
        val requestBody = body?.toString()?.toRequestBody(JSON)
        val request = Request.Builder()
            .url(settings.serverUrl + path)
            .apply { if (bearer != null) header("Authorization", "Bearer $bearer") }
            .method(method, requestBody)
            .build()
        client.newCall(request).execute().use { response ->
            val text = response.body.string()
            if (!response.isSuccessful) throw ApiException(response.code, errorDetail(text) ?: "Server error ${response.code}")
            text.ifEmpty { null }
        }
    }

    /** FastAPI errors: {"detail": "message"} or, for validation, {"detail": [{"msg": ...}, ...]} */
    private fun errorDetail(text: String): String? = runCatching {
        when (val detail = JSONObject(text).get("detail")) {
            is String -> detail
            is JSONArray -> (0 until detail.length()).joinToString("; ") { detail.getJSONObject(it).getString("msg") }
            else -> null
        }
    }.getOrNull()

    companion object {
        private val JSON = "application/json".toMediaType()
        private val client = OkHttpClient.Builder()
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(20, TimeUnit.SECONDS)
            .build()

        /** The AI takes a while to read a photo */
        private val photoClient = client.newBuilder().readTimeout(90, TimeUnit.SECONDS).build()
    }
}
