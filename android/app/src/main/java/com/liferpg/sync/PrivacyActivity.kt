package com.liferpg.sync

import android.app.Activity
import android.os.Bundle
import android.widget.TextView

/** Shown by Health Connect when you ask why this app wants health data. */
class PrivacyActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val padding = (16 * resources.displayMetrics.density).toInt()
        setContentView(TextView(this).apply {
            setText(R.string.privacy_text)
            textSize = 16f
            setPadding(padding, padding, padding, padding)
        })
    }
}
