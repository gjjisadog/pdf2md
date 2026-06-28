plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.bookmd.reader"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.bookmd.reader"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "0.1"
    }
}
