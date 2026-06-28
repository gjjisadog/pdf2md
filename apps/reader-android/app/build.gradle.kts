plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.bookmd.reader"
    compileSdk = 33

    defaultConfig {
        applicationId = "com.bookmd.reader"
        minSdk = 26
        targetSdk = 33
        versionCode = 1
        versionName = "0.1"
    }
}
