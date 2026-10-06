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

/** One of the six areas the stats are grouped into: the average of its stats that have data. */
data class Category(val key: String, val name: String, val score: Int?, val grade: String?, val stats: List<String>)

/** overall: the average of the categories that have data. categories is empty from a server older than them. */
data class CharacterSheet(
    val date: String,
    val overall: Int?,
    val overallGrade: String?,
    val stats: List<Stat>,
    val categories: List<Category> = emptyList(),
) {
    fun statsOf(category: Category) = category.stats.mapNotNull { code -> stats.firstOrNull { it.code == code } }
}

/** One day of history: each stat's and each category's score (null = no data that day). */
data class HistoryDay(val date: String, val stats: Map<String, Int?>, val categories: Map<String, Int?>)

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

/** A big one-off achievement; its XP is shared out over all your skills when you complete it. */
data class Milestone(val key: String, val description: String, val xp: Int, val completed: Boolean)

/** A to-do that earns XP for one skill: 1.5x on time, 1x up to a week late, 0.5x after that. */
data class Quest(
    val id: Int,
    val task: String,
    val skillId: Int,
    val baseXp: Int,
    val deadline: String,
    val completed: Boolean,
    val completedOn: String?,
)

/** Paid work: its value counts toward this month's income (Wealth) when completed. */
data class Project(val id: Int, val name: String, val value: Int, val deadline: String, val completed: Boolean, val completedOn: String?)

/** A life area ("Category - Skill") with its own level: 150 XP a level. */
data class Skill(val id: Int, val name: String, val level: Int, val xp: Int) {
    val category get() = name.substringBefore(" - ", "").ifEmpty { name }
    val shortName get() = name.substringAfter(" - ", name)
    val progress get() = (xp % XP_PER_LEVEL) / XP_PER_LEVEL.toFloat()

    companion object {
        const val XP_PER_LEVEL = 150
        /** Habit and social XP land in these by name, so the server won't rename or delete them */
        val PROTECTED = setOf("Health - Exercise", "Health - Sleep", "Health - Hygiene", "Social Balance")
    }
}

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
data class DayLog(val auto: JSONObject, val manual: JSONObject, val merged: JSONObject, val date: String = "") {
    fun phone(field: LogField): Any? = auto.optJSONObject(field.section)?.opt(field.key)?.takeUnless { it == JSONObject.NULL }
    fun typed(field: LogField): Any? = manual.optJSONObject(field.section)?.opt(field.key)?.takeUnless { it == JSONObject.NULL }
    /** What the stats use: what you typed, else what the phone sent */
    fun value(field: LogField): Any? = typed(field) ?: phone(field)
    /** A value by section and key, typed-in first, for values the catalog doesn't list */
    fun raw(section: String, key: String): Any? =
        (manual.optJSONObject(section)?.opt(key) ?: auto.optJSONObject(section)?.opt(key))?.takeUnless { it == JSONObject.NULL }
    val isEmpty get() = auto.length() == 0 && manual.length() == 0
}

/**
 * One value a day can hold, from the server's catalog. kind: decimal / whole / yesno / time;
 * source: phone / checkin / both; feeds: the stat codes whose formulas read it.
 */
data class LogField(
    val section: String,
    val key: String,
    val label: String,
    val unit: String,
    val kind: String,
    val source: String,
    val feeds: List<String>,
)

data class FieldCatalog(val sections: List<Pair<String, String>>, val fields: List<LogField>)

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
    categories = json.optJSONArray("categories")?.map { c ->
        val codes = c.getJSONArray("stats")
        Category(c.getString("key"), c.getString("name"), c.intOrNull("score"), c.stringOrNull("grade"), (0 until codes.length()).map(codes::getString))
    }.orEmpty(),
)

private fun JSONObject?.scores(): Map<String, Int?> =
    this?.keys()?.asSequence()?.associateWith { if (isNull(it)) null else getInt(it) }.orEmpty()

fun parseHistoryDay(json: JSONObject) =
    HistoryDay(json.getString("date"), json.optJSONObject("scores").scores(), json.optJSONObject("categories").scores())

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

fun parseMilestone(json: JSONObject) =
    Milestone(json.getString("key"), json.getString("description"), json.getInt("xp_reward"), json.getBoolean("completed"))

