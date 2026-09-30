package com.liferpg.sync.ui

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.animateContentSize
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.liferpg.sync.Api
import com.liferpg.sync.DayMeals
import com.liferpg.sync.Meal
import com.liferpg.sync.MealPhotos
import com.liferpg.sync.widget.WidgetCache
import kotlinx.coroutines.launch
import org.json.JSONArray
import org.json.JSONObject
import java.time.LocalDate

/**
 * Meals: snap a photo (or share one from the camera or gallery) and the server's AI reads the food,
 * portions and calories. [sharedPhoto] is a photo shared into the app, logged as soon as the tab opens.
 */
@Composable
fun MealsScreen(api: Api, sharedPhoto: Uri? = null, onSharedPhotoUsed: () -> Unit = {}) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val levelState = LocalLevel.current
    val day = rememberLoader { api.meals(LocalDate.now()) }
    fun changed() {
        day.reload()
        scope.launch {
            runCatching { WidgetCache.refresh(context) }
            levelState?.refresh()
        }
    }
    var busy by remember { mutableStateOf<String?>(null) }
    var message by remember { mutableStateOf<String?>(null) }
    var quickAdd by remember { mutableStateOf(false) }
    var cameraUri by remember { mutableStateOf<Uri?>(null) }

    fun logPhoto(uri: Uri) {
        busy = "Reading your meal…"
        message = null
        scope.launch {
            message = try {
                val photo = MealPhotos.prepare(context, uri)
                val meal = api.logMealPhoto(photo.jpeg, photo.takenAt, note = null)
                changed()
                "✅ ${meal.name}: ${meal.kcal.toInt()} kcal"
            } catch (e: Exception) {
                "❌ ${e.message}"
            }
            busy = null
        }
    }

    val camera = rememberLauncherForActivityResult(ActivityResultContracts.TakePicture()) { saved ->
        cameraUri?.takeIf { saved }?.let(::logPhoto)
    }
    val gallery = rememberLauncherForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri -> uri?.let(::logPhoto) }

    LaunchedEffect(sharedPhoto) {
        sharedPhoto?.let {
            logPhoto(it)
            onSharedPhotoUsed()
        }
    }

    Column(Modifier.verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Text("MEALS", style = MaterialTheme.typography.headlineLarge, color = Rpg.Accent)

        when (val load = day.value) {
            is Load.Ready -> Totals(load.value)
            is Load.Failed -> Text(load.message, color = Rpg.Muted)
            Load.Loading -> Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) { CircularProgressIndicator(color = Rpg.Accent) }
        }

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(
                onClick = { MealPhotos.newCameraUri(context).also { cameraUri = it; camera.launch(it) } },
                enabled = busy == null,
                modifier = Modifier.weight(1f),
            ) { Text("📷 Snap a meal") }
            OutlinedButton(
                onClick = { gallery.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)) },
                enabled = busy == null,
                modifier = Modifier.weight(1f),
            ) { Text("🖼 From gallery") }
        }
        OutlinedButton(onClick = { quickAdd = true }, enabled = busy == null, modifier = Modifier.fillMaxWidth()) { Text("✍ Quick add") }
        Text("Tip: in the Samsung camera or gallery, Share → Life RPG Sync logs a meal photo too.", color = Rpg.Muted, fontSize = 12.sp)

        busy?.let {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                CircularProgressIndicator(Modifier.size(20.dp), color = Rpg.Accent, strokeWidth = 2.dp)
                Text(it, color = Rpg.Muted)
            }
        }
        message?.let { Text(it, color = if (it.startsWith("✅")) Rpg.Good else Rpg.Bad) }

        (day.value as? Load.Ready)?.value?.meals?.forEach { meal ->
            MealCard(api, meal, onChanged = ::changed)
        }
    }

    if (quickAdd) QuickAddDialog(api, onDone = { quickAdd = false; changed() }, onCancel = { quickAdd = false })
}

