package com.liferpg.sync.ui

import android.Manifest
import android.content.pm.PackageManager
import android.media.AudioManager
import android.media.ToneGenerator
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.annotation.OptIn
import androidx.camera.core.CameraSelector
import androidx.camera.core.ExperimentalGetImage
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.Preview
import androidx.camera.core.resolutionselector.AspectRatioStrategy
import androidx.camera.core.resolutionselector.ResolutionSelector
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.pose.Pose
import com.google.mlkit.vision.pose.PoseDetection
import com.google.mlkit.vision.pose.PoseLandmark
import com.google.mlkit.vision.pose.defaults.PoseDetectorOptions
import com.liferpg.sync.Api
import com.liferpg.sync.Exercise
import com.liferpg.sync.Phase
import com.liferpg.sync.RepCounter
import kotlinx.coroutines.launch
import java.time.LocalDate
import java.util.concurrent.Executors

/** Landmarks as seen in the upright camera image, plus the image's size and whether it's mirrored */
internal data class PoseFrame(val points: Map<Int, Offset>, val width: Int, val height: Int, val mirrored: Boolean, val tracked: List<Int>)

/** The limbs drawn over the camera image */
private val BONES = listOf(11 to 12, 11 to 13, 13 to 15, 12 to 14, 14 to 16, 11 to 23, 12 to 24, 23 to 24, 23 to 25, 25 to 27, 24 to 26, 26 to 28)

/**
 * Counts push-ups, squats or sit-ups with the camera. The phone finds your body (ML Kit pose detection,
 * on the phone: no video is recorded or sent anywhere) and counts each bend-and-straighten.
 */
@Composable
fun RepCounterScreen(api: Api) {
    val context = LocalContext.current
    var granted by remember {
        mutableStateOf(ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED)
    }
    val ask = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted = it }
    var exercise by remember { mutableStateOf(Exercise.Pushups) }
    var front by remember { mutableStateOf(true) }
    val counter = remember(exercise) { RepCounter(exercise) }
    var count by remember(exercise) { mutableIntStateOf(0) }
    var phase by remember(exercise) { mutableStateOf(Phase.Unknown) }
    var angle by remember(exercise) { mutableStateOf<Double?>(null) }
    var frame by remember { mutableStateOf<PoseFrame?>(null) }
    var message by remember { mutableStateOf<String?>(null) }
    val levelState = LocalLevel.current
    val scope = rememberCoroutineScope()
    val pop = remember { Animatable(1f) }
    val beep = remember { runCatching { ToneGenerator(AudioManager.STREAM_MUSIC, 70) }.getOrNull() }
    DisposableEffect(Unit) { onDispose { beep?.release() } }
    val view = LocalView.current
    DisposableEffect(Unit) {
        view.keepScreenOn = true  // no dimming mid-set
        onDispose { view.keepScreenOn = false }
    }
    LaunchedEffect(count) {
        if (count > 0) {
            pop.snapTo(1.35f)
            pop.animateTo(1f, tween(250))
        }
    }

    Column(Modifier.verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("REP COUNTER", style = MaterialTheme.typography.headlineLarge, color = Rpg.Accent)
        ChoiceChips(Exercise.entries.map { it to "${it.icon} ${it.label}" }, exercise) { exercise = it; message = null }
        Text(exercise.tip, color = Rpg.Muted, fontSize = 13.sp)
        if (!granted) {
            HudCard {
                Text("The counter needs the camera. It watches your body on the phone itself: nothing is recorded or uploaded.", fontSize = 14.sp)
                Button(onClick = { ask.launch(Manifest.permission.CAMERA) }) { Text("Allow the camera") }
            }
        } else {
            Box(Modifier.fillMaxWidth().aspectRatio(3f / 4f).clip(RoundedCornerShape(20.dp)).background(Color.Black)) {
                CameraPose(front) { pose, w, h ->
                    val result = poseAngle(pose, exercise)
                    val done = counter.update(result?.first)
                    count = counter.count
                    phase = counter.phase
                    angle = counter.angle
                    frame = PoseFrame(
                        pose.allPoseLandmarks.filter { it.inFrameLikelihood >= RepCounter.MIN_LIKELIHOOD }
                            .associate { it.landmarkType to Offset(it.position.x, it.position.y) },
                        w, h, front, result?.second.orEmpty(),
                    )
                    if (done) beep?.startTone(ToneGenerator.TONE_PROP_BEEP, 120)
                }
                frame?.let { PoseOverlay(it) }
                RepHud(count, phase, angle, exercise, Modifier.align(Alignment.TopStart), pop.value)
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = { front = !front }) { Text(if (front) "Back camera" else "Front camera") }
                OutlinedButton(onClick = { counter.reset(); count = 0; phase = Phase.Unknown; message = null }) { Text("Reset") }
            }
            Button(
                enabled = count > 0,
                onClick = {
                    val reps = count
                    scope.launch {
                        runCatching { api.addReps(LocalDate.now(), exercise.key, reps) }
                            .onSuccess {
                                message = "✓ Added $reps ${exercise.label.lowercase()} to today"
                                counter.reset(); count = 0; phase = Phase.Unknown
                                levelState?.refresh()
                            }
                            .onFailure { message = "❌ ${it.message}" }
                    }
                },
                modifier = Modifier.fillMaxWidth(),
            ) { Text(if (count > 0) "Add $count ${exercise.label.lowercase()} to today" else "Do a rep to start") }
        }
        message?.let { Text(it, color = if (it.startsWith("✓")) Rpg.Good else Rpg.Bad, fontSize = 13.sp) }
        Text(
            "Counts a rep each time the ${when (exercise) { Exercise.Pushups -> "elbow"; Exercise.Squats -> "knee"; Exercise.Situps -> "hip" }} bends past " +
                "${exercise.flexedBelow.toInt()}° and straightens past ${exercise.extendedAbove.toInt()}° again. Sets go into today's check-in " +
                "and count toward achievements (Seen by the Machine, Verified, Leg Day).",
            color = Rpg.Muted, fontSize = 12.sp,
        )
    }
}

