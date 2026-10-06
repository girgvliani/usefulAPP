plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.plugin.compose")
}

android {
    namespace = "com.liferpg.sync"
    compileSdk = 37

    defaultConfig {
        applicationId = "com.liferpg.sync"
        minSdk = 29
        targetSdk = 36
        versionCode = 14
        versionName = "0.14"
        // ML Kit's pose detection ships native code for every CPU; phones like the Galaxy S23 only need arm64
        ndk { abiFilters += listOf("arm64-v8a") }
    }

    buildFeatures {
        compose = true
    }

    testOptions {
        unitTests {
            isIncludeAndroidResources = true
            // Screenshot tests write PNGs to app/build/screenshots
            all {
                it.systemProperty("roborazzi.test.record", "true")
                // Robolectric reaches into JDK internals that Java 21 locks by default
                it.jvmArgs("--add-opens=java.base/jdk.internal.access=ALL-UNNAMED", "--add-opens=java.base/java.io=ALL-UNNAMED")
            }
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.19.1")
    implementation("androidx.activity:activity-compose:1.13.0")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.11.0")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.11.0")
    implementation("androidx.work:work-runtime-ktx:2.12.0")
    implementation("androidx.health.connect:connect-client:1.1.0")
    // Rep counter: camera preview + frames, and pose detection on the phone
    implementation("androidx.camera:camera-camera2:1.5.0")
    implementation("androidx.camera:camera-lifecycle:1.5.0")
    implementation("androidx.camera:camera-view:1.5.0")
    implementation("com.google.mlkit:pose-detection:18.0.0-beta5")
    implementation("com.squareup.okhttp3:okhttp:5.5.0")
    implementation("androidx.glance:glance-appwidget:1.2.0")

    implementation(platform("androidx.compose:compose-bom:2026.09.00"))
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    debugImplementation("androidx.compose.ui:ui-tooling")
    debugImplementation("androidx.compose.ui:ui-test-manifest")

    // Screenshot tests: render Compose screens on the JVM, no phone or emulator needed
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.robolectric:robolectric:4.17")
    testImplementation("io.github.takahirom.roborazzi:roborazzi:1.76.0")
    testImplementation("io.github.takahirom.roborazzi:roborazzi-compose:1.76.0")
    testImplementation("androidx.compose.ui:ui-test-junit4")
    testImplementation("androidx.glance:glance-appwidget-testing:1.2.0")
}