@Composable
internal fun Totals(day: DayMeals) {
    val target = day.targets.calories
    HudCard {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(16.dp)) {
            CalorieRing(day.kcal, target)
            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                if (target != null) {
                    val left = target - day.kcal.toInt()
                    Text(if (left >= 0) "$left kcal left" else "${-left} kcal over", fontWeight = FontWeight.Black, fontSize = 20.sp,
                        color = if (left >= 0) Rpg.Text else Rpg.Bad)
                    Text(
                        when {
                            day.targets.adjustment < 0 -> "Target $target · losing (${day.targets.adjustment} kcal/day)"
                            day.targets.adjustment > 0 -> "Target $target · gaining (+${day.targets.adjustment} kcal/day)"
                            else -> "Target $target · maintaining"
                        },
                        color = Rpg.Muted, fontSize = 12.sp,
                    )
                } else {
                    Text("${day.kcal.toInt()} kcal today", fontWeight = FontWeight.Black, fontSize = 20.sp)
                    Text("Add your ${day.targets.missing.joinToString(", ")} (Settings › profile, weight in Check-in) to get a calorie target.",
                        color = Rpg.Muted, fontSize = 12.sp)
                }
                day.targets.protein?.let { protein ->
                    Text("Protein ${day.protein.toInt()} / $protein g", fontSize = 13.sp)
                    Meter((day.protein / protein).toFloat(), statColor("H"))
                }
            }
        }
    }
}

/** Eaten against target as a ring; past the target the overflow is drawn in red. */
@Composable
private fun CalorieRing(eaten: Double, target: Int?) {
    Box(Modifier.size(104.dp), contentAlignment = Alignment.Center) {
        Canvas(Modifier.size(104.dp)) {
            val stroke = 10.dp.toPx()
            val inset = stroke / 2
            val arc = Size(size.width - stroke, size.height - stroke)
            drawArc(Rpg.SurfaceHigh, 0f, 360f, false, Offset(inset, inset), arc, style = Stroke(stroke))
            if (target != null && target > 0) {
                val fraction = (eaten / target).toFloat()
                drawArc(statColor("H"), -90f, 360f * fraction.coerceAtMost(1f), false, Offset(inset, inset), arc, style = Stroke(stroke, cap = StrokeCap.Round))
                if (fraction > 1f) {
                    drawArc(Rpg.Bad, -90f, 360f * (fraction - 1f).coerceAtMost(1f), false, Offset(inset, inset), arc, style = Stroke(stroke, cap = StrokeCap.Round))
                }
            }
        }
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text(eaten.toInt().toString(), fontWeight = FontWeight.Black, fontSize = 22.sp)
            Text("kcal", color = Rpg.Muted, fontSize = 11.sp)
        }
    }
}

@Composable
internal fun MealCard(api: Api, meal: Meal, onChanged: () -> Unit) {
    val scope = rememberCoroutineScope()
    var open by remember { mutableStateOf(false) }
    var editing by remember { mutableStateOf(false) }
    var confirmDelete by remember { mutableStateOf(false) }

    HudCard(Modifier.clickable { open = !open }.animateContentSize()) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text("${if (meal.source == "photo") "📷" else "✍"} ${meal.mealType.replaceFirstChar { it.uppercase() }} · ${meal.eatenAt.substring(11, 16)}",
                    color = Rpg.Muted, fontSize = 12.sp)
                Text(meal.name, fontWeight = FontWeight.Bold)
            }
            Text("${meal.kcal.toInt()}", fontWeight = FontWeight.Black, fontSize = 20.sp)
            Text(" kcal", color = Rpg.Muted, fontSize = 12.sp)
        }
        Text("P ${meal.protein.toInt()} g · C ${meal.carbs.toInt()} g · F ${meal.fat.toInt()} g", color = Rpg.Muted, fontSize = 12.sp)
        if (open) {
            meal.items.forEach { item ->
                Row {
                    Text("• ${item.name}${item.grams?.let { " (${it.toInt()} g)" } ?: ""}", Modifier.weight(1f), fontSize = 13.sp)
                    Text("${item.kcal.toInt()} kcal", fontSize = 13.sp)
                }
            }
            meal.confidence?.let { Text("AI's confidence: ${(it * 100).toInt()}%. Tap Fix if a portion looks wrong.", color = Rpg.Muted, fontSize = 11.sp) }
            Row(horizontalArrangement = Arrangement.End, modifier = Modifier.fillMaxWidth()) {
                TextButton(onClick = { editing = true }) { Text("Fix") }
                TextButton(onClick = { confirmDelete = true }) { Text("Delete", color = Rpg.Bad) }
            }
        }
    }

    if (editing) FixMealDialog(api, meal, onDone = { editing = false; onChanged() }, onCancel = { editing = false })
    if (confirmDelete) {
        AlertDialog(
            onDismissRequest = { confirmDelete = false },
            title = { Text("Delete meal?") },
            text = { Text("${meal.name} (${meal.kcal.toInt()} kcal)") },
            confirmButton = {
                TextButton(onClick = {
                    confirmDelete = false
                    scope.launch { runCatching { api.deleteMeal(meal.id) }; onChanged() }
                }) { Text("Delete", color = Rpg.Bad) }
            },
            dismissButton = { TextButton(onClick = { confirmDelete = false }) { Text("Cancel") } },
        )
    }
}

