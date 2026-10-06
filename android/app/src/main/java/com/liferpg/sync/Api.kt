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

    /** Every stat's and category's score for each of the last [days] days, oldest first */
    suspend fun history(days: Int): List<HistoryDay> {
        val start = LocalDate.now().minusDays((days - 1).toLong())
        return list("/stats/character/history?start=$start", ::parseHistoryDay)
    }

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

    /** Every day that has something logged between [start] and [end], by ISO date */
    suspend fun days(start: LocalDate, end: LocalDate): Map<String, DayLog> =
        list("/daily-logs?start=$start&end=$end", ::parseDayLog).associateBy { it.date }

    /** What each value is, how it's entered and which stats read it */
    suspend fun fields(): FieldCatalog = parseFieldCatalog(JSONObject(call("GET", "/daily-logs/fields")!!))

    /** Remove one value: source "manual" (your correction), "auto" (the phone's) or "all" */
    suspend fun clearField(date: LocalDate, section: String, field: String, source: String) {
        call("DELETE", "/daily-logs/$date?source=$source&section=$section&field=$field")
    }

    /** The questions, answers to start from, and your latest results */
    suspend fun questionnaire(): Questionnaire = parseQuestionnaire(JSONObject(call("GET", "/questionnaire")!!))

    /** Saves an attempt (every one is kept) and returns your priorities, focus areas and plan */
    suspend fun submitQuestionnaire(answers: JSONObject): Attempt =
        parseAttempt(JSONObject(call("POST", "/questionnaire", JSONObject().put("answers", answers))!!))

    /** Every attempt, newest first */
    suspend fun attempts(): List<Attempt> = list("/questionnaire/attempts", ::parseAttempt)

    // ---- Friends

    suspend fun friends(): FriendsOverview = parseFriendsOverview(JSONObject(call("GET", "/friends")!!))

    /** Turns sharing switches on or off (level, stats, streaks, goals); applies to all friends */
    suspend fun updateSharing(body: JSONObject) {
        call("PATCH", "/friends/sharing", body)
    }

    /** By friend code (K7QF-M2XA) or email, whichever [who] looks like. Returns "pending" or "accepted". */
    suspend fun addFriend(who: String): String {
        val body = if ("@" in who) JSONObject().put("email", who.trim()) else JSONObject().put("code", who.trim())
        return JSONObject(call("POST", "/friends/requests", body)!!).getString("status")
    }

    suspend fun acceptFriend(requestId: Int) {
        call("POST", "/friends/requests/$requestId/accept")
    }

    /** Decline a request to you, or take back one you sent */
    suspend fun dropRequest(requestId: Int) {
        call("DELETE", "/friends/requests/$requestId")
    }

    suspend fun removeFriend(userId: Int) {
        call("DELETE", "/friends/$userId")
    }

    /** Everyone by level and XP: the top 50 and your own place */
    suspend fun globalBoard(): GlobalBoard = parseGlobalBoard(JSONObject(call("GET", "/friends/global")!!))

    /** You (everything) and your friends (what they share) */
    suspend fun leaderboard(): List<FriendView> = list("/friends/leaderboard", ::parseFriendView)

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

    // ---- Plan: milestones, quests (todos), projects, skills (life areas)

    suspend fun milestones(): List<Milestone> = list("/milestones", ::parseMilestone)

    suspend fun createMilestone(description: String, xp: Int): Milestone =
        parseMilestone(JSONObject(call("POST", "/milestones", JSONObject().put("description", description).put("xp_reward", xp))!!))

    suspend fun updateMilestone(key: String, description: String, xp: Int): Milestone =
        parseMilestone(JSONObject(call("PATCH", "/milestones/$key", JSONObject().put("description", description).put("xp_reward", xp))!!))

    suspend fun completeMilestone(key: String) {
        call("POST", "/milestones/$key/complete")
    }

    suspend fun deleteMilestone(key: String) {
        call("DELETE", "/milestones/$key")
    }

    suspend fun quests(): List<Quest> = list("/todos", ::parseQuest)

    /** body: task, area_id, base_xp, deadline (all of them to create, any of them to update) */
    suspend fun createQuest(body: JSONObject): Quest = parseQuest(JSONObject(call("POST", "/todos", body)!!))

    suspend fun updateQuest(id: Int, body: JSONObject): Quest = parseQuest(JSONObject(call("PATCH", "/todos/$id", body)!!))

    suspend fun completeQuest(id: Int) {
        call("POST", "/todos/$id/complete")
    }

    suspend fun deleteQuest(id: Int) {
        call("DELETE", "/todos/$id")
    }

    suspend fun projects(): List<Project> = list("/projects", ::parseProject)

    /** body: name, value, deadline */
    suspend fun createProject(body: JSONObject): Project = parseProject(JSONObject(call("POST", "/projects", body)!!))

    suspend fun updateProject(id: Int, body: JSONObject): Project = parseProject(JSONObject(call("PATCH", "/projects/$id", body)!!))

    suspend fun completeProject(id: Int) {
        call("POST", "/projects/$id/complete")
    }

    suspend fun deleteProject(id: Int) {
        call("DELETE", "/projects/$id")
    }

    suspend fun skills(): List<Skill> = list("/life-areas", ::parseSkill)

    suspend fun createSkill(name: String): Skill = parseSkill(JSONObject(call("POST", "/life-areas", JSONObject().put("name", name))!!))

    suspend fun renameSkill(id: Int, name: String): Skill =
        parseSkill(JSONObject(call("PATCH", "/life-areas/$id", JSONObject().put("name", name))!!))

    suspend fun deleteSkill(id: Int) {
        call("DELETE", "/life-areas/$id")
    }

    private suspend fun <T> list(path: String, parse: (JSONObject) -> T): List<T> {
        val rows = JSONArray(call("GET", path)!!)
        return (0 until rows.length()).map { parse(rows.getJSONObject(it)) }
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
        val request = Request.Builder()
            .url(settings.serverUrl + path)
            .apply { if (bearer != null) header("Authorization", "Bearer $bearer") }
            .method(method, requestBody(method, body))
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

        /**
         * OkHttp refuses a POST, PUT or PATCH without a body, so actions that send nothing
         * (completing a quest, milestone or project) get an empty one instead of failing.
         */
        internal fun requestBody(method: String, body: JSONObject?) = when {
            body != null -> body.toString().toRequestBody(JSON)
            method in setOf("POST", "PUT", "PATCH") -> ByteArray(0).toRequestBody(null)
            else -> null
        }
        private val client = OkHttpClient.Builder()
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(20, TimeUnit.SECONDS)
            .build()

        /** The AI takes a while to read a photo */
        private val photoClient = client.newBuilder().readTimeout(90, TimeUnit.SECONDS).build()
    }
}
