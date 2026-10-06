package com.liferpg.sync.ui

import com.liferpg.sync.Stat

/** A stat's parts grouped for its detail page. */
data class StatCategory(
    val title: String,
    val parts: List<Part>,
    val isDrain: Boolean = false,
) {
    /** One component (points earned of a maximum) or penalty (points lost). */
    data class Part(val name: String, val earned: Double?, val max: Double, val note: String, val tip: String?)

    val earned get() = parts.sumOf { it.earned ?: 0.0 }
    val max get() = parts.filter { it.earned != null || isDrain }.sumOf { it.max }
    val hasData get() = parts.any { it.earned != null }
}

/**
 * Which category each component belongs to, by stat. Names match the server's component names;
 * anything unlisted lands in "Other" so a new server-side component still shows up.
 */
private val CATEGORIES: Map<String, List<Pair<String, (String) -> Boolean>>> = mapOf(
    "MP" to listOf(
        "😴 Sleep" to { n -> n.startsWith("Sleep") },
        "💼 Work" to { n -> n == "Deep work" },
        "🏃 Body" to { n -> n == "Physical activity" || n == "Outdoors" },
        "🧠 Mind" to { n -> n == "Meditation" },
    ),
    "PS" to listOf("💪 Strength" to { _ -> true }),
    "STA" to listOf("🏃 Cardio" to { _ -> true }),
    "H" to listOf(
        "🍽️ Eating" to { n -> n in setOf("Calories on target", "Protein", "Meals logged") },
        "⚖️ Body" to { n -> n == "Weight trend" },
    ),
    "INT" to listOf("📚 Learning" to { _ -> true }),
    "DIS" to listOf(
        "✅ Habits" to { n -> n in setOf("Daily check-ins", "Slept 7-9h", "Showered") || n.endsWith("push-ups") },
        "📋 Tasks" to { n -> n == "Tasks done on time" },
        "🍽️ Eating" to { n -> n == "Ate within calories" },
    ),
    "FOC" to listOf(
        "📱 Feeds" to { n -> n == "Reels / Shorts / TikTok" || n == "Social feeds" },
        "🔓 Phone habits" to { n -> n == "Unlocks" || n == "Phone after midnight" },
        "⏱️ Screen time" to { n -> n == "Total screen time" },
    ),
    "SOC" to listOf("👥 People" to { _ -> true }),
    "WLT" to listOf("💰 Money" to { _ -> true }),
)

/** Short, concrete advice for a part that isn't full yet. */
private val TIPS = mapOf(
    "Sleep last night" to "Aim for 7–9 hours tonight.",
    "Sleep debt (7 days)" to "Pay it back with an earlier night or two.",
    "Sleep regularity" to "Fall asleep within 30 minutes of the same time every night.",
    "Sleep quality" to "No caffeine 6h before bed, no phone in the last hour, go easy on alcohol.",
    "Deep work" to "Block 2–4 hours of focused work with notifications off.",
    "Physical activity" to "A 30-minute brisk walk or 8,000 steps.",
    "Outdoors" to "20 minutes outside, in nature if you can.",
    "Meditation" to "10 minutes of meditation.",
    "Reels / Shorts / TikTok" to "Keep reels under 15 minutes. Goggins mode can nag you off them.",
    "Passive video over 2h" to "Cap videos and series at 2 hours.",
    "Gaming over 2h" to "Cap gaming at 2 hours.",
    "Overwork today" to "Past 10 hours, output drops. Stop earlier and sleep.",
    "Overwork this week" to "Past ~50 hours a week, extra hours stop paying off.",
    "Max push-up test" to "Do a max push-up set once a week and log it.",
    "Training consistency" to "Strength training at least 2 days a week.",
    "Steps (7-day avg)" to "8,000–10,000 steps a day.",
    "Cardio minutes / week" to "150–300 minutes of brisk activity a week.",
    "Calories on target" to "Stay between 75% and 110% of your calorie target.",
    "Protein" to "Hit your protein target: 1.6 g per kg of body weight.",
    "Meals logged" to "Log all 3 meals: snap a photo each time.",
    "Weight trend" to "Weigh in weekly; 0.5–1% of body weight a week is the healthy pace.",
    "Learning (28 days)" to "About an hour of learning a day adds up fast.",
    "Daily check-ins" to "Do the 30-second check-in every evening.",
    "Slept 7-9h" to "7–9 hours every night.",
    "Showered" to "Shower daily and tick it in the check-in.",
    "Tasks done on time" to "Finish tasks before their deadline.",
    "Ate within calories" to "Stay within your calorie target.",
    "Social feeds" to "30 minutes of social feeds a day is plenty.",
    "Unlocks" to "Put the phone in another room while you work.",
    "Phone after midnight" to "Phone away by midnight.",
    "Total screen time" to "Under 2–3 hours of phone time a day.",
    "Meaningful contacts / week" to "3–4 real conversations a week, in person or on a call.",
    "Monthly income goal" to "Log what you earn so Wealth can track it.",
)

private fun tipFor(name: String) = TIPS[name] ?: if (name.endsWith("push-ups")) "Hit your daily push-up target." else null

/** The stat's components and penalties, grouped; penalties become a "Drains" category. */
fun categoriesOf(stat: Stat): List<StatCategory> {
    val rules = CATEGORIES[stat.code].orEmpty()
    val grouped = linkedMapOf<String, MutableList<StatCategory.Part>>()
    rules.forEach { (title, _) -> grouped[title] = mutableListOf() }
    for (c in stat.components) {
        val title = rules.firstOrNull { (_, matches) -> matches(c.name) }?.first ?: "Other"
        val earned = c.score?.let { it * c.weight }
        val tip = if (c.score != null && c.score < 1) tipFor(c.name) else null
        grouped.getOrPut(title) { mutableListOf() } += StatCategory.Part(c.name, earned, c.weight, c.note, tip)
    }
    val categories = grouped.filterValues { it.isNotEmpty() }.map { (title, parts) -> StatCategory(title, parts) }
    val drains = stat.penalties.map { StatCategory.Part(it.name, -it.points, it.points, it.note, tipFor(it.name)) }
    return if (drains.isEmpty()) categories else categories + StatCategory("📉 Drains", drains, isDrain = true)
}
