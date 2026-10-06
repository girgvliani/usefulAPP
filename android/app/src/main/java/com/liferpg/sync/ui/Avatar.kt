package com.liferpg.sync.ui

import android.graphics.BitmapFactory
import android.util.LruCache
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.produceState
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request

/** The server's address, so photo paths like /photos/abc.jpg can be loaded ("" before signing in) */
val LocalServerUrl = staticCompositionLocalOf { "" }

/** Profile photos already downloaded; a new photo has a new URL, so nothing goes stale */
object PhotoCache {
    private val cache = LruCache<String, ImageBitmap>(64)
    private val client = OkHttpClient()

    fun put(url: String, image: ImageBitmap) = cache.put(url, image)

    fun cached(url: String): ImageBitmap? = cache.get(url)

    suspend fun load(url: String): ImageBitmap? = cache.get(url) ?: withContext(Dispatchers.IO) {
        runCatching {
            client.newCall(Request.Builder().url(url).build()).execute().use { response ->
                if (!response.isSuccessful) return@use null
                val bytes = response.body.bytes()
                BitmapFactory.decodeByteArray(bytes, 0, bytes.size)?.asImageBitmap()
            }
        }.getOrNull()?.also { cache.put(url, it) }
    }
}

/** A round profile photo, or the name's first letter on the accent gradient */
@Composable
fun Avatar(path: String?, name: String, size: Dp, modifier: Modifier = Modifier, ring: Color? = null) {
    val base = LocalServerUrl.current
    val url = path?.let { if (it.startsWith("http")) it else base + it }
    val image by produceState(url?.let { PhotoCache.cached(it) }, url) {
        value = url?.takeIf { base.isNotEmpty() || it.startsWith("http") }?.let { PhotoCache.load(it) }
    }
    val shape = CircleShape
    val framed = modifier.size(size).let { if (ring != null) it.border(maxOf(size / 24, Dp(1.5f)), ring, shape) else it }.clip(shape)
    val loaded = image
    if (loaded != null) {
        Image(loaded, contentDescription = name, modifier = framed, contentScale = ContentScale.Crop)
    } else {
        Box(framed.background(Brush.linearGradient(listOf(Rpg.Accent, Rpg.AccentDeep))), contentAlignment = Alignment.Center) {
            val letter = name.removePrefix("Player ").firstOrNull { it.isLetterOrDigit() }?.uppercase() ?: "?"
            Text(letter, color = Rpg.Background, fontWeight = FontWeight.Black, fontSize = with(LocalDensity.current) { (size * 0.45f).toSp() })
        }
    }
}
