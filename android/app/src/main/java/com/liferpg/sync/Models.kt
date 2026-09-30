package com.liferpg.sync

import org.json.JSONArray
import org.json.JSONObject

data class StatComponent(val name: String, val weight: Double, val score: Double?, val note: String)

data class StatPenalty(val name: String, val points: Double, val note: String)

data class Stat(
    val code: String,
    val name: String,
    val score: Int?,
    val grade: String?,
    val confidence: Int,
    val ceiling: Int?,
    val ceilingNote: String,
    val bestMove: String?,
    val bestMovePoints: Int?,
    val components: List<StatComponent>,
    val penalties: List<StatPenalty>,
)

data class CharacterSheet(val date: String, val overall: Int?, val overallGrade: String?, val stats: List<Stat>)

data class Goal(
    val id: Int,
    val type: String,
    val title: String,
    val unit: String,
    val startValue: Double,
    val targetValue: Double,
    val currentValue: Double?,
    val progress: Double?,
    val direction: String,
    val achieved: Boolean,
    val deadline: String?,
    val intensity: Int,  // Goggins scale, 1-10
)

data class Profile(
    val displayName: String?,
    val currency: String,
    val timezone: String,
    val pushupTarget: Int,
    val stepsTarget: Int,
    val sleepTarget: Double,
    val heightCm: Double?,
    val birthYear: Int?,
    val sex: String?,
)

data class MealItem(val name: String, val grams: Double?, val kcal: Double, val protein: Double, val carbs: Double, val fat: Double)

data class Meal(
    val id: Int,
    val eatenAt: String,
    val mealType: String,
    val name: String,
    val items: List<MealItem>,
    val kcal: Double,
    val protein: Double,
    val carbs: Double,
    val fat: Double,
    val source: String,
    val confidence: Double?,
)

/** calories/protein are null until the profile has height, birth year, sex and a weight (see missing) */
data class NutritionTargets(val calories: Int?, val protein: Int?, val adjustment: Int, val missing: List<String>)

data class DayMeals(val date: String, val meals: List<Meal>, val kcal: Double, val protein: Double, val targets: NutritionTargets)

data class Income(val monthlyGoal: Int, val earned: Int)

/** Global level from all XP. progress: 0-1 through the current level. */
data class Level(
    val level: Int,
    val xp: Int,
    val levelStartXp: Int,
    val nextLevelXp: Int,
    val todayXp: Int,
    val title: String = "",
    val nextTitle: String? = null,
    val today: List<Pair<String, Int>> = emptyList(),
    val sources: Map<String, Int> = emptyMap(),
    val history: List<Pair<String, Int>> = emptyList(),  // (ISO date, activity XP), oldest first
) {
    val progress get() = ((xp - levelStartXp).toFloat() / (nextLevelXp - levelStartXp)).coerceIn(0f, 1f)
    val toNext get() = nextLevelXp - xp
}

data class Streak(
    val key: String,
    val name: String,
    val emoji: String,
    val rule: String,
    val current: Int,
    val best: Int,
    val doneToday: Boolean,
    val atRisk: Boolean,
    val brokenToday: Boolean,
)

/** mood: happy (all safe), worried (a streak at risk), angry (at risk in the evening, or broken), idle (none) */
data class Streaks(val date: String, val mood: String, val message: String, val streaks: List<Streak>)

/** One day as the server holds it: what the phone sent, what you entered, and the two combined. */
data class DayLog(val auto: JSONObject, val manual: JSONObject, val merged: JSONObject)

// ---- JSON parsing (org.json, so no serialization plugin is needed)

private fun JSONObject.intOrNull(key: String): Int? = if (isNull(key)) null else getInt(key)
private fun JSONObject.doubleOrNull(key: String): Double? = if (isNull(key)) null else getDouble(key)
private fun JSONObject.stringOrNull(key: String): String? = if (isNull(key)) null else getString(key)
private fun <T> JSONArray.map(transform: (JSONObject) -> T): List<T> = (0 until length()).map { transform(getJSONObject(it)) }

fun parseCharacterSheet(json: JSONObject) = CharacterSheet(
    date = json.getString("date"),
    overall = json.intOrNull("overall"),
    overallGrade = json.stringOrNull("overall_grade"),
    stats = json.getJSONArray("stats").map { s ->
        val best = s.optJSONObject("best_move")
        Stat(
            code = s.getString("code"),
            name = s.getString("name"),
            score = s.intOrNull("score"),
            grade = s.stringOrNull("grade"),
            confidence = s.getInt("confidence"),
            ceiling = s.intOrNull("ceiling"),
            ceilingNote = s.getString("ceiling_note"),
            bestMove = best?.getString("name"),
            bestMovePoints = best?.getInt("points"),
            components = s.getJSONArray("components").map {
                StatComponent(it.getString("name"), it.getDouble("weight"), it.doubleOrNull("score"), it.getString("note"))
            },
            penalties = s.getJSONArray("penalties").map {
                StatPenalty(it.getString("name"), it.getDouble("points"), it.getString("note"))
            },
        )
    },
)

