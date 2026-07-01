plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.afienoto.launcher"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.afienoto.launcher"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"

        val botUsername = project.findProperty("botUsername") as String? ?: "YOUR_BOT_USERNAME"
        buildConfigField("String", "BOT_USERNAME", "\"$botUsername\"")
    }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }

    buildFeatures {
        buildConfig = true
        viewBinding = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")
}