fun parseQuest(json: JSONObject) = Quest(
    id = json.getInt("id"),
    task = json.getString("task"),
    skillId = json.getInt("area_id"),
    baseXp = json.getInt("base_xp"),
    deadline = json.getString("deadline"),
    completed = json.getBoolean("completed"),
    completedOn = json.stringOrNull("completion_date"),
)

fun parseProject(json: JSONObject) = Project(
    id = json.getInt("id"),
    name = json.getString("name"),
    value = json.getInt("value"),
    deadline = json.getString("deadline"),
    completed = json.getBoolean("completed"),
    completedOn = json.stringOrNull("completion_date"),
)

fun parseSkill(json: JSONObject) = Skill(json.getInt("id"), json.getString("name"), json.getInt("level"), json.getInt("xp"))

fun parseIncome(json: JSONObject) = Income(json.getInt("monthly_goal"), json.getInt("current_month_earnings"))

fun parseDayLog(json: JSONObject) =
    DayLog(json.getJSONObject("auto"), json.getJSONObject("manual"), json.getJSONObject("merged"), json.optString("date"))

fun parseFieldCatalog(json: JSONObject) = FieldCatalog(
    sections = json.getJSONArray("sections").map { it.getString("key") to it.getString("title") },
    fields = json.getJSONArray("fields").map { f ->
        val feeds = f.getJSONArray("feeds")
        LogField(
            f.getString("section"), f.getString("key"), f.getString("label"), f.getString("unit"),
            f.getString("kind"), f.getString("source"), (0 until feeds.length()).map(feeds::getString),
        )
    },
)

// ---- Questionnaire (questions come from the server, so both apps ask the same thing)

/** kind: single / multi / scale / number / rank / text */
data class QQuestion(
    val id: String,
    val text: String,
    val kind: String,
    val options: List<Pair<String, String>>,
    val optional: Boolean,
    val max: Int?,
    val min: Int?,
    val unit: String,
    val minLabel: String,
    val maxLabel: String,
)

data class QSection(val key: String, val title: String, val intro: String, val questions: List<QQuestion>)

data class PlanStep(
    val id: String,
    val category: String,
    val categoryName: String,
    val title: String,
    val why: String,
    val firstStep: String,
    val goal: JSONObject?,  // a goal to create in one tap, as /goals takes it
)

data class Priority(val key: String, val name: String, val level: Int, val tracked: Boolean)

data class QResults(val priorities: List<Priority>, val focus: List<String>, val plan: List<PlanStep>, val tips: List<String>)

data class Attempt(val id: Int, val createdAt: String, val answers: JSONObject, val results: QResults)

data class Questionnaire(val sections: List<QSection>, val prefill: JSONObject, val latest: Attempt?)

private fun JSONArray.strings() = (0 until length()).map(::getString)

fun parseAttempt(json: JSONObject): Attempt {
    val r = json.getJSONObject("results")
    return Attempt(
        id = json.getInt("id"),
        createdAt = json.getString("created_at"),
        answers = json.getJSONObject("answers"),
        results = QResults(
            priorities = r.getJSONArray("priorities").map { Priority(it.getString("key"), it.getString("name"), it.getInt("level"), it.getBoolean("tracked")) },
            focus = r.getJSONArray("focus").strings(),
            plan = r.getJSONArray("plan").map {
                PlanStep(
                    it.getString("id"), it.getString("category"), it.getString("category_name"), it.getString("title"),
                    it.getString("why"), it.getString("first_step"), it.optJSONObject("goal"),
                )
            },
            tips = r.getJSONArray("tips").strings(),
        ),
    )
}

fun parseQuestionnaire(json: JSONObject) = Questionnaire(
    sections = json.getJSONArray("sections").map { s ->
        QSection(
            s.getString("key"), s.getString("title"), s.optString("intro"),
            s.getJSONArray("questions").map { q ->
                QQuestion(
                    id = q.getString("id"),
                    text = q.getString("text"),
                    kind = q.getString("kind"),
                    options = q.optJSONArray("options")?.map { it.getString("value") to it.getString("label") }.orEmpty(),
                    optional = q.optBoolean("optional"),
                    max = if (q.has("max")) q.getInt("max") else null,
                    min = if (q.has("min")) q.getInt("min") else null,
                    unit = q.optString("unit"),
                    minLabel = q.optString("min_label"),
                    maxLabel = q.optString("max_label"),
                )
            },
        )
    },
    prefill = json.optJSONObject("prefill") ?: JSONObject(),
    latest = json.optJSONObject("latest")?.let(::parseAttempt),
)