/** Correct each item's calories and protein; the meal's totals follow on the server. */
@Composable
private fun FixMealDialog(api: Api, meal: Meal, onDone: () -> Unit, onCancel: () -> Unit) {
    val scope = rememberCoroutineScope()
    val kcal = remember { mutableStateListOf(*meal.items.map { it.kcal.toInt().toString() }.toTypedArray()) }
    val protein = remember { mutableStateListOf(*meal.items.map { it.protein.toInt().toString() }.toTypedArray()) }
    var error by remember { mutableStateOf<String?>(null) }

    AlertDialog(
        onDismissRequest = onCancel,
        title = { Text("Fix ${meal.name}") },
        text = {
            Column(Modifier.verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                meal.items.forEachIndexed { i, item ->
                    Text(item.name, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        NumberBox(kcal[i], { kcal[i] = it }, "kcal", Modifier.weight(1f))
                        NumberBox(protein[i], { protein[i] = it }, "protein g", Modifier.weight(1f))
                    }
                }
                error?.let { Text("❌ $it", color = Rpg.Bad, fontSize = 13.sp) }
            }
        },
        confirmButton = {
            TextButton(onClick = {
                scope.launch {
                    error = runCatching {
                        val items = JSONArray()
                        meal.items.forEachIndexed { i, item ->
                            items.put(JSONObject()
                                .put("name", item.name)
                                .put("grams", item.grams ?: JSONObject.NULL)
                                .put("kcal", kcal[i].toDoubleOrNull() ?: error("${item.name}: calories must be a number"))
                                .put("protein", protein[i].toDoubleOrNull() ?: error("${item.name}: protein must be a number"))
                                .put("carbs", item.carbs)
                                .put("fat", item.fat))
                        }
                        api.updateMeal(meal.id, JSONObject().put("items", items))
                        onDone()
                    }.exceptionOrNull()?.message
                }
            }) { Text("Save") }
        },
        dismissButton = { TextButton(onClick = onCancel) { Text("Cancel") } },
    )
}

@Composable
private fun QuickAddDialog(api: Api, onDone: () -> Unit, onCancel: () -> Unit) {
    val scope = rememberCoroutineScope()
    var name by remember { mutableStateOf("") }
    var kcal by remember { mutableStateOf("") }
    var protein by remember { mutableStateOf("") }
    var error by remember { mutableStateOf<String?>(null) }

    AlertDialog(
        onDismissRequest = onCancel,
        title = { Text("Quick add") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(name, { name = it }, label = { Text("What (e.g. Protein shake)") }, singleLine = true)
                NumberBox(kcal, { kcal = it }, "Calories", Modifier.fillMaxWidth())
                NumberBox(protein, { protein = it }, "Protein g (optional)", Modifier.fillMaxWidth())
                error?.let { Text("❌ $it", color = Rpg.Bad, fontSize = 13.sp) }
            }
        },
        confirmButton = {
            TextButton(onClick = {
                scope.launch {
                    error = runCatching {
                        val title = name.trim().ifEmpty { "Quick add" }
                        val item = JSONObject().put("name", title)
                            .put("kcal", kcal.toDoubleOrNull() ?: error("Calories must be a number"))
                            .put("protein", protein.toDoubleOrNull() ?: 0.0)
                        api.logMeal(JSONObject().put("name", title).put("items", JSONArray().put(item)))
                        onDone()
                    }.exceptionOrNull()?.message
                }
            }) { Text("Add") }
        },
        dismissButton = { TextButton(onClick = onCancel) { Text("Cancel") } },
    )
}

@Composable
private fun NumberBox(value: String, onChange: (String) -> Unit, label: String, modifier: Modifier) {
    OutlinedTextField(
        value, onChange, label = { Text(label) }, singleLine = true, modifier = modifier,
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
    )
}
