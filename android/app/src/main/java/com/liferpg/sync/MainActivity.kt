package com.liferpg.sync

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.mutableStateOf
import androidx.core.content.IntentCompat
import androidx.lifecycle.lifecycleScope
import com.liferpg.sync.ui.LifeRpgApp
import com.liferpg.sync.ui.LifeRpgTheme
import com.liferpg.sync.widget.WidgetCache
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    /** A meal photo shared into the app, waiting for the Meals tab to log it */
    private val sharedPhoto = mutableStateOf<Uri?>(null)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        GogginsMode.apply(this)
        lifecycleScope.launch { runCatching { WidgetCache.refresh(this@MainActivity) } }
        if (savedInstanceState == null) receive(intent)
        setContent {
            LifeRpgTheme { LifeRpgApp(sharedPhoto.value, onSharedPhotoUsed = { sharedPhoto.value = null }) }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        receive(intent)
    }

    private fun receive(intent: Intent?) {
        if (intent?.action == Intent.ACTION_SEND && intent.type?.startsWith("image/") == true) {
            sharedPhoto.value = IntentCompat.getParcelableExtra(intent, Intent.EXTRA_STREAM, Uri::class.java)
        }
    }
}
