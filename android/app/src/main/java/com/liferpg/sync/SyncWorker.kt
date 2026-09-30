package com.liferpg.sync

import android.content.Context
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import com.liferpg.sync.widget.WidgetCache
import java.io.IOException
import java.util.concurrent.TimeUnit

/** Hourly background sync. Network errors retry with backoff; setup errors wait for the next hour. */
class SyncWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result = try {
        Sync.run(applicationContext)
        runCatching { GogginsMode.update(applicationContext, Api(Settings(applicationContext)).goals()) }
        runCatching { WidgetCache.refresh(applicationContext) }
        runCatching { LevelUpNotice.check(applicationContext) }
        Result.success()
    } catch (e: IOException) {
        Settings(applicationContext).lastStatus = "⚠️ Sync failed, will retry: ${e.message}"
        Result.retry()
    } catch (e: ApiException) {
        // 5xx may be a restart on the server's side; 4xx (bad token, bad data) won't fix itself
        Settings(applicationContext).lastStatus = "❌ Sync failed (${e.code}): ${e.message}"
        if (e.code >= 500) Result.retry() else Result.failure()
    } catch (e: Exception) {
        Settings(applicationContext).lastStatus = "❌ Sync failed: ${e.message}"
        Result.failure()
    }

    companion object {
        private const val NAME = "hourly-sync"

        fun schedule(context: Context) {
            val request = PeriodicWorkRequestBuilder<SyncWorker>(1, TimeUnit.HOURS)
                .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
                .build()
            WorkManager.getInstance(context).enqueueUniquePeriodicWork(NAME, ExistingPeriodicWorkPolicy.UPDATE, request)
        }
    }
}
