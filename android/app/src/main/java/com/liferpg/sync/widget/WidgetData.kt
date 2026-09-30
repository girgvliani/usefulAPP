package com.liferpg.sync.widget

import android.content.Context
import androidx.core.content.edit
import androidx.glance.appwidget.updateAll
import com.liferpg.sync.Api
import com.liferpg.sync.CharacterSheet
import com.liferpg.sync.Level
import com.liferpg.sync.Settings
import com.liferpg.sync.Streaks
import com.liferpg.sync.parseCharacterSheet
import com.liferpg.sync.parseLevel
import com.liferpg.sync.parseStreaks
import org.json.JSONObject
import java.time.LocalTime
import java.time.format.DateTimeFormatter

/** What the widget shows: the last streaks and character sheet fetched from the server. */
data class WidgetData(val streaks: Streaks?, val sheet: CharacterSheet?, val level: Level?, val updated: String?)

/**
 * The widget can't wait on the network, so it always draws the last saved copy. [refresh] fetches a
 * new one (hourly with the sync, when the app opens, and from the widget's ↻) and redraws every widget.
 */
object WidgetCache {
    private const val PREFS = "widget"

    fun load(context: Context): WidgetData {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        fun <T> parse(key: String, parser: (JSONObject) -> T): T? =
            prefs.getString(key, null)?.let { runCatching { parser(JSONObject(it)) }.getOrNull() }
        return WidgetData(
            parse("streaks", ::parseStreaks), parse("sheet", ::parseCharacterSheet), parse("level", ::parseLevel), prefs.getString("updated", null),
        )
    }

    suspend fun refresh(context: Context) {
        val settings = Settings(context)
        if (settings.isConfigured) {
            val api = Api(settings)
            val streaks = api.streaksJson()
            val sheet = api.characterJson()
            val level = runCatching { api.levelJson() }.getOrNull()  // older servers don't have it
            context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit {
                putString("streaks", streaks)
                putString("sheet", sheet)
                level?.let { putString("level", it) }
                putString("updated", LocalTime.now().format(DateTimeFormatter.ofPattern("HH:mm")))
            }
        }
        LifeRpgWidget().updateAll(context)
    }
}
