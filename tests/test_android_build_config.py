from pathlib import Path


def test_android_project_includes_gradle_wrapper_and_java11_compatible_plugins():
    root = Path("apps/reader-android")
    project_build = (root / "build.gradle.kts").read_text(encoding="utf-8")
    app_build = (root / "app/build.gradle.kts").read_text(encoding="utf-8")
    wrapper = root / "gradle/wrapper/gradle-wrapper.properties"

    assert (root / "gradlew").exists()
    assert wrapper.exists()
    assert "gradle-7.6.4-bin.zip" in wrapper.read_text(encoding="utf-8")
    assert 'com.android.application") version "7.4.2"' in project_build
    assert 'org.jetbrains.kotlin.android") version "1.8.22"' in project_build
    assert "compileSdk = 33" in app_build
    assert "targetSdk = 33" in app_build