/** The count, the phase and an angle gauge, over the camera image */
@Composable
internal fun RepHud(count: Int, phase: Phase, angle: Double?, exercise: Exercise, modifier: Modifier = Modifier, scale: Float = 1f) {
    Column(modifier.padding(14.dp).background(Color.Black.copy(alpha = 0.55f), RoundedCornerShape(16.dp)).padding(horizontal = 14.dp, vertical = 8.dp)) {
        Text("$count", Modifier.scale(scale), color = Color.White, fontWeight = FontWeight.Black, fontSize = 64.sp, lineHeight = 66.sp)
        Text(
            when {
                angle == null -> "Step into view"
                phase == Phase.Flexed -> "DOWN ⬇"
                phase == Phase.Extended -> "UP ⬆"
                else -> "Ready"
            },
            color = if (angle == null) Rpg.Bad else Rpg.Accent, fontWeight = FontWeight.Black, fontSize = 14.sp,
        )
        angle?.let {
            Text("${it.toInt()}° (${exercise.flexedBelow.toInt()}–${exercise.extendedAbove.toInt()})", color = Color.White.copy(alpha = 0.8f), fontSize = 11.sp, textAlign = TextAlign.Start)
        }
    }
}

/** The body's limbs over the image; the joints being counted in the accent colour */
@Composable
internal fun PoseOverlay(frame: PoseFrame) {
    Canvas(Modifier.fillMaxSize()) {
        // The preview fills the box (centre crop), so scale the image the same way
        val scale = maxOf(size.width / frame.width, size.height / frame.height)
        val dx = (size.width - frame.width * scale) / 2
        val dy = (size.height - frame.height * scale) / 2
        fun map(p: Offset): Offset {
            val x = p.x * scale + dx
            return Offset(if (frame.mirrored) size.width - x else x, p.y * scale + dy)
        }
        BONES.forEach { (a, b) ->
            val pa = frame.points[a] ?: return@forEach
            val pb = frame.points[b] ?: return@forEach
            val hot = a in frame.tracked && b in frame.tracked
            drawLine(if (hot) Rpg.Accent else Color.White.copy(alpha = 0.7f), map(pa), map(pb), if (hot) 9f else 5f, StrokeCap.Round)
        }
        frame.tracked.forEach { id -> frame.points[id]?.let { drawCircle(Rpg.Accent, 12f, map(it)) } }
    }
}

