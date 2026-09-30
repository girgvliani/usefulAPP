package com.liferpg.sync

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

/** Brings Goggins mode back after the phone restarts. */
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED) GogginsMode.apply(context)
    }
}