fun parseGoal(json: JSONObject) = Goal(
    id = json.getInt("id"),
    type = json.getString("type"),
    title = json.getString("title"),
    unit = json.getString("unit"),
    startValue = json.getDouble("start_value"),
    targetValue = json.getDouble("target_value"),
    currentValue = json.doubleOrNull("current_value"),
    progress = json.doubleOrNull("progress"),
    direction = json.getString("direction"),
    achieved = json.getBoolean("achieved"),
    deadline = json.stringOrNull("deadline"),
    intensity = json.optInt("intensity", 5),
)

fun parseGoals(json: JSONArray) = json.map(::parseGoal)

fun parseProfile(json: JSONObject) = Profile(
    displayName = json.stringOrNull("display_name"),
    currency = json.getString("currency"),
    timezone = json.getString("timezone"),
    pushupTarget = json.getInt("pushup_target"),
    stepsTarget = json.getInt("steps_target"),
    sleepTarget = json.getDouble("sleep_target"),
    heightCm = json.doubleOrNull("height_cm"),
    birthYear = json.intOrNull("birth_year"),
    sex = json.stringOrNull("sex"),
)

fun parseMeal(json: JSONObject) = Meal(
    id = json.getInt("id"),
    eatenAt = json.getString("eaten_at"),
    mealType = json.getString("meal_type"),
    name = json.getString("name"),
    items = json.getJSONArray("items").map {
        MealItem(it.getString("name"), it.doubleOrNull("grams"), it.getDouble("kcal"), it.getDouble("protein"), it.getDouble("carbs"), it.getDouble("fat"))
    },
    kcal = json.getDouble("kcal"),
    protein = json.getDouble("protein"),
    carbs = json.getDouble("carbs"),
    fat = json.getDouble("fat"),
    source = json.getString("source"),
    confidence = json.doubleOrNull("confidence"),
)

fun parseDayMeals(json: JSONObject): DayMeals {
    val targets = json.getJSONObject("targets")
    val missing = targets.getJSONArray("missing")
    return DayMeals(
        date = json.getString("date"),
        meals = json.getJSONArray("meals").map(::parseMeal),
        kcal = json.getDouble("kcal"),
        protein = json.getDouble("protein"),
        targets = NutritionTargets(
            calories = targets.intOrNull("calories"),
            protein = targets.intOrNull("protein"),
            adjustment = targets.getInt("adjustment"),
            missing = (0 until missing.length()).map { missing.getString(it) },
        ),
    )
}

fun parseStreaks(json: JSONObject) = Streaks(
    date = json.getString("date"),
    mood = json.getString("mood"),
    message = json.getString("message"),
    streaks = json.getJSONArray("streaks").map {
        Streak(
            key = it.getString("key"),
            name = it.getString("name"),
            emoji = it.getString("emoji"),
            rule = it.getString("rule"),
            current = it.getInt("current"),
            best = it.getInt("best"),
            doneToday = it.getBoolean("done_today"),
            atRisk = it.getBoolean("at_risk"),
            brokenToday = it.optBoolean("broken_today"),
        )
    },
)

fun parseLevel(json: JSONObject) = Level(
    level = json.getInt("level"),
    xp = json.getInt("xp"),
    levelStartXp = json.getInt("level_start_xp"),
    nextLevelXp = json.getInt("next_level_xp"),
    todayXp = json.getInt("today_xp"),
    title = json.optString("title"),
    nextTitle = json.stringOrNull("next_title").takeIf { json.has("next_title") },
    today = json.optJSONArray("today")?.map { it.getString("reason") to it.getInt("xp") }.orEmpty(),
    sources = json.optJSONObject("sources")?.let { s -> s.keys().asSequence().associateWith { s.getInt(it) } }.orEmpty(),
    history = json.optJSONArray("history")?.map { it.getString("date") to it.getInt("xp") }.orEmpty(),
)

fun parseIncome(json: JSONObject) = Income(json.getInt("monthly_goal"), json.getInt("current_month_earnings"))

fun parseDayLog(json: JSONObject) = DayLog(json.getJSONObject("auto"), json.getJSONObject("manual"), json.getJSONObject("merged"))