/** The counted joint's angle on the side the camera sees best, and which landmarks those are (null: not in view) */
internal fun poseAngle(pose: Pose, exercise: Exercise): Pair<Double, List<Int>>? {
    fun side(ids: Triple<Int, Int, Int>): Pair<Float, List<PoseLandmark>>? {
        val marks = listOf(ids.first, ids.second, ids.third).map { pose.getPoseLandmark(it) ?: return null }
        return marks.minOf { it.inFrameLikelihood } to marks
    }
    val best = listOfNotNull(side(exercise.left), side(exercise.right)).maxByOrNull { it.first } ?: return null
    if (best.first < RepCounter.MIN_LIKELIHOOD) return null
    val (a, b, c) = best.second
    return RepCounter.jointAngle(a.position.x, a.position.y, b.position.x, b.position.y, c.position.x, c.position.y) to best.second.map { it.landmarkType }
}

/** The camera preview, with every frame run through ML Kit pose detection (on the phone) */
@OptIn(ExperimentalGetImage::class)
@Composable
private fun CameraPose(front: Boolean, onPose: (Pose, Int, Int) -> Unit) {
    val context = LocalContext.current
    val lifecycle = LocalLifecycleOwner.current
    val detector = remember {
        PoseDetection.getClient(PoseDetectorOptions.Builder().setDetectorMode(PoseDetectorOptions.STREAM_MODE).build())
    }
    val executor = remember { Executors.newSingleThreadExecutor() }
    val previewView = remember { PreviewView(context).apply { scaleType = PreviewView.ScaleType.FILL_CENTER } }
    DisposableEffect(front) {
        val providerFuture = ProcessCameraProvider.getInstance(context)
        var provider: ProcessCameraProvider? = null
        providerFuture.addListener({
            val p = providerFuture.get()
            provider = p
            val ratio = ResolutionSelector.Builder().setAspectRatioStrategy(AspectRatioStrategy.RATIO_4_3_FALLBACK_AUTO_STRATEGY).build()
            val preview = Preview.Builder().setResolutionSelector(ratio).build().also { it.surfaceProvider = previewView.surfaceProvider }
            val analysis = ImageAnalysis.Builder()
                .setResolutionSelector(ratio)
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .build()
            analysis.setAnalyzer(executor) { proxy ->
                val media = proxy.image
                if (media == null) {
                    proxy.close()
                    return@setAnalyzer
                }
                val rotation = proxy.imageInfo.rotationDegrees
                val (w, h) = if (rotation % 180 == 0) proxy.width to proxy.height else proxy.height to proxy.width
                detector.process(InputImage.fromMediaImage(media, rotation))
                    .addOnSuccessListener { pose -> onPose(pose, w, h) }  // on the main thread
                    .addOnCompleteListener { proxy.close() }
            }
            val camera = if (front) CameraSelector.DEFAULT_FRONT_CAMERA else CameraSelector.DEFAULT_BACK_CAMERA
            runCatching {
                p.unbindAll()
                p.bindToLifecycle(lifecycle, camera, preview, analysis)
            }
        }, ContextCompat.getMainExecutor(context))
        onDispose { provider?.unbindAll() }
    }
    DisposableEffect(Unit) {
        onDispose {
            detector.close()
            executor.shutdown()
        }
    }
    AndroidView({ previewView }, Modifier.fillMaxSize())
}
