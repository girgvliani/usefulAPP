package com.liferpg.sync

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.media.ExifInterface
import android.net.Uri
import androidx.core.content.FileProvider
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.ByteArrayOutputStream
import java.io.File
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter

/** Turns a camera or gallery photo into a small JPEG for the meal reader, plus when it was taken. */
object MealPhotos {
    private const val MAX_SIDE = 1600
    private val EXIF_TIME = DateTimeFormatter.ofPattern("yyyy:MM:dd HH:mm:ss")

    class Prepared(val jpeg: ByteArray, val takenAt: String?)

    /** A fresh file for the camera to write into, shared with it through the FileProvider */
    fun newCameraUri(context: Context): Uri {
        val dir = File(context.cacheDir, "meals").apply { mkdirs() }
        val file = File(dir, "meal-${System.currentTimeMillis()}.jpg")
        return FileProvider.getUriForFile(context, "${context.packageName}.files", file)
    }

    suspend fun prepare(context: Context, uri: Uri): Prepared = withContext(Dispatchers.IO) {
        val resolver = context.contentResolver
        val exif = resolver.openInputStream(uri)?.use { runCatching { ExifInterface(it) }.getOrNull() }

        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        resolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, bounds) }
        var sample = 1
        while (maxOf(bounds.outWidth, bounds.outHeight) / (sample * 2) >= MAX_SIDE) sample *= 2
        val decoded = resolver.openInputStream(uri)?.use {
            BitmapFactory.decodeStream(it, null, BitmapFactory.Options().apply { inSampleSize = sample })
        } ?: error("Couldn't open that photo")

        val upright = rotate(decoded, exif?.rotationDegrees ?: 0)
        val scale = MAX_SIDE.toFloat() / maxOf(upright.width, upright.height)
        val sized = if (scale < 1f) Bitmap.createScaledBitmap(upright, (upright.width * scale).toInt(), (upright.height * scale).toInt(), true) else upright
        val jpeg = ByteArrayOutputStream().use { out ->
            sized.compress(Bitmap.CompressFormat.JPEG, 85, out)
            out.toByteArray()
        }
        val takenAt = exif?.getAttribute(ExifInterface.TAG_DATETIME_ORIGINAL)
            ?.let { runCatching { LocalDateTime.parse(it, EXIF_TIME).toString() }.getOrNull() }
        Prepared(jpeg, takenAt)
    }

    private fun rotate(bitmap: Bitmap, degrees: Int): Bitmap =
        if (degrees == 0) bitmap else Bitmap.createBitmap(bitmap, 0, 0, bitmap.width, bitmap.height, Matrix().apply { postRotate(degrees.toFloat()) }, true)

    private val ExifInterface.rotationDegrees: Int
        get() = when (getAttributeInt(ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL)) {
            ExifInterface.ORIENTATION_ROTATE_90 -> 90
            ExifInterface.ORIENTATION_ROTATE_180 -> 180
            ExifInterface.ORIENTATION_ROTATE_270 -> 270
            else -> 0
        }
}
